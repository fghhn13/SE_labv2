## Manual Play GUI（外挂手动操控脚本）

这个 GUI 是调试/演示用的“外挂脚本”，目标是把环境当成黑盒来玩：
- GUI 只负责渲染（View）与按键监听（Controller）
- **所有状态变化都必须通过 `env.step(action)` 完成**（Model/裁判=环境）

### 位置与启动
- 脚本路径：`lab/scripts/manual_play.py`
- 运行方式（建议在仓库根目录 `lab_v2` 执行）：
  - `python -m lab.scripts.manual_play --map-name level_01_trap_maze`

### 窗口布局
- 上半部分：`tk.Canvas` 渲染整个地图网格
- 下半部分：一个两列表格（Frame）
  - 左列是字段名：`Action/done/success/blocked/info`
  - 右列是字段值，随每次按键更新

### 颜色映射（由 `elem.symbol` 决定）
GUI 遍历网格：
- `env.grid.get_element_at((x, y)).symbol` 取出符号
- 依据符号设置填充颜色，并用 `create_rectangle` 绘制每个 cell

默认映射如下：
- `#`：墙（深灰）
- `.`：空地（白色）
- `S`：起点（蓝色）
- `G`：终点（绿色）
- `x`：陷阱（红色）

角色（Agent）渲染：
- 使用 `env.state`（一个 `@property`）获得当前坐标
- 在该 cell 中画一个黄色圆形表示 FGHN

### 按键控制（仅处理明确按键）
- `w/a/s/d`：移动（分别是 `up/left/down/right`）
- `r`：重置（`env.reset()`，并清除本轮 `done` 锁）

`done` 锁定规则：
- GUI 内部维护 `self._done`
- 一旦某步返回 `step_result.done=True`，直到按 `r` 之前都不再响应移动按键

### 交互反馈来源
每次按下移动键：
1. 调用 `step_result = env.step(action)`
2. GUI 展示：
   - `step_result.done`
   - `step_result.info["success"]`（Trap 应为 `False`，Goal 应为 `True`）
   - `step_result.info["blocked"]`（如果撞墙/不可通行）
   - `step_result.info` 的完整内容

### 与当前环境语义的对齐点
- 环境终止完全依赖元素交互 `interact()` 返回的 `terminal`
- 环境把 `success` 写入 `info`，GUI 展示 `info["success"]`，从而把“done”和“成功语义”区分开

