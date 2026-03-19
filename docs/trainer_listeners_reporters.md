## Trainer / Listeners / Reporters 模块（事件数据流闭环）

### 1. 目标
本模块用于完成“训练在线采集 + 异步落盘 + 离线聚合报告”的闭环数据流，专注于：
- 训练循环的纯调度（Trainer 负责 env-agent 交互）
- 训练期间非阻塞 IO（Listener 在后台线程落盘）
- 训练结束后的可读报告（Reporter 从落盘文件离线读取并聚合）

本次实现的核心成功语义：
- 当 `env.step(action)` 返回 `done=True` 时，以 `step_result.info.get("success", False)` 作为 episode 的 `success`

### 2. 模块划分与职责
1. `lab/trainer/standard_trainer.py`
   - `StandardTrainer`：驱动 episode / step 循环
   - 在每个 step 广播事件（`event_type="step"`）
   - 在每个 episode 结束时广播事件（`event_type="episode_end"`）
   - 事件通过 `listeners` 注入
   - 训练主线程不做写文件/画图等阻塞工作

2. `lab/listeners/async_jsonl_listener.py`
   - `AsyncJsonlListener`：后台线程把事件写入 `.jsonl`
   - 主线程仅做非阻塞入队（当队列满时会丢弃旧事件以保护 FPS）
   - 通过 `close()` 触发结束并 flush

3. `lab/reporters/text_summary_reporter.py`
   - `TextSummaryReporter`：离线读取 `.jsonl`
   - 只聚合 `event_type="episode_end"` 的核心指标
   - 生成终端输出，并可选择写 `summary.txt`

### 3. Online 事件 Data Contract（events.jsonl）
落盘文件采用 JSON Lines 格式：文件每一行都是一个独立 JSON 对象。

字段标准化约定（强制）：
- `schema_version`：字符串，例如 `"1.0"`
- `run_id`：本次训练 run 的 UUID（所有行共享同一个 run_id）
- `event_type`：`"step"` 或 `"episode_end"`

核心指标字段（episode 粒度）：
- `episode_end` 行必须包含：
  - `episode`
  - `steps`（episode 内实际走过的步数）
  - `success`（来自 `info["success"]` 的严格语义）

事件类型：`step`
- `event_type="step"`
- `episode`：当前 episode 索引
- `step`：当前 step 索引（从 0 开始）
- `steps`：当前累计步数（= `step + 1`）
- `success`：当前步的 success（终止步才可能为 True，非终止通常为 False）
- `done`：是否终止
- `state` / `next_state` / `action`：直接透传当前交互要素（可为任意 JSON 可序列化对象）
- `info`：`step_result.info` 的字典快照（若为 None 则为空字典）

事件类型：`episode_end`
- `event_type="episode_end"`
- `episode`：当前 episode 索引
- `steps`：episode 实际步数
- `success`：最终成功语义
- `path`：是否记录由 `StandardTrainer(record_path=...)` 决定；未记录时可为 `null`

示例（简化）：
```json
{"schema_version":"1.0","run_id":"...","event_type":"episode_end","episode":3,"steps":17,"success":true,"path":[[0,0],[0,1]]}
```

### 4. Offline Reporter 输出
本次 `TextSummaryReporter` 的聚合结果包括：
- `Total Episodes`
- `Success Rate`（成功率）
- `Average Steps`（平均步数）
- 成功 episode 数、失败 episode 数

如果传入 `--summary-out`，会把同样内容写入 `summary.txt`。

### 5. 使用说明（最小闭环）
1. 生成事件落盘（Online -> jsonl）
```bash
python -m lab.cli.run_standard_trainer ^
  --episodes 10 ^
  --max-steps 50 ^
  --map-name level_01_trap_maze ^
  --agent-name greedy --epsilon 0.1 ^
  --output-jsonl lab_v2_results/standard/events.jsonl
```

说明：
- `--map-name` 直接使用 `.map` stem 或内置地图名（如 `open_5x5`）
- `--env-name` 默认 `grid_basic`
- `--agent-name` 默认 `greedy`

2. 离线生成战报（jsonl -> summary.txt）
```bash
python -m lab.cli.run_reporter ^
  --events-jsonl lab_v2_results/standard/events.jsonl ^
  --summary-out lab_v2_results/standard/summary.txt
```

3.（可选）只跑 Barebones 以最快观察 success 语义
```bash
python -m lab.cli.run_barebones ^
  --episodes 5 --max-steps 50 ^
  --map-name level_01_trap_maze ^
  --agent-name greedy --epsilon 0.1
```

### 6. 扩展点（后续 Reporter / Listener）
扩展原则：
- 新 Listener：实现 `lab/listeners/base.py::Listener` 并注册到 `lab/listeners/registry.py`
- 新 Reporter：实现 Reporter（读取标准化 events.jsonl）并注册到 `lab/reporters/registry.py`

只要保持 `events.jsonl` 的 Data Contract 字段名不变，Reporter 就可以独立演进。

