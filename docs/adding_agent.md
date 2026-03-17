## 新增模型 / Agent 的推荐流程

本文件说明：在当前实验架构下，如何**新增一个 Agent（模型）并完成训练与结果分析**。  
目标是保证流程统一、结果目录清晰，便于后续对比不同模型。

---

### 1. 命名约定与总体思路

- **Agent 名称**：在 `experiments/*.json` 中通过 `agent.name` 指定，例如 `"random"`、`"greedy"`、`"struct_agent"`。
- **注册点**：所有可用 Agent 都需要在 `lab/agents/registry.py` 中注册一个 builder。
- **结果目录**：
  - 训练日志、指标图、路径图会自动归档到：
    - `lab_v2_results/<agent_name>/...`
  - 这样，同一个实验配置下，只要切换 `agent.name`，就能在不同子文件夹下得到可对比的结果。

新增一个 Agent 的完整流程可以概括为：

1. 在 `lab/agents` 中实现 Agent 类；
2. 在 `lab/agents/registry.py` 中注册；
3. 在 CLI 启动前的 `_register_defaults` 中确保有默认注册（或在别处集中注册）；
4. 在 `experiments/*.json` 中配置 `agent.name` 与参数；
5. 使用 `python -m lab.cli.run_and_plot ...` 跑训练并自动保存图表。

下面详细展开。

---

### 2. 在 `lab/agents` 中实现新的 Agent

#### 2.1 选择基类与接口

- 推荐继承 `lab.agents.base.BaseAgent`：
  - 已经实现了空的 `reset` / `observe` / `end_episode`，只需实现核心的：
    - `select_action(self, state, env) -> Action`
- 也可以直接实现 `lab.core.interfaces.Agent` 协议，但建议统一使用 `BaseAgent`，便于维护。

#### 2.2 建议的 Agent 结构（示意）

在 `lab/agents/` 下新建一个文件，例如 `greedy_agent.py`，实现：

- 构造函数：接收必要的超参数（如 `seed`、`epsilon` 等）；
- `select_action`：根据当前状态与环境信息输出一个动作；
- 视情况实现：
  - `reset`：在每个 episode 开始时重置内部状态；
  - `observe`：在每个 step 之后更新内部统计或学习；
  - `end_episode`：在一个 episode 结束后做收尾处理。

> 要点：Agent 不控制训练循环，只做“给定 state 和 env，如何选 action”这一件事。

---

### 3. 在 `lab/agents/registry.py` 注册新 Agent

`lab/agents/registry.py` 维护了一个全局注册表，用于通过字符串名称创建 Agent。  
新增 Agent 时，需要：

1. 在顶部导入你的 Agent 类；
2. 在某个初始化逻辑中（目前在 `lab/cli/run_experiment.py::_register_defaults` 中）注册：

```python
from lab.agents.greedy_agent import GreedyAgent

def build_greedy_agent(**kwargs: Any) -> GreedyAgent:
    return GreedyAgent(**kwargs)

agent_registry.register("greedy", build_greedy_agent)
```

- 注册后，可以在 config 中通过 `"name": "greedy"` 来引用这个 Agent。
- builder 的 `**kwargs` 来源于实验配置中的 `agent` 字段（见下一节）。

---

### 4. 在实验配置中指定 Agent 与超参数

以 `experiments/basic_grid_shortest_path/config.json` 为例，`agent` 区段目前类似：

```json
"agent": {
  "name": "random",
  "seed": 42
}
```

如果新增了一个 `greedy` Agent，可以按如下方式配置：

```json
"agent": {
  "name": "greedy",
  "seed": 42,
  "epsilon": 0.1
}
```

要点：

- `name`：对应注册时使用的字符串（如 `"greedy"`）。
- 其他键（如 `seed`、`epsilon`）会通过 `agent_registry.create` 传入 builder：
  - `builder(env=env, **agent_cfg)` 或 `builder(**agent_cfg)`（具体实现见当前代码）。

---

### 5. 训练与结果路径（按模型名分目录）

`lab/cli/run_experiment.py` 中会根据 `agent.name` 自动组织结果目录：

- 配置中写的是一个**基准路径**，例如：

```json
"logging": {
  "csv_path": "lab_v2_results/basic_grid_shortest_path.csv"
}
```

- 实际运行时，路径会变为：

```text
lab_v2_results/<agent_name>/basic_grid_shortest_path.csv
```

- 对应的衍生结果也会进入同一子目录：
  - 代表性路径图：

    ```text
    lab_v2_results/<agent_name>/maps/most_frequent.png
    lab_v2_results/<agent_name>/maps/best.png
    lab_v2_results/<agent_name>/maps/worst.png
    ```

  - 指标曲线图（使用 `run_and_plot` 脚本后生成）：

    ```text
    lab_v2_results/<agent_name>/plots/success_rate.png
    lab_v2_results/<agent_name>/plots/steps_cost.png
    ```

> 因此，**同一个 config** 下只要切换 `agent.name`，就会自动在不同子文件夹下积累该模型的训练结果，便于对比。

---

### 6. 推荐的对比实验流程

当你要比较多个模型（多个 Agent）时，推荐流程如下：

1. **实现并注册所有待比较的 Agent**
   - 在 `lab/agents/` 下分别实现，例如 `RandomAgent`、`GreedyAgent`、`StructAwareAgent`。
   - 在 `agents/registry.py` 和 `_register_defaults()` 中注册 `"random"`、`"greedy"`、`"struct_aware"` 等名称。

2. **准备一个或多个实验配置**
   - 例如 `experiments/basic_grid_shortest_path/config.json`。
   - 其他字段（环境、训练步数等）保持不变。

3. **循环修改 `agent.name` 并运行一键脚本**

   ```bash
   # random 模型
   # config.json 中 agent.name = "random"
   python -m lab.cli.run_and_plot experiments/basic_grid_shortest_path/config.json --window 10

   # greedy 模型
   # 把 config.json 中 agent.name 改成 "greedy"
   python -m lab.cli.run_and_plot experiments/basic_grid_shortest_path/config.json --window 10
   ```

4. **对比结果**
   - CSV 与图像按模型名分目录存放：
     - `lab_v2_results/random/...`
     - `lab_v2_results/greedy/...`
     - 将 `plots/` 下的图直接并排查看即可。

---

### 7. 小结

新增一个模型 / Agent 的关键点：

- **实现**：在 `lab/agents` 中实现一个类（推荐继承 `BaseAgent`），实现 `select_action` 等方法。
- **注册**：在 `agents/registry.py` + `_register_defaults` 中注册一个 builder，并取一个清晰的字符串名称。
- **配置**：在 `experiments/*.json` 中设置 `agent.name` 与超参数。
- **运行**：使用 `python -m lab.cli.run_and_plot <config>` 一键完成训练与画图。
- **结果组织**：所有训练结果都会自动进入 `lab_v2_results/<agent_name>/...` 子目录，便于长期维护和模型对比。

