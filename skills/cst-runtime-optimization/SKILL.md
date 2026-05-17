---
name: cst-runtime-optimization
description: 当用户要求使用 CLI/runtime 执行 CST 参数优化循环、S11 指标迭代、多轮仿真对比时调用此 Skill。本 Skill 依赖 cst-runtime-cli 提供基础设施，不携带 runtime scripts，所有 CLI 调用走 base skill 的 scripts/cst_runtime_cli.py。
---

# CST Runtime 优化 Skill

## 定位

本 Skill 专注 CST 参数优化闭环，依赖 `cst-runtime-cli` 提供底层基础设施。

- 不携带 `scripts/` 或 `cst_runtime/` 源码；所有 CLI 调用走 base skill 的 `python <base-skill-root>\scripts\cst_runtime_cli.py ...`
- 负责定义优化循环流程、早停判断、参数迭代策略、S11 对比和审计落盘。
- 所有生产任务使用标准 `tasks/task_xxx_slug/runs/run_xxx/{projects,exports,logs,stages,analysis}` 结构。
- 参考工程一律视为只读蓝本，操作前必须先通过 base skill 的 `prepare-run` 创建工作副本。

## 依赖声明

本 Skill 不实现任何 CST 操作，以下工具全部由 `cst-runtime-cli` 提供：

| 职责 | CLI 工具 |
|---|---|
| run 创建 | `prepare-run`、`get-run-context` |
| 审计 | `record-stage`、`update-status` |
| 进程管理 | `cleanup-cst-processes`、`cst-session-open`、`cst-session-close` |
| 身份/锁 | `verify-project-identity`、`wait-project-unlocked` |
| 参数读写 | `list-parameters`、`change-parameter` |
| 仿真 | `start-simulation-async`、`is-simulation-running`、`wait-simulation` |
| 结果读取 | `list-run-ids`、`get-parameter-combination`、`get-1d-result` |
| S11 对比 | `generate-s11-comparison` |

调用时 `<skill-root>` 指向 `cst-runtime-cli` 的目录，而非本 Skill 目录。

## 触发条件

使用本 Skill 的情况：

- 用户明确要求执行参数优化循环、S11 指标迭代或多轮仿真对比。
- 任务需要实现"仿真 → 读结果 → 解析指标 → 判断是否达目标 → 达则 break，不达则继续"的自动化循环。
- 需要定义早停条件（target S11 ≤ 阈值、轮数上限、用户指定指标）。
- 需要生成可审计的优化调用链，落到 run 的 `logs/` 和 `stages/`。

不要使用本 Skill 的情况：

- 只需要单次仿真、结果读取或远场导出（使用 `cst-runtime-cli`）。
- 几何建模、材料、边界、网格、结构创建。

## CLI 调用原则

- 入口固定为 base skill：`python <base-skill-root>\scripts\cst_runtime_cli.py ...`
- 简单发现命令可直接调用：`doctor`、`usage-guide`、`list-tools`、`list-pipelines`、`describe-tool`、`describe-pipeline`、`args-template`、`pipeline-template`。
- 带路径或复杂参数的命令优先使用 `args-template` 生成 JSON，再用 `--args-file` 调用。
- 所有 `project_path`、`source_project`、`working_project` 都必须指向具体 `.cst` 文件。
- `change-parameter` 的参数名固定为 `name` 和 `value`。
- 每次调用必须检查 JSON 返回的 `status`；不得只看退出码。
- S11 原始数据是复数字典 `{'real': ..., 'imag': ...}`，不是 dB 值；必须先 `math.hypot(real, imag)`，再做 `20*log10()`。

## 自动化优化循环红线

- 自动优化循环每轮执行流程必须包含早停判断：`仿真 → 读结果 → 解析指标 → 判断是否达目标 → 达则 break，不达则继续`
- "执行"和"评估"不得拆分为两个独立阶段；目标指标必须在每轮循环体内部实时解析和判断。
- 自动化脚本或管道定义的停止条件（target S11 阈值、轮数上限、或用户指定阈值）必须在执行循环代码中显式实现，不得仅写在 config.json 或文档中。
- 若未实现早停导致超过目标后继续执行额外轮次，任务输出必须明确标记为 `overrun` 并说明浪费了多少轮。

## 优化闭环流程

### 1. 创建 run

输入 task 目录应包含 `task.json`，其中至少有 `source_project`。

```powershell
$task = "C:\path\to\tasks\task_xxx"
@{ task_path = $task } |
  ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\prepare_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py prepare-run --args-file "$task\prepare_args.json"
```

成功后读取上下文：

```powershell
python <base-skill-root>\scripts\cst_runtime_cli.py get-run-context --args-file "$task\prepare_args.json"
```

后续所有路径使用返回的 `working_project`、`exports_dir`、`logs_dir`。

### 2. 打开并确认工程身份

```powershell
@{ project_path = $workingProject } |
  ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\project_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py cst-session-open --args-file "$task\project_args.json"
python <base-skill-root>\scripts\cst_runtime_cli.py verify-project-identity --args-file "$task\project_args.json"
python <base-skill-root>\scripts\cst_runtime_cli.py list-parameters --args-file "$task\project_args.json"
```

若返回 `ambiguous_open_projects`，必须先关闭无关 CST 工程；禁止继续写参数。

### 3. 修改参数

```powershell
@{
  project_path = $workingProject
  name = "R"
  value = 0.102
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\change_parameter_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py change-parameter --args-file "$task\change_parameter_args.json"
python <base-skill-root>\scripts\cst_runtime_cli.py list-parameters --args-file "$task\project_args.json"
```

必须读回确认参数生效后再启动仿真。

### 4. 异步仿真与轮询

```powershell
python <base-skill-root>\scripts\cst_runtime_cli.py start-simulation-async --args-file "$task\project_args.json"
```

轮询示例：

```powershell
for ($poll = 1; $poll -le 80; $poll++) {
  $raw = python <base-skill-root>\scripts\cst_runtime_cli.py is-simulation-running --args-file "$task\project_args.json"
  $json = ($raw -join "`n") | ConvertFrom-Json
  if ($json.status -ne "success") { throw ($raw -join "`n") }
  if ($json.running -eq $false) { break }
  Start-Sleep -Seconds 15
}
```

不要默认用同步 `start-simulation`；同步调用更容易超时。

### 5. 保存、关闭、解锁

```powershell
python <base-skill-root>\scripts\cst_runtime_cli.py save-project --args-file "$task\project_args.json"

@{
  project_path = $workingProject
  save = $false
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\close_project_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py cst-session-close --args-file "$task\close_project_args.json"

@{
  project_path = $workingProject
  timeout_seconds = 30
  poll_interval_seconds = 0.5
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\wait_unlock_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py wait-project-unlocked --args-file "$task\wait_unlock_args.json"
```

若 `save-project` 失败但仿真已完成，不要反复保存；关闭后用 results `list-run-ids` 判断结果是否已落盘。

收尾时只允许通过白名单清理 CST 进程：

```powershell
@{
  project_path = $workingProject
  dry_run = $false
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\cleanup_cst_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py cleanup-cst-processes --args-file "$task\cleanup_cst_args.json"
```

强杀白名单固定为：`cstd`、`CST DESIGN ENVIRONMENT_AMD64`、`CSTDCMainController_AMD64`、`CSTDCSolverServer_AMD64`。若这些进程返回 `Access is denied`，且工程已 `close(save=False)`、当前 run 无 `.lok`，只能记录为 `nonblocking_access_denied_residual`，禁止声称已杀掉。

### 6. 刷新 results 并读取最新结果

```powershell
@{
  project_path = $workingProject
  treepath = "1D Results\S-Parameters\S1,1"
  module_type = "3d"
  max_mesh_passes_only = $false
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\list_run_ids_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py list-run-ids --args-file "$task\list_run_ids_args.json"
```

选择最新可用 `run_id` 后导出：

```powershell
@{
  project_path = $workingProject
  treepath = "1D Results\S-Parameters\S1,1"
  module_type = "3d"
  run_id = $runId
  export_path = "$exportsDir\s11_run$runId.json"
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\get_1d_result_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py get-1d-result --args-file "$task\get_1d_result_args.json"
```

读取参数组合：

```powershell
@{
  project_path = $workingProject
  run_id = $runId
  module_type = "3d"
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\get_parameter_combination_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py get-parameter-combination --args-file "$task\get_parameter_combination_args.json"
```

### 7. 生成 S11 对比

```powershell
@{
  file_paths = @("$exportsDir\s11_run0.json", "$exportsDir\s11_run1.json")
  output_html = "$exportsDir\s11_comparison.html"
  page_title = "S11 Comparison"
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\s11_comparison_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py generate-s11-comparison --args-file "$task\s11_comparison_args.json"
```

### 8. 阶段记录与状态更新

每轮至少记录参数、run_id、指标文件、HTML 输出、异常和耗时。

```powershell
@{
  task_path = $task
  run_id = "run_001"
  stage = "cli_runtime_iteration"
  status = "completed"
  message = "CLI runtime iteration completed"
  details_json = '{"parameter_changes":{"R":0.102},"result_run_ids":[0,1]}'
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\record_stage_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py record-stage --args-file "$task\record_stage_args.json"
```

```powershell
@{
  task_path = $task
  run_id = "run_001"
  status = "validated"
  stage = "cli_runtime_iteration"
  output_files_json = '{"s11_json":"exports/s11_run1.json","s11_comparison_html":"exports/s11_comparison.html"}'
} | ConvertTo-Json -Depth 8 |
  Set-Content -LiteralPath "$task\update_status_args.json" -Encoding UTF8

python <base-skill-root>\scripts\cst_runtime_cli.py update-status --args-file "$task\update_status_args.json"
```

## 错误处理

- `workspace_not_initialized`：先运行 `init-workspace`，或用 `--workspace` / `CST_WORKSPACE` 指向已初始化工作区。
- `source_project_missing`：`task.json` 或入参中的 `source_project` 缺失、路径不存在，或不是可用 `.cst` / `.prj` 工程；不要继续 `prepare-run`。
- `production_dependency_missing`：真实 CST 生产命令缺少 `cst.interface` / `cst.results` 等依赖；发现类命令仍可用，生产动作必须先修 CST Python 库或 session 环境。
- `invalid_json_args`：不要修 CLI，改用 `--args-file`。
- `ambiguous_open_projects`：关闭无关 CST 工程后重试。
- `project_not_open`：先 `cst-session-open`。
- `lock_not_released`：确认项目已关闭，等待或清理当前任务相关 CST 窗口。
- `no_cst_session`：如果只是 results 读取，通常不阻塞；如果要 modeler 写操作，需要先 `cst-session-open`。
- `Access is denied` 杀不掉 CST 后台进程：先确认进程名在强杀白名单内，再用 `cleanup-cst-processes` 记录 PID/进程名/原因；若无打开工程且无 `.lok`，标为非阻塞残留；禁止声称已杀掉。

## 历史说明

本 Skill 由 `skills/cst-runtime-cli-optimization` 拆分而来。旧 skill 已归档到 `archive/skills/cst-runtime-cli-optimization-20260516/`。

## 最终验收清单

- [ ] 优化循环每轮均实现早停判断，超过目标后未继续执行额外轮次。
- [ ] `status.json` 状态正确（validated / blocked / needs_validation / overrun）。
- [ ] 所有输出文件（S11 JSON/HTML、阶段记录）已落盘。
- [ ] 工程已关闭且无 `.lok` 锁文件。
- [ ] 清理 CST 进程结果已记录；Access denied 残留没有写成已杀掉。
- [ ] `logs/tool_calls.jsonl` 和 `stages/` 能追溯每一步。
- [ ] 只使用了 `cst-runtime-optimization` + `cst-runtime-cli`，没有调用旧脚本。
