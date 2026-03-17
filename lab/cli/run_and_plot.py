from __future__ import annotations

"""
一键脚本：先训练，再画图。

等价流程：
1) 调用 run_experiment.main(config_path) 进行训练（含断点续训、CSV 日志、代表性路径图）。
2) 使用 viz.metrics.plot_all_metrics 根据 CSV 结果画出指标曲线。
"""

import argparse
import os
from pathlib import Path
from typing import Optional

from . import run_experiment
from lab.viz.metrics import plot_all_metrics


def _default_csv_and_plot_dir(config_path: Path) -> tuple[Optional[Path], Optional[Path]]:
    """
    从 config.json 推断 CSV 路径和 plot 目录。
    如果 config 中没有 logging.csv_path，则返回 (None, None)。
    """
    import json

    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    logging_cfg = cfg.get("logging", {}) or {}
    agent_cfg = cfg.get("agent", {}) or {}
    env_cfg = cfg.get("env", {}) or {}
    agent_name = agent_cfg.get("name", "unknown_agent")
    map_name = env_cfg.get("map_name", "unknown_map")
    csv_path_str = logging_cfg.get("csv_path")
    if not csv_path_str:
        return None, None

    # 与 run_experiment 中的规则保持一致：在中间插入模型名与地图名子目录
    base = (config_path.parent / csv_path_str).resolve()
    csv_path = base.parent / agent_name / map_name / base.name
    plots_dir = csv_path.parent / "plots"
    return csv_path, plots_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run training and then plot metrics in one command."
    )
    parser.add_argument(
        "config_path",
        type=str,
        help="Path to experiment config JSON (same as run_experiment).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=10,
        help="Rolling window size for smoothing metrics when plotting.",
    )

    args = parser.parse_args(argv)
    config_path = Path(args.config_path).resolve()
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")

    # 1) 先运行训练（包含断点续训、CSV 日志与代表性路径图）
    run_experiment.main(str(config_path))

    # 2) 再根据 CSV 画指标曲线
    csv_path, plots_dir = _default_csv_and_plot_dir(config_path)
    if csv_path is None:
        print("[run_and_plot] No logging.csv_path in config; skip metric plotting.")
        return

    if not csv_path.exists():
        print(f"[run_and_plot] CSV not found after training: {csv_path}")
        return

    print(
        f"[run_and_plot] plotting metrics from CSV {csv_path} "
        f"to directory {plots_dir}"
    )
    plot_all_metrics(csv_path, output_dir=plots_dir, window=args.window)


if __name__ == "__main__":
    main()

