## 架构说明（当前实现）

本文件描述当前（已落地）的最小可运行研究架构：把 2D 栅格任务切分为 **地图/环境层** 与 **训练数据流层**，训练数据流层采用：
- Online 训练采样（Trainer 驱动 env-agent 交互）
- Async Listener 异步落盘（写原始事件 jsonl）
- Offline Reporter 离线聚合（读事件 jsonl 生成文本战报）

地图与环境层的语义见 `docs/grid_map_module_today.md`。
Trainer/Listener/Reporter 的事件契约见 `docs/trainer_listeners_reporters.md`。

---

### 1. 模块分层与职责

#### 1.1 `envs`：环境层（物理裁判）

- `lab/envs/grid/grid_map.py`：`GridMap`，提供元素/数值编码查询与基础网格接口。
- `lab/envs/grid/map_file_parser.py`：解析 `.map` 文件为元素网格。
- `lab/envs/grid/environment.py`：`GridWorldEnvironment.step(action)`：
  - 越界/不可通行保持原地并写 `info["blocked"]=True`
  - 可通行则调用元素 `interact()`，以 `outcome["terminal"]` 决定 `done`
  - 用 `outcome["success"]` 写入 `step_result.info["success"]`

> 重要：当前物理层 reward 为占位值；训练模块的 success 语义来自 `info["success"]`。

#### 1.2 `agents`：智能体层（决策）

- `lab/agents/*`：遵循统一 `Agent` 协议：
  - `select_action(state, env)`
  - `observe(step_result)`
  - `end_episode(episode_result)`

Trainer 负责驱动循环，Agent 不参与训练控制流程。

#### 1.3 `trainer`：训练数据流在线阶段（Online）

- `lab/trainer/loop.py`：`BarebonesTrainer`
  - 纯 episode loop + 每 episode 只打印成功/失败与步数
  - 用于快速验证 success 语义与 step/done 对齐
- `lab/trainer/standard_trainer.py`：`StandardTrainer`
  - drives episode/step
  - 每个 step/episode_end 广播事件给 `listeners`
  - success 严格读取 `step_result.info["success"]`
  - 不在主线程做 IO（IO 由 Listener 后台线程完成）

#### 1.4 `listeners`：训练期间异步落盘（Async Logging）

- `lab/listeners/base.py`：`Listener` 协议（`on_step`/`on_episode_end`/`close`）
- `lab/listeners/async_jsonl_listener.py`：`AsyncJsonlListener`
  - 后台线程把事件写入 `events.jsonl`
  - 主线程只做非阻塞入队（队列满时丢弃旧事件保护 FPS）

#### 1.5 `reporters`：训练结束后的离线聚合（Offline Reporting）

- `lab/reporters/text_summary_reporter.py`：`TextSummaryReporter`
  - 读取 `events.jsonl`
  - 聚合 `event_type == "episode_end"` 的 `episode/steps/success`
  - 输出到终端，并可选写入 `summary.txt`

---

### 2. Online -> Async Logging -> Offline Reporting 数据流

典型数据流：

1. `python -m lab.cli.run_standard_trainer ...`
2. `StandardTrainer`：
   - 调用 `env.reset()`
   - `agent.select_action(state, env)` -> `env.step(action)` -> `agent.observe(step_result)`
   - 广播事件：`event_type="step"` 与 `event_type="episode_end"`
3. `AsyncJsonlListener`：异步把事件写入 `events.jsonl`
4. `python -m lab.cli.run_reporter ...`
5. `TextSummaryReporter`：离线读取并生成文本战报

---

### 3. 事件 Data Contract（强制约定）

事件 schema 与字段约定见 `docs/trainer_listeners_reporters.md`，当前核心包括：
- `schema_version`：如 `"1.0"`
- `run_id`：同一训练 run 的 UUID（全文件共享）
- `event_type`：`"step"` / `"episode_end"`
- `episode_end` 行必须包含：`episode`、`steps`、`success`

---

### 4. 推荐的最小验证/使用路径

1. 先跑 Barebones 验证 success 语义：
   - `python -m lab.cli.run_barebones --episodes 5 --max-steps 50`
2. 再跑 StandardTrainer 生成事件：
   - `python -m lab.cli.run_standard_trainer --episodes 10 --output-jsonl lab_v2_results/standard/events.jsonl`
3. 最后用 Reporter 生成战报：
   - `python -m lab.cli.run_reporter --events-jsonl lab_v2_results/standard/events.jsonl --summary-out lab_v2_results/standard/summary.txt`


