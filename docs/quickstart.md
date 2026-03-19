# 快速开始（当前实现）

本项目当前以 `Trainer -> Listener -> Reporter` 为主线，通过一个 JSON 配置一次性驱动整条流水线。

## 1) 准备 pipeline config

创建一个类似下面的 `config.json`（示例：5 个 episode，事件写入 `events.jsonl`，离线战报写入 `summary.txt`）：

```json
{
  "episodes": 5,
  "env": { "name": "grid_basic", "kwargs": { "map_name": "open_5x5" } },
  "agent": { "name": "greedy", "kwargs": { "seed": 1, "epsilon": 0.0 } },
  "trainer": { "name": "standard", "kwargs": { "max_steps": 20, "record_path": false } },
  "listeners": [
    { "name": "async_jsonl", "kwargs": { "output_file": "events.jsonl" } }
  ],
  "reporters": [
    { "name": "text_summary", "kwargs": { "source_file": "events.jsonl", "output_file": "summary.txt" } }
  ]
}
```

说明：`output_file` / `source_file` 使用相对路径时，会被解析到本次 `run` 的目录下。

## 2) 运行

```bash
python -m lab.cli.run --config ./config.json
```

运行后会自动生成一个目录，例如：

- `lab_v2_results/runs/RUN_001/`

并把以下文件放进去：
- `config.json`（config 快照）
- `events.jsonl`（训练事件落盘）
- `summary.txt`（离线聚合结果）

## 3) 查看结果

直接打开 `runs/<RUN_xxx>/summary.txt` 即可。

