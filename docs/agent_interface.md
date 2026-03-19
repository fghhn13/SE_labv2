# Agent 接口说明（当前实现）

本文件说明本项目中 `lab.core.interfaces.Agent` 的契约，以及如何让一个新 `Agent` 与现有 `Trainer/Listener/Reporter` 工作。

---

## 1. 契约概览

`Agent` 的职责是：在**每一步**根据 `state` 与 `env` 做出决策，并接收 `step_result` 做可选的观察/学习，最后在每个回合结束时接收 `EpisodeResult`。

协议定义在：`lab/core/interfaces.py`。

最小实现需要包含以下方法：

1. `reset(self) -> None`
   - 由 `Trainer` 在每个 episode 开始前调用。
   - 用于清空内部状态（如记忆、计数器、随机种子状态等）。

2. `select_action(self, state, env) -> action`
   - 由 `Trainer` 在每个 step 调用。
   - 返回一个 `Action`，其语义由具体环境决定（本项目目前为栅格移动动作）。
   - 推荐只从 `env.get_actions(state)` 返回的动作集合中选择；在动作集合为空时可以返回 `None`（环境应当能优雅处理）。

3. `observe(self, step_result) -> None`
   - 由 `Trainer` 在执行 `env.step(action)` 后调用。
   - `step_result` 包含：`next_state`、`reward`、`done`、`info`（本项目的 `success` 语义来自 `step_result.info["success"]`）。

4. `end_episode(self, result) -> None`
   - 由 `Trainer` 在 episode 结束后调用。
   - `result` 为 `EpisodeResult`，包含：`path`、`success`、`steps` 等。

---

## 2. 与项目流水线的关系

典型数据流由 `Trainer` 驱动：

- `env.reset() -> state`
- `agent.select_action(state, env) -> action`
- `step_result = env.step(action)`
- `agent.observe(step_result)`
- 重复直到 episode 结束
- `agent.end_episode(episode_result)`

注意：**训练循环与 IO** 由 `Trainer/Listener/Reporter` 承担；Agent 建议保持轻量，不要在 `select_action/observe` 里做文件写入/网络请求等阻塞 IO。

---

## 3. 最小可用 Agent 示例

你可以继承 `lab/agents/base.py::BaseAgent`，得到空实现（`observe/end_episode` 为 no-op），只需实现 `select_action` 即可：

```python
from __future__ import annotations

from typing import Any

from lab.core.interfaces import Environment
from lab.core.types import State, Action, StepResult, EpisodeResult
from lab.agents.base import BaseAgent


class FirstActionAgent(BaseAgent):
    def select_action(self, state: State, env: Environment) -> Action:
        actions = env.get_actions(state)
        if not actions:
            return None
        return actions[0]

    def observe(self, step_result: StepResult) -> None:
        return

    def end_episode(self, result: EpisodeResult) -> None:
        return
```

---

## 4. 与 registry / JSON config 的对接方式

1. Agent 工厂与注册表：
   - `lab/agents/registry.py` 提供：
     - `register(name, builder)`
     - `create(name, env=None, **kwargs)`

2. 当前配置驱动的入口：
   - `lab/cli/run.py` 的 pipeline 会使用 `env_registry.create(...)` 与 `agent_registry.create(...)` 创建组件。
   - pipeline 中会把 `agent.kwargs` 作为 `**kwargs` 传给 agent 的 builder。
   - 目前默认流程**不会把 env 传入 agent builder**（`agent_registry.create(..., env=None)` 的语义），因此：
     - 如果你的 agent 需要环境信息，建议在 `select_action(state, env)` 里按需读取，而不是依赖 `__init__` 时拿到 env。

3. JSON config 字段：
   - `agent.name`：在 registry 中注册的名字
   - `agent.kwargs`：builder 需要的参数字典

---

## 5. 扩展建议（保持研究可控）

- 把“决策逻辑”放在 `select_action`
- 把“状态更新/统计累积”放在 `observe`
- 把“回合级统计输出/清理”放在 `end_episode`
- 保持 Agent 可重放：尽量让随机性可由 `agent.kwargs` 里的种子控制

---

## 6. 模板 Agent 与快速上手

仓库内提供可复制的模板文件：`lab/agents/template_agent.py`。

- **类名**：`TemplateAgent`
- **注册名**：`template`（已在 `lab/registry_defaults.py` 中注册）
- **策略**：当前为“选第一个合法动作”；可改为随机/贪心等。

**使用步骤：**

1. 复制 `template_agent.py` 为例如 `my_agent.py`，重命名类为 `MyAgent`。
2. 在 `lab/registry_defaults.py` 中：import 新类、写 `build_my_agent(**kwargs)`、`agent_registry.register("my_agent", build_my_agent)`。
3. 在 JSON config 里使用：
   ```json
   "agent": { "name": "my_agent", "kwargs": { "seed": 42 } }
   ```

**用模板直接跑 pipeline（示例）：**

```json
"agent": { "name": "template", "kwargs": { "seed": 1 } }
```

然后执行：`python -m lab.cli.run --config your_config.json`。

