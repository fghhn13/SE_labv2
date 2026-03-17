import json
import os
import sys
from typing import Any, Dict, Tuple, Optional

from lab.core.types import EpisodeResult
from lab.envs import registry as env_registry
from lab.agents import registry as agent_registry
from lab.structure import registry as structure_registry
from lab.structure.basic_recorder import BasicRecordingStructure
from lab.viz.grid_text import print_path_summaries
from lab.viz.grid_plot import save_representative_path_plots
from lab.trainer.loop import Trainer
from lab.logging.csv_logger import CsvEpisodeLogger
from lab.envs.grid.grid_map import GridMap
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.maps import register_builtin_maps, get_map
from lab.agents.random_agent import RandomAgent
from lab.agents.greedy_agent import GreedyAgent


def _get_completed_episodes(csv_path: str) -> int:
    """
    从已有的 CSV 日志中推断已完成的 episode 数量。
    约定：episode 列为从 0 开始的递增整数。
    """
    if not os.path.exists(csv_path):
        return 0

    last_episode: Optional[int] = None
    with open(csv_path, "r", encoding="utf-8") as f:
        # 跳过表头
        header = next(f, None)
        for line in f:
            parts = line.strip().split(",")
            if not parts or parts[0] == "":
                continue
            try:
                last_episode = int(parts[0])
            except ValueError:
                continue

    if last_episode is None:
        return 0

    return last_episode + 1


def _maybe_plot_metrics(csv_path: str, plots_dir: str, window: int = 10) -> None:
    """
    如果安装了可视化依赖 (.[viz])，则基于 CSV 生成训练曲线图。
    否则仅打印提示，不影响训练流程。
    """
    try:
        from lab.viz.metrics import plot_all_metrics  # type: ignore
    except Exception:
        print(
            "[run_experiment] plotting skipped; install extras with "
            '"pip install -e .[viz]" to enable metric plots.'
        )
        return

    os.makedirs(plots_dir, exist_ok=True)
    print(
        f"[run_experiment] plotting metrics from CSV {csv_path} "
        f"to directory {plots_dir}"
    )
    plot_all_metrics(csv_path, output_dir=plots_dir, window=window)


def _register_defaults() -> None:
    # 注册内置地图
    register_builtin_maps()

    # Env: basic grid
    def build_grid_env(**kwargs: Any):
        # 实验配置中只写 map_name，不直接写 width/height/walls 等细节
        map_name = kwargs.get("map_name", "open_5x5")
        grid = get_map(map_name)
        return GridWorldEnvironment(grid_map=grid)

    env_registry.register("grid_basic", build_grid_env)

    # Agent: random
    def build_random_agent(**kwargs: Any):
        return RandomAgent(seed=kwargs.get("seed"))

    agent_registry.register("random", build_random_agent)

    # Agent: greedy (曼哈顿距离启发式)
    def build_greedy_agent(env=None, **kwargs: Any):
        # env 由 agent_registry.create 传入（可为空），用于读取 goal 坐标
        return GreedyAgent(env=env, seed=kwargs.get("seed"), epsilon=kwargs.get("epsilon", 0.0))

    agent_registry.register("greedy", build_greedy_agent)

    # Structure: placeholder no-op
    class NoOpStructure:
        def on_episode_end(self, result: EpisodeResult, env):
            return

        def query(self, state):
            return None

    def build_noop_structure(**kwargs: Any):
        return NoOpStructure()

    def build_basic_recorder(**kwargs: Any):
        return BasicRecordingStructure()

    structure_registry.register("none", build_noop_structure)
    structure_registry.register("basic_recorder", build_basic_recorder)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(config_path: str) -> None:
    _register_defaults()
    cfg = load_config(config_path)

    env_cfg = cfg.get("env", {}) or {}
    agent_cfg = cfg.get("agent", {}) or {}
    structure_cfg = cfg.get("structure", {}) or {}
    trainer_cfg = cfg.get("trainer", {})
    logging_cfg = cfg.get("logging", {})

    # 提前取出 name，避免在 **kwargs 中重复传入
    env_name = env_cfg.pop("name", "grid_basic")
    agent_name = agent_cfg.pop("name", "random")
    structure_name = structure_cfg.pop("name", "none")

    # 记录 map 名称用于结果目录组织与可视化标签
    map_name = env_cfg.get("map_name", "unknown_map")

    env = env_registry.create(env_name, **env_cfg)
    agent = agent_registry.create(agent_name, **agent_cfg)
    structure = structure_registry.create(structure_name, **structure_cfg)

    callbacks = []
    csv_path_cfg = logging_cfg.get("csv_path")
    csv_path = None
    completed_episodes = 0
    if csv_path_cfg:
        # 按模型名 / 地图名组织结果：
        # config 中写的是一个相对路径，例如 "lab_v2_results/basic_grid_shortest_path.csv"
        # 实际使用时会变成 "lab_v2_results/<agent_name>/<map_name>/basic_grid_shortest_path.csv"
        base_dir = os.path.dirname(csv_path_cfg)
        filename = os.path.basename(csv_path_cfg)
        csv_path = os.path.join(base_dir, agent_name, map_name, filename)

        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        callbacks.append(CsvEpisodeLogger(csv_path, print_to_stdout=True))
        # 简单断点续训：从现有 CSV 推断已完成的 episode 数量
        completed_episodes = _get_completed_episodes(csv_path)

    trainer = Trainer(
        env=env,
        agent=agent,
        structure=structure,
        callbacks=callbacks,
        max_steps=trainer_cfg.get("max_steps", 100),
    )
    episodes_target = trainer_cfg.get("episodes", 50)

    # 计算本次应该再跑多少个 episode
    remaining = max(0, episodes_target - completed_episodes)
    if remaining <= 0:
        print(
            f"[run_experiment] target episodes={episodes_target}, "
            f"already completed={completed_episodes}. Nothing to run."
        )
    else:
        trainer.start_episode = completed_episodes
        print(
            f"[run_experiment] resuming from episode {completed_episodes}, "
            f"running {remaining} more episodes (target={episodes_target})."
        )
        trainer.run(remaining)

    # 训练完成后，基于本次运行记录的历史打印代表性文字总结，并输出路径图
    if isinstance(structure, BasicRecordingStructure) and structure.history:
        # 1) 终端文字输出（整体统计 + 三类代表性 episode 信息）
        print_path_summaries(env.grid, structure.history)

        # 2) 使用 matplotlib 绘制代表性路径图
        if csv_path:
            base_dir = os.path.dirname(csv_path)
            maps_dir = os.path.join(base_dir, "maps")
        else:
            # 回退路径：按 agent / map 组织
            maps_dir = os.path.join("lab_v2_results", agent_name, map_name, "maps")
        save_representative_path_plots(env.grid, structure.history, maps_dir)

        # 3) 基于 CSV 绘制训练指标曲线（如果可视化依赖可用）
        if csv_path:
            plots_dir = os.path.join(os.path.dirname(csv_path), "plots")
            _maybe_plot_metrics(csv_path, plots_dir, window=10)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m lab.cli.run_experiment <config_path>")
        sys.exit(1)
    main(sys.argv[1])

