# 计划演进记录：2026-04-03

## 触发事件

原计划（2026-03-31）设计为 Python 原型 + CST MCP 工具直接调用，架构本身无偏差。但在 real_mode 端到端测试中发现 `mcp_bridge.CSTResultsBridge` 封装层引入的状态问题，导致 `get_1d_result` 报 "tree path not found"，而直接调 `cst_results_mcp` 可以成功读取。

## 本次修改决策

### 1. 架构决策：逐步迁移到 Skill 驱动

**决策**：在 Skill/Agent 层直接编排 MCP 工具调用，将 Python 胶水层（`orchestrator.py` + `CSTAdapter`）视为过渡期遗留，逐步用 Skill 工作流替换。

**核心原则**：
- Skill 只负责编排工作流（判断条件、下一步调什么工具）
- 禁止一次性全改，必须逐步替换，边改边验证
- 逐步将 Python 逻辑（采样/评分/入库）迁移到 Skill 嵌套的 Python 脚本
- Skill 数量最小化，功能在 Skill 内部按分支组织

### 2. 渐进路径（三步）

#### Step 1（当前）：修通 real_mode 端到端 + 建立 Skill 骨架
- 去掉 `mcp_bridge` 绕路：直接在 `CSTAdapter` 中引用 `cst_results_mcp` / `advanced_mcp`
- 解决 `get_1d_result` 跨调用状态问题（`allow_interactive=True` + `run_id=1` 直读）
- 新建 `cst-antenna-optimizer` Skill（SKILL.md + scripts/ 嵌套）
- 验证 dry_run 和 real_mode 都能端到端跑通

#### Step 2：DB 操作封装为 MCP 工具
- 将 SQLite 操作封装为 MCP 工具（task_repo / run_repo / report_repo）
- Skill 内直接调 DB 工具，去掉 Python storage/ 胶水

#### Step 3：扩展优化策略
- Stratified sampling / 多目标评分 / 报告生成等

### 3. 本次代码修改清单

#### 修改文件
| 文件 | 修改内容 |
|------|---------|
| `result_reader.py` | 重写 `read_farfield_export`：修复列索引错位（header split 17 tokens vs data 8 tokens，通过括号段偏移修正） |
| `orchestrator.py` | `project_copy_path` 加 `.resolve()` 得绝对路径 |
| `cst_adapter.py` | 仿真后强制 save_project()，results 层 close+open(allow_interactive=True) 刷新 session |
| `default_config.json` | `save_project_after_simulation: true`（强制保存以传播仿真结果到磁盘） |

#### 今日发现（已修复）
| 问题 | 根因 | 修复方案 |
|------|------|---------|
| `get_1d_result` 报 "tree path not found" | `mcp_bridge` 封装层跨调用状态问题 | 去掉 bridge，直接调 `cst_results_mcp` |
| 仿真结果无法被 results 层读取 | modeler/results 是不同 COM session，仿真结果在 modeler 内存不自动共享 | 仿真后强制 `save_project()`，results 层 close→open(allow_interactive=True) 刷新 |
| 历史运行失败 | 历史日志显示 GUI 锁定工程，`allow_interactive=False` 无法关联 | results 层统一 `allow_interactive=True` 关联 GUI session |

### 4. Skill 结构规划

```
cst-antenna-optimizer/
├── SKILL.md               # 工作流编排（判断 + 工具调用序列）
└── scripts/
    ├── optimizer_loop.py  # 优化循环主逻辑
    ├── sampler.py         # 参数采样（random / stratified）
    ├── scorer.py           # 综合评分
    └── evaluator.py        # 指标计算
```

### 5. 待验证目标

- [x] dry_run 端到端跑通
- [ ] real_mode 端到端跑通（S11 读到、farfield 导出成功、评分入库、报告生成）
- [x] Skill 骨架建立并可被 Streamlit UI 触发

---

## 历史版本

- `2026-03-31-antenna-optimizer-dev-guide.md`：原始设计文档
