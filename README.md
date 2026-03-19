## Minimal Emergent Structure Lab (2D Shortest Path)

一个用于研究 **最小可复用决策结构** 在 2D 栅格最短路径任务中如何涌现的个人实验仓库。

本项目侧重于**实验基础设施**，而不是一开始就固定具体算法或模型形式。当前目标是搭建一个干净、可扩展的实验平台，用于长期迭代与结构可解释性研究。

---

### 项目愿景

- **研究问题**：在简单的 2D 最短路径任务中，智能体在学习过程中是否会自发形成可复用的内部决策结构（如宏动作、子目标图、决策树片段等）。
- **长期目标**：让这些内部结构尽可能 **人类可读 / 可解释**，例如：
  - 决策树或规则表
  - 宏动作图（macro graph）
  - 可视化的子目标 / 通路结构
- **设计原则**：
  - 环境与学习逻辑解耦
  - 训练循环清晰、可插拔
  - 新 Agent / 新环境 / 新结构服务易于添加
  - 日志与可视化模块化，方便后期扩展

---

### 当前状态

- **已实现（v0 实验骨架）**：
  - `GridWorldEnvironment`：支持基于 `Element` 的网格地图（起点 `S`、终点 `G`、墙 `#`、陷阱 `x` 等）。
    - 物理裁判仅依赖 `Element.is_passable()` 与 `Element.interact()`。
    - Immediate Termination：`done` 来自元素交互返回的 `terminal`。
    - 元素交互的成功标记写入 `step_result.info["success"]`（Trap => false，Goal => true）。
    - 为保持轻量兼容，当前环境返回的 `StepResult.reward` 为占位值（物理层暂不计算 reward）。
  - `RandomAgent` / `GreedyAgent`：随机策略与基于曼哈顿距离的贪心策略（支持 `epsilon` 探索）。
  - **训练数据闭环（当前默认链路）**：
    - `lab/trainer/loop.py`：`BarebonesTrainer`（最小 episode loop + 终端打印）。
    - `lab/trainer/standard_trainer.py`：`StandardTrainer`（广播事件给 listeners，success 严格来自 `step_result.info["success"]`）。
    - `lab/listeners/async_jsonl_listener.py`：`AsyncJsonlListener`（后台线程把事件写入 `events.jsonl`）。
    - `lab/reporters/text_summary_reporter.py`：`TextSummaryReporter`（离线读取 `events.jsonl` 输出 `summary.txt`）。
    - CLI：
      - `python -m lab.cli.run_barebones`：验证 success/steps 打印。
      - `python -m lab.cli.run_standard_trainer`：生成 events.jsonl。
      - `python -m lab.cli.run_reporter`：离线生成文字战报（summary.txt）。
  - 调试辅助（外挂 GUI）：
    - `lab/scripts/manual_play.py`：用 tkinter 手动操作环境，用于验证终止与 `info` 语义。
  - 说明：旧版 CSV + 画图链路已彻底移除；当前默认闭环以 listeners/reporters 为主。
- **规划中（后续工作）**：
  - 更丰富的地图生成器（如 corridor / maze）与可达性检查。
  - 更复杂的 Agent（结构感知 / 学习型）。
  - 结构服务从“路径记录”演进到“宏 / 子目标 / 图结构”抽取。
  - 批量实验 / 对比工具（简单 sweep / grid search）。

---

### 仓库结构（当前概览）

主要目录与模块如下（简化版）：

- `lab/core/`：通用类型与接口（`Environment` / `Agent`）。
- `lab/envs/`：
  - `grid/`：2D 栅格环境（`GridMap`、`GridWorldEnvironment`、`maps.py`）。
- `lab/agents/`：
  - `random_agent.py`、`greedy_agent.py`、`base.py`、`registry.py` 等。
- `lab/listeners/`：
  - `async_jsonl_listener.py`：异步写入 `events.jsonl`。
- `lab/reporters/`：
  - `text_summary_reporter.py`：离线读取 `events.jsonl` 并输出 `summary.txt`。
- `lab/trainer/`：
  - `loop.py`：`BarebonesTrainer`（最小 episode loop + 终端打印）。
  - `standard_trainer.py`：`StandardTrainer`（广播事件给 listeners）。
- `lab/cli/`：
  - `run_barebones.py`：最小 loop 验证。
  - `run_standard_trainer.py`：生成 `events.jsonl`。
  - `run_reporter.py`：离线生成 `summary.txt`。
- `lab/scripts/`：
  - `manual_play.py`：外挂 tkinter GUI 手动操控环境（用于 debug）。
  - `debug_map_check.py` / `debug_rollout.py`：地图格式校验 + 最小 rollout 检查。
- `docs/`：
  - `architecture.md`：当前实现的整体分层说明。
  - `grid_map_module_today.md`：今天地图模块实现说明（Element/注册/解析/step 语义）。
  - `trainer_listeners_reporters.md`：Trainer->Listener->Reporter 事件闭环与 Data Contract。
  - `version_past/`：历史/规划版文档归档。

---

### 当前架构总览（重点）

地图与环境语义见 `docs/grid_map_module_today.md`，训练数据流闭环见：
- `docs/trainer_listeners_reporters.md`
- `docs/architecture.md`

当前最关键的数据流是：
- **Online（采样）**：`StandardTrainer` 驱动 `env.reset -> agent.select_action -> env.step`，并在每个 episode 广播标准化事件。
- **Async（落盘）**：`AsyncJsonlListener` 后台线程写入 `events.jsonl`（主线程只入队，避免阻塞）。
- **Offline（聚合）**：`TextSummaryReporter` 离线读取 `events.jsonl`，聚合 `episode_end` 指标并输出 `summary.txt`。

---

### v0 目标

v0 的目标是搭建一个**最小可运行的实验骨架**，而不是完成任何“最优算法”：

- **一个最简单的 2D 栅格最短路径环境**
  - 固定大小或简单可配置
  - 简单障碍布置
- **一个基础 Agent**
  - 可以是随机策略、贪心策略或简单可学习策略
- **一个最小 Trainer**
  - 能够运行多 episode 的训练 / 采样循环（`BarebonesTrainer` / `StandardTrainer`）
- **一个 Listener（异步落盘）**
  - `AsyncJsonlListener`：把事件写入 `events.jsonl`
- **一个 Reporter（离线聚合）**
  - `TextSummaryReporter`：从 `events.jsonl` 生成 `summary.txt`
- **一个从 CLI 运行的最小闭环脚本**
  - `run_barebones -> run_standard_trainer -> run_reporter`

---

### 快速开始（当前版本）

- **克隆仓库并进入目录**

```bash
git clone <your-repo-url>
cd lab_v2
```

- **创建 Conda 环境并安装依赖（推荐）**

```bash
conda create -n minimal-structure-lab python=3.10
conda activate minimal-structure-lab
pip install -e .           # 安装核心包
pip install -e ".[viz]"    # 如需画图（matplotlib + pandas）
```

- **1) 最小 loop 验证（BarebonesTrainer）**

```bash
python -m lab.cli.run_barebones --episodes 5 --max-steps 50 --map-name level_01_trap_maze --agent-name greedy --epsilon 0.1
```

- **2) 生成事件落盘（events.jsonl）**

```bash
python -m lab.cli.run_standard_trainer --episodes 10 --max-steps 50 --map-name level_01_trap_maze --agent-name greedy --epsilon 0.1 --output-jsonl lab_v2_results/standard/events.jsonl
```

- **3) 离线生成文字战报（summary.txt）**

```bash
python -m lab.cli.run_reporter --events-jsonl lab_v2_results/standard/events.jsonl --summary-out lab_v2_results/standard/summary.txt
```

- **手动操控 GUI（用于调试终止与元素交互语义）**

示例（使用仓库 `maps/` 下新增的示例地图）：
```bash
python -m lab.scripts.manual_play --map-name level_01_trap_maze
```

你也可以运行你自己的 `.map`：
1. 把地图文件放到仓库根目录 `maps/` 下；
2. `--map-name` 使用文件名（不含扩展名，例如 `level_01_trap_maze.map` 对应 `level_01_trap_maze`）。

- **调试脚本（不启动 GUI）**
```bash
python -m lab.envs.grid.debug_map_check --map-name level_01_trap_maze
python -m lab.envs.grid.debug_rollout --map-name level_01_trap_maze
```

- **查看结果（当前闭环）**
  - `events.jsonl`：训练过程原始事件流（用于离线 Reporter）
  - `summary.txt`：离线聚合战报

---

### 路线图（简要）

历史与规划版文档见 `docs/version_past/`。这里给出与当前实现对齐的简要进度：

- **里程碑 A：地图/环境语义契约 ✅（已完成）**：Element 注册、`.map` 解析、物理裁判 step 语义与 `info["success"]`。
- **里程碑 B：Trainer->Listener->Reporter 数据闭环 ✅（已完成）**：`events.jsonl` + 异步落盘 + 离线 `summary.txt`。
- **里程碑 C：结构观察与可解释扩展 ⏳（后续）**：从路径集合/统计扩展到宏动作/子目标/图结构抽取与可视化。
- **里程碑 D：实验管理与对比 ⏳（后续）**：sweep/grid search、多 run 汇总、统一导出。

---

### 贡献与维护

本仓库目前是个人研究实验室，主要面向：

- 未来的自己（回顾思路、继续迭代）
- 可能的合作者（快速理解架构与研究方向）

如果未来开放协作，将在此处补充贡献指南与代码规范。

