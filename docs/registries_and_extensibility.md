# 注册表与可扩展点（当前实现）

本文档从软件工程角度梳理：**哪些地方已有注册表或可扩展**，以及**建议的改进方向**。

---

## 一、已有注册表 / 可扩展点

| 模块 | 注册表位置 | 契约 | 扩展方式 | 默认注册来源 |
|------|------------|------|----------|--------------|
| **Agent** | `lab/agents/registry.py` | `Agent` (Protocol), `AgentBuilder` | `register(name, builder)` → `create(name, env=?, **kwargs)` | `lab/registry_defaults.py::register_all_defaults()` |
| **Environment** | `lab/envs/registry.py` | `Environment` (Protocol), `EnvBuilder` | `register(name, builder)` → `create(name, **kwargs)` | 同上 |
| **Map** | `lab/envs/grid/maps.py` | `MapBuilder` | `register_map(name, builder)` → `get_map(name)` | `register_builtin_maps()` + `maps/*.map` 自动注册 |
| **Element** | `lab/envs/grid/elements.py` | `ElementRegistry`（实例）, `BaseElement` | `reg.register(element_cls)` | `build_default_element_registry()`（解析 .map 时用） |
| **Trainer** | `lab/trainer/registry.py` | `TrainerBuilder` | `register(name, builder)` → `create(name, env=, agent=, listeners=?, **kwargs)` | `standard_trainer.py` 末尾 import 时自动注册 |
| **Listener** | `lab/listeners/registry.py` | `Listener` (Protocol), `ListenerBuilder` | `register(name, builder)` → `create(name, **kwargs)` | `async_jsonl_listener.py` 末尾 import 时自动注册 |
| **Reporter** | `lab/reporters/registry.py` | `Reporter` (Protocol), `ReporterBuilder` | `register(name, builder)` → `create(name, source_file=, output_file=?, **kwargs)` | `text_summary_reporter.py` 末尾 import 时自动注册 |

**仅接口、无注册表：**

- `lab/core/interfaces.py`：`Environment`、`Agent`。

---

## 二、软件工程建议

### 1. 默认注册集中到一处（避免 CLI 重复）
**现状：** 默认 env + agent + 内置 map 注册已集中在 `lab/registry_defaults.py::register_all_defaults()`，两个 CLI 都直接调用它。

### 2. 注册表约定与 create 签名

**现状：** 各 registry 的 `create()` 签名不一致（如 Reporter 必须 `source_file`，Trainer 必须 `env`/`agent`）。

**建议：**  
- 保持“按名创建 + 关键字参数”的总体约定，便于将来用 JSON 配置驱动。  
- 在 `docs/` 或各 registry 模块 docstring 中简短写明：每个 `create(name, ...)` 的必选/可选参数，以及 config 中对应字段名（例如 `reporter.source_file`）。这样后续做“完全配置化”时不会猜参数。

### 4. Trainer / Listener / Reporter 的“自动注册”

**现状：** 通过在各实现文件末尾 `import registry; register("...", builder)` 做 side-effect 注册，依赖“有人 import 过该模块”（例如 `lab/trainer/__init__.py` 里 import `standard_trainer`）。

**建议：** 保持现状即可；若后续实现变多，可考虑：  
- 在单一入口（如 `lab/registry_defaults.py`）里显式 import 所有需要注册的实现模块，使“默认可用组件”一目了然；或  
- 用 setuptools entry_points 做可选发现（成本较高，当前规模不必上）。

### 5. 类型与返回值

**现状：** `TrainerBuilder = Callable[..., Any]`，`create()` 返回 `Any`。

**建议：** 若希望类型更清晰，可把 `TrainerBuilder` 改为返回 `Union[BarebonesTrainer, StandardTrainer]` 或定义 `Trainer` 基类/Protocol，让 IDE 和静态检查能推断返回值。当前规模下非必须。

### 6. 配置驱动时的组装顺序

**现状：** 当前完全由 CLI 参数驱动；若未来再次引入 JSON 配置，会涉及：按名创建 env → agent → listeners → trainer，再 run；以及 reporter 按名创建并指定 source_file。

**建议：** 保持各 `create(name, **kwargs)` 与“config 中一段 name + 键值对”一一对应；必要时在文档或示例 config 中写明组装顺序（env → agent → listeners → trainer；训练结束后 reporter 读 events.jsonl）。这样“完全配置化”时只需一个组装函数，而不必改各 registry 接口。

---

## 三、小结

- **已有且可扩展：** Agent、Environment、Map、Element、Trainer、Listener、Reporter 七处；env/agent 默认注册已集中在 `lab/registry_defaults.py`，其余组件按模块内/地图扫描实现自动注册。  
- **已完成：** 默认注册集中（env/agent + register_builtin_maps）以及移除结构服务接口。
- **可选/后续：** 进一步加强 Reporter/Listener create 参数契约文档、收紧 Trainer 返回值类型、以及为将来 config 驱动预留组装顺序说明。
