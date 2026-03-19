## 地图运行器与地图设计规则

本文件说明当前 2D 栅格最短路径任务中：
- **地图运行器（GridWorldEnvironment）** 的行为规则；
- **地图设计约束与推荐规范**；
- 与后续地图生成器对接时需要保持的不变量。

本说明基于当前实现（`GridMap` + `GridWorldEnvironment`），随着代码演进可在此补充或修正。

---

### 1. 地图运行器（GridWorldEnvironment）的行为

当前的地图运行器实现位于：
- `lab/envs/grid/grid_map.py`：`GridMap`
- `lab/envs/grid/environment.py`：`GridWorldEnvironment`

#### 1.1 状态与坐标系

- 状态表示为整数坐标对 `Coord = (x, y)`：
  - `x`：水平方向，从左到右，取值范围 \[0, width - 1\]
  - `y`：垂直方向，从上到下，取值范围 \[0, height - 1\]
- `GridMap` 中的字段：
  - `width, height`：网格宽和高。
  - `start`：起点坐标。
  - `goal`：终点坐标。
  - `walls: Set[Coord]`：障碍集合。
- 有效坐标需满足：
  - `in_bounds((x, y))`：在网格范围内。
  - `not is_wall((x, y))`：不是障碍。

#### 1.2 动作空间

- `GridWorldEnvironment.get_actions(state)` 返回一组离散动作：
```python
[(0, -1), (0, 1), (-1, 0), (1, 0)]
```

- 含义：
  - `(0, -1)`：向上
  - `(0, 1)`：向下
  - `(-1, 0)`：向左
  - `(1, 0)`：向右
- Agent 的 `select_action` 函数应返回上述四个动作之一（或在空动作集时返回 `None`，环境会忽略）。

#### 1.3 状态转移与终止条件

在 `GridWorldEnvironment.step(action)` 中：

1. 当前状态为 `_state = (x, y)`，动作为 `(dx, dy)`；
2. 计算下一位置候选：`next_pos = (x + dx, y + dy)`；
3. 若 `next_pos` 越界或是墙：
   - `next_pos` 被修正为保持在原地 `_state`；
4. 更新内部状态：`self._state = next_pos`；
5. 终止判定：
   - `done = (next_pos == grid.goal)`；
6. 返回 `StepResult`：
   - `next_state = self._state`
   - `reward = step_reward`（当前为一个常数，默认为 -1.0）
   - `done = done`
   - `info = {}`（后续可按需扩展）。

> 目前没有额外的“撞墙惩罚”或“超步数惩罚”，episode 的总 cost 由 `Trainer` 控制的 `max_steps` 与 `step_reward` 共同决定。

#### 1.4 回合（Episode）控制

- `Trainer` 负责 episode 级别循环：
  - 每个 episode 调用一次 `env.reset()`，将状态置为 `grid.start`。
  - 在最多 `max_steps` 步内反复调用 `env.step(action)`。
  - 若 `done=True`，则提前结束 episode。
  - 若走满 `max_steps` 仍未到达 `goal`，episode 以失败告终。
- 训练过程中记录：
  - 路径：所有访问过的状态序列；
  - 成功标记：是否在步数上限内达到目标；
  - 步数与累积 reward。

---

### 2. 地图设计规则（当前与后续生成器共用的约束）

为了保证实验的可解释性和对比性，地图设计建议遵守以下规则。

#### 2.1 基本合法性约束

任何 `GridMap` 都必须满足：
- 起点 / 终点必须在边界内：
  - `in_bounds(start) == True`
  - `in_bounds(goal) == True`
- 起点 / 终点不能是墙：
  - `start not in walls`
  - `goal not in walls`
- 坐标唯一性：
  - `start != goal`
  - `walls` 不包含重复元素（Set 已保证）。

#### 2.2 可达性约束（推荐）

为了避免“无解地图”占据过多比例，推荐地图设计时保证：
- 从 `start` 到 `goal` 至少存在一条无障碍路径。
- 检查方式（建议在未来的地图生成器中实现）：
  - 使用 BFS / DFS 在 \[0, width-1\] × \[0, height-1\] 上搜索；
  - 允许的移动为 4 邻接，不能穿过 `walls`；
  - 若能到达 `goal`，则认为地图可达。

> 当前代码中未强制执行该检查，因此手工编写地图时需要自行遵守这一约束；未来地图生成器应默认只输出可达地图。

#### 2.3 难度与结构设计建议

为了让“涌现结构”更有分析意义，地图设计可以考虑以下维度：
- **路径多样性**：
  - 是否存在多条不同的最短路径？
  - 是否存在明显的“瓶颈点”（例如必须通过的窄通道）？
- **障碍模式**：
  - 直线走廊（long corridor）：测试 Agent 是否能长距保持方向；
  - 迷宫状结构（maze-like）：测试分叉决策与回溯行为；
  - 开放区域 + 局部障碍块（open area with blocks）：测试对局部捷径的偏好。
- **规模控制**：
  - 小地图（如 5×5）：适合快速实验与手动检查，路径短、易可视化；
  - 中等地图（如 10×10, 16×16）：适合结构涌现研究；
  - 更大地图：建议在基础结果稳定后再引入。

实际设计中，可以先手工定义少量具有代表性的地图模板（开放 / 走廊 / 单瓶颈 / 多瓶颈），再逐步引入自动生成器。

---

### 3. 地图运行与日志 / 可视化的关系

地图运行器与训练、可视化的关系目前如下：
- `Trainer`：
  - 控制 episode 循环，收集 `EpisodeResult`（路径 / 成功 / cost / steps）。
- 日志与可视化：
  - `CsvEpisodeLogger`：
    - 依据 episode 记录标量指标（成功、cost、steps）。
  - `viz.grid_plot.save_representative_path_plots`：
    - 使用 `GridMap` + `EpisodeResult.path` 用 matplotlib 绘制代表性路径（最多次数 / 最好 / 最坏）。
  - `viz.metrics.plot_all_metrics`：
    - 基于 CSV 绘制训练曲线（成功率、步数、cost）。

地图设计直接影响：
- 训练难度（成功率曲线、平均步数）；
- 路径图的形态（是否存在明显通路 / 瓶颈）；
- 未来结构服务中提取的宏、子目标等结构。

---

### 4. 未来地图生成器与本规则的接口预期

未来引入地图生成器（map generator）时，建议遵循以下接口与约定：

- **生成接口**（建议）：
```python
def generate_grid_map(
    width: int,
    height: int,
    start: Coord,
    goal: Coord,
    map_type: str,
    **kwargs,
) -> GridMap:
    ...
```

- **必须遵守的约束**：
  - 满足第 2.1 节中的基本合法性；
  - 优先满足第 2.2 节中的可达性（可通过参数控制是否允许无解地图）。

- **地图类型与参数**：
  - `map_type` 明确表征地图类别（例如 `"open"`, `"corridor"`, `"blocks_random"`, `"maze"` 等）；
  - 其他参数（如障碍密度、随机种子）应被记录到配置和日志中，以便复现实验。

> 本文件的规则旨在在“手工地图”和“自动生成地图”之间建立一致的约束，方便你在演进过程中保持环境层的稳定性和可解释性。

