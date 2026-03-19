## 今天地图模块的实现说明（Element/注册/.map 解析/物理裁判）

本说明聚焦“地图与环境层”的实现，覆盖今天加入的关键机制：
- Element 注册系统（`ElementRegistry` + 内置元素）
- `.map` 沙盘文件解析（`map_file_parser.py`）
- GridMap 的元素网格查询接口（`GridMap.get_element_at/get_numeric_code_at`）
- GridWorldEnvironment 的纯物理 step 逻辑（passable/interact + Immediate Termination）

本次改动遵循你的小步快跑策略：
- 只改地图与环境/元素层
- Trainer/Agent/Logger/Metrics 暂不做连锁重构

### 1. Element 与注册中心（`lab/envs/grid/elements.py`）
核心契约（元素类层面的 contract）：
- `symbol`：用于 `.map` 文件解析
- `numeric_code`：用于 Agent/观测中的数字编码
- `is_passable()`：决定该格子是否允许进入
- `interact()`：在“成功进入该格子后”被环境调用
  - 返回形如：`{"terminal": bool, "success": bool, "info": {...}}`

内置元素（当前版本）：
- `#`：`WallElement`（`is_passable=False`）
- `.`：`EmptyElement`（可通行，`interact` 不终止）
- `S`：`StartElement`（可通行，不终止）
- `G`：`GoalElement`
  - `interact()` 返回 `terminal=True, success=True`
- `x`：`TrapElement`
  - `interact()` 返回 `terminal=True, success=False`（立即失败）

### 2. `.map` 文件格式与解析（`lab/envs/grid/map_file_parser.py`）
文件结构分两段：
- `[Metadata]`：键值对（至少要有 `width` 与 `height`）
- `[Sandbox]`：符号矩阵

Sandbox 行支持两种写法：
1) 空格分隔：`# # . x G`
2) 不带空格（逐字符）：`##..xG#`

解析时会强制校验：
- `width/height` 必须存在且可解析为整数
- Sandbox 行数必须等于 `height`
- 每行 token 数必须等于 `width`
- `S` 和 `G` 必须各恰好出现一次（`start_count==1` 且 `goal_count==1`）

解析产物：
- `GridMap(elements=...)`，其中元素存的是“元素类”（class），环境/GUI 通过 class attribute/method 读 `symbol/numeric_code/is_passable/interact`

### 3. GridMap 的全局查询接口（`lab/envs/grid/grid_map.py`）
今天的关键点是把“元素查询”作为接口暴露出去，给 Agent 的 FOV/数字观测留位置：

- `grid.get_element_at((x, y)) -> ElementClass`
- `grid.get_numeric_code_at((x, y)) -> int`

也保留了兼容方法：
- `grid.is_wall(pos)`：底层仍通过元素 passable 推导 walls 集合

这样你后续在 Agent 侧就可以直接：
- 用 `numeric_code` 做“全局数字地图”
- 在需要时由 Agent 自己切片成 FOV

### 4. 物理环境裁判 step 语义（`lab/envs/grid/environment.py`）
`GridWorldEnvironment.step(action)` 的逻辑是“极纯粹”的物理裁判：
1. 计算候选坐标 `candidate_pos = current + action(dx,dy)`
2. 若越界或不可通行（`not elem.is_passable()`）：
   - 保持原地
   - `step_result.info["blocked"]=True`
3. 若可通行：
   - 成功移动到目标格
   - 调用 `elem.interact()`
4. Immediate Termination：
   - `done = outcome["terminal"]`
   - 不再并行判断是否到达 `goal`
5. success 由元素交互结果提供：
   - 环境把 `outcome["success"]` 写入 `step_result.info["success"]`

reward：
- 本次保持“轻量兼容”：`StepResult.reward` 字段仍存在，但环境返回固定 `0.0`
- 物理层剔除 reward 概念，避免外部模块连锁改动

### 5. 地图注册与加载（`lab/envs/grid/maps.py`）
运行时地图来源包括：
- 内置地图（仍保留 `open_5x5`、`random_blocks_10x10`）
- 自动注册：从仓库根目录 `maps/*.map` 自动注册，注册名为文件 `stem`

因此 `.map` 文件只要放到 `maps/` 目录：
- 文件名 `level_01_trap_maze.map`
- 就可以在 config 里使用 `map_name=level_01_trap_maze`

### 6. 怎么新增一个元素/地图（最小流程）
新增元素（修改 `elements.py`）：
1. 新建 `MyElement(BaseElement)`，定义 `symbol/numeric_code/_is_passable`
2. 实现 `interact()` 返回 `terminal/success/info`
3. 把类注册到 `build_default_element_registry()` 中
4. 若你希望 GUI 颜色正确：在 `manual_play.py` 的颜色表增加该 `symbol -> color`

新增地图（新增 `maps/*.map`）：
1. 复制现有 `.map` 模板
2. 写好 `Metadata.width/height`
3. 在 `[Sandbox]` 中使用元素符号放置格子
4. 保证 `S` 与 `G` 各出现一次
5. 运行：
   - GUI：`--map-name <stem>`
   - 或训练：在 env 配置里写 `map_name=<stem>`

### 7. 推荐的调试脚本（可选使用）
- `lab/envs/grid/debug_map_check.py`：批量校验 `.map` 不变量（尺寸、start/goal、可选可达性）
- `lab/envs/grid/debug_rollout.py`：用环境做最小 rollout，观察 `done` 与 `info["success"]`

这两个脚本都只用地图/环境层，不依赖 Trainer/Agent 训练流程。

