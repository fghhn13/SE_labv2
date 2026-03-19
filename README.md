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
  - `Trainer`：episode 循环控制，支持按 episode 数的断点续训。
  - `BasicRecordingStructure`：记录每个 episode 的完整路径和结果，方便后续结构分析。
  - 日志与可视化：
    - `CsvEpisodeLogger`：按 episode 写 CSV。
    - 代表性路径图（最频繁 / 最好 / 最坏）使用 matplotlib 绘制。
    - 训练曲线（成功率 / 步数 / cost）使用 pandas + matplotlib 绘制。
  - CLI：
    - `lab.cli.run_experiment`：单次训练 + 结果可视化（CSV + 地图 + 训练曲线）。
    - `lab.cli.run_and_plot`：一键“训练 + 画图”（兼容 `run_experiment` 的配置）。
  - 实验配置与结果组织：
    - `experiments/<agent_name>/*.json`：按 Agent 名称组织实验配置。
    - 地图通过 `env.map_name` 指定：
      - 内置地图在 `lab.envs.grid.maps` 中注册；
      - `maps/*.map` 会在运行时被自动注册。
      - `.map` 采用 `[Metadata]` + `[Sandbox]` 两段式，Sandbox 由元素符号构建。
    - 结果自动归档到 `lab_v2_results/<agent_name>/<map_name>/...`。
  - 调试辅助（外挂 GUI）：
    - `lab/scripts/manual_play.py`：用 tkinter 手动操作环境，用于验证终止与 `info` 语义。
- **规划中（后续工作）**：
  - 更丰富的地图生成器（如 corridor / maze）与可达性检查。
  - 更复杂的 Agent（结构感知 / 学习型）。
  - 结构服务从“路径记录”演进到“宏 / 子目标 / 图结构”抽取。
  - 批量实验 / 对比工具（简单 sweep / grid search）。

---

### 仓库结构（当前概览）

主要目录与模块如下（简化版）：

- `lab/core/`：通用类型与接口（`Environment` / `Agent` / `StructureService` 等）。
- `lab/envs/`：
  - `grid/`：2D 栅格环境（`GridMap`、`GridWorldEnvironment`、`maps.py`）。
- `lab/agents/`：
  - `random_agent.py`、`greedy_agent.py`、`base.py`、`registry.py` 等。
- `lab/structure/`：
  - `basic_recorder.py` 及结构服务注册表。
- `lab/trainer/`：
  - `loop.py`：`Trainer` 与回调接口。
- `lab/logging/`：
  - `csv_logger.py`。
- `lab/viz/`：
  - `grid_plot.py`：地图与路径可视化。
  - `metrics.py` / `run_metrics.py`：训练曲线绘制。
- `lab/cli/`：
  - `run_experiment.py` / `run_and_plot.py`：实验入口脚本。
- `experiments/`：
  - `random/`、`greedy/`：按 Agent 名称组织的实验配置。
- `docs/`：
  - `architecture.md`、`project_plan.md`、`quickstart.md`、`concepts.md`、
  - `adding_agent.md`、`map_rules_and_runner.md` 等。

---

### 计划中的架构总览

核心分层（详细见 `docs/architecture.md`）：

- **`core`**：通用类型、接口、工具函数（时间管理、配置、通用数据结构等）。
- **`envs`**：环境相关，包括栅格地图、地图生成器、环境执行逻辑。
- **`agents`**：不同决策策略 / 模型的实现，统一 Agent 接口。
- **`structure`**：结构服务（`StructureService`）及相关数据结构，用于追踪与更新内部可解释结构。
- **`trainer`**：训练与采样循环控制器，负责 episode / step 循环和模块调用。
- **`logging`**：日志与指标收集（文本日志、标量指标等），以回调 / 钩子形式挂载到 Trainer。
- **`viz`**：可视化模块（例如路径、结构图、学习曲线等），与训练逻辑解耦。
- **`cli`**：命令行入口，用于运行预定义实验场景。

一个典型的控制流程：

1. `Trainer` 从 `envs` 请求一个新 episode（生成或加载地图）。
2. Episode 内，`Trainer` 在每个 step：
   - 将当前状态传给 `Agent`；
   - 接收 `Agent` 动作并送入 `Environment`；
   - 从 `Environment` 获取下一状态 / 奖励 / 终止标记。
3. `Trainer` 将与结构相关的信息（如路径片段、成功/失败记录）交给 `StructureService`。
4. `StructureService` 更新内部结构表示（例如宏、子图），并可选择反馈给 `Agent`。
5. `logging` / `viz` 通过回调获取事件流，记录或可视化。

---

### v0 目标

v0 的目标是搭建一个**最小可运行的实验骨架**，而不是完成任何“最优算法”：

- **一个最简单的 2D 栅格最短路径环境**
  - 固定大小或简单可配置
  - 简单障碍布置
- **一个基础 Agent**
  - 可以是随机策略、贪心策略或简单可学习策略
- **一个最小 Trainer**
  - 能够运行多 episode 的训练 / 采样循环
  - 能够挂载简单的日志回调
- **一个简单的 StructureService 占位实现**
  - 至少能够记录路径和基本统计（例如成功路径集合）
  - 为后续“结构涌现”研究预留接口
- **一个从 CLI 运行的首个实验脚本**
  - 当前由 `lab.cli.run_experiment` / `lab.cli.run_and_plot` 承担。

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

- **运行示例实验（5×5 开放地图，Random Agent）**

```bash
python -m lab.cli.run_experiment experiments/random/basic_grid_open_5x5.json
```

- **手动操控 GUI（用于调试终止与元素交互语义）**

示例（使用仓库 `maps/` 下新增的示例地图）：
```bash
python -m lab.scripts.manual_play --map-name level_01_trap_maze
```

- **运行 Greedy Agent 与 10×10 随机障碍示例**

```bash
python -m lab.cli.run_experiment experiments/greedy/basic_grid_open_5x5.json
python -m lab.cli.run_experiment experiments/random/basic_grid_10x10_random_blocks.json
python -m lab.cli.run_experiment experiments/greedy/basic_grid_10x10_random_blocks.json
```

- **查看结果**

所有结果按 `agent_name/map_name` 归档，例如：

- `lab_v2_results/random/open_5x5/...`
- `lab_v2_results/greedy/random_blocks_10x10/...`

其中包括：

- `*.csv`：每 episode 的成功 / 步数 / cost（当前物理层 reward 已剔除，`cost` 可能是占位值；建议优先看 `steps` 与 `success`）；
- `maps/*.png`：代表性路径图（最频繁 / 最好 / 最坏）；
- `plots/*.png`：训练曲线（成功率 / 步数 / cost）。

---

### 路线图（简要）

更详细的规划见 `docs/project_plan.md`，这里给出简要版，并标记当前进度：

- **里程碑 1：架构骨架 ✅（已完成初版）**
  - 搭建基础目录与模块接口（core/envs/agents/structure/trainer/logging/viz/cli）。
- **里程碑 2：首个可运行版本 ✅（已完成）**
  - 实现简单 Grid 环境、Random/Greedy Agent 和 Trainer；可通过 CLI 跑通多个实验。
- **里程碑 3：结构观察版本 ⏳（进行中）**
  - `BasicRecordingStructure` 已能记录和导出路径；后续将增加更丰富的结构统计和导出格式。
  - 已有基本的日志与可视化支持（CSV + 路径图 + 训练曲线）。
- **里程碑 4：可做实验的版本（规划）**
  - 计划增加更系统的实验管理（sweep）、更复杂的地图和 Agent，对结构涌现进行系统性探索。

---

### 贡献与维护

本仓库目前是个人研究实验室，主要面向：

- 未来的自己（回顾思路、继续迭代）
- 可能的合作者（快速理解架构与研究方向）

如果未来开放协作，将在此处补充贡献指南与代码规范。

