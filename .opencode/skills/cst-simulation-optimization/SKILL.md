---
name: cst-simulation-optimization
description: 当任务需要对某个 CST 工程做参数优化，并围绕目标频点反复执行“复制蓝本→改参数→跑仿真→刷新结果→读取指标→记录日志”闭环，以改善 S11、VSWR、增益或方向图等指标时，调用此 Skill。
---

# CST 仿真优化 Skill

## 触发点

当用户出现以下意图时，应优先触发这个 Skill：

- 用户要求对某个 CST 工程做参数优化
- 用户要求改善 `S11`、`VSWR`、阻抗匹配、带宽、增益、方向图等指标
- 用户要求围绕某个频点或频段做仿真调参
- 用户要求批量测试参数组合并比较结果
- 用户要求把“复制蓝本→改参数→跑仿真→读结果→记录日志”串成闭环
- 用户要求在 `tasks/task_xxx/runs/run_xxx/` 结构下开展一次正式优化任务
- 用户已经给出了 `task.json`、`config.json` 或明确的 run 目录，希望直接开始执行

当任务满足以下条件时，也建议主动切换到这个 Skill：

- 需要反复运行 CST 仿真，而不是只读一次结果
- 需要记录卡点、基线值、运行摘要
- 需要把结果稳定落到 `summary.md`、`status.json`、`logs/`、`exports/`

以下情况不要优先触发本 Skill：

- 只是打开/保存/关闭工程，不涉及优化闭环
- 只是读取现有结果，不需要改参数和重跑仿真
- 只是做几何建模，不涉及结果评估

## 目标

这个 Skill 用于执行 CST 参数化优化任务的最小闭环。

当前骨架阶段只定义：
- 任务输入
- 执行流程
- 结果读取路径
- 日志与卡点记录规范
- 当前已验证可用的稳定链路

后续再根据真实测试继续补充：
- 参数搜索策略
- 评分函数
- 不同目标的专用流程
- 更多异常分支处理

## 适用场景

- 目标是优化 `S11`、`VSWR`、`Z/Y Matrix` 或远场指标
- 参考工程必须先复制成工作副本再操作
- 需要通过 MCP tools 驱动完整仿真闭环
- 需要把测试结论、卡点和基线值落到 `run_xxx` 目录

## 不适用场景

- 只做几何建模，不跑仿真
- 只读已有结果，不做参数调整
- 直接修改 `ref/`、`ref_model/` 或其他蓝本目录

## 输入

执行前至少应明确以下信息：

- `task_id`
- `run_id`
- 蓝本工程路径 `source_project`
- 工作副本路径 `working_project`
- 优化目标，例如：`Improve S11 matching near 10 GHz`
- 频率范围，例如：`9-11 GHz`
- 目标指标，例如：`S11 at 10 GHz`
- 可调参数范围

推荐从以下文件读取上下文：
- `tasks/task_xxx/task.json`
- `tasks/task_xxx/runs/run_xxx/config.json`
- `tasks/task_xxx/runs/run_xxx/status.json`
- `tasks/task_xxx/notes.md`

## 输出

至少产出以下内容：

- 工作副本工程：`runs/run_xxx/projects/working.cst`
- 导出的结果文件：放入 `runs/run_xxx/exports/`
- 运行状态：写入 `runs/run_xxx/status.json`
- 运行摘要：写入 `runs/run_xxx/summary.md`
- 卡点与诊断：写入 `runs/run_xxx/logs/`

## 强制规则

### 1. 蓝本只读

- 禁止直接修改 `ref/`、`ref_model/`、`prototype_optimizer/data/workspaces/*/projects/source/`
- 每次任务必须先复制出工作副本
- 复制时必须完整复制 `.cst` 文件和同名目录

### 2. 目录规范

- run 目录统一使用：`tasks/task_xxx_slug/runs/run_xxx/`
- `projects/` 只放工程副本与其同名目录
- `exports/` 只放导出结果
- `logs/` 只放日志、报错、卡点记录
- `analysis/` 只放分析结论和中间结果
- `summary.md` 记录结论摘要
- `status.json` 记录当前状态

### 3. 仿真与进程管理

- 优先使用异步仿真链路，不默认使用同步 `start_simulation`
- 仿真结束后必须 `save_project()`
- `results` 层在读新结果前必须关闭再重开
- 任务完成后必须关闭项目并退出本次相关的 CST 会话
- 不主动强杀与当前任务无关的 CST 进程

### 4. 远场导出

- 远场导出放在流程最后
- 导出前优先关闭 `results` 上下文，避免文件锁
- 导出后不要再保存工程，避免项目损坏

## 最小稳定工作流

这是当前项目中已验证可用的最小闭环。

### Phase 1：准备

1. 读取 task/run 配置
2. 检查当前任务相关的 CST 窗口是否已关闭
3. 从蓝本完整复制到工作副本
4. 更新 `status.json`，进入运行态

### Phase 2：打开工程

1. `cst-modeler.open_project(working.cst)`
2. `cst-results.open_project(working.cst, allow_interactive=true)`
3. 列参数、确认工程上下文

### Phase 3：应用参数

1. 修改一个或多个参数
2. 如有需要，修改频率范围
3. 记录本轮参数组合

## Phase 4：运行仿真

推荐流程：

1. `cst-modeler.start_simulation_async`
2. 轮询 `cst-modeler.is_simulation_running`
3. 等待直到返回 `running=false`
4. 调用 `cst-modeler.save_project`

说明：
- 当前工程实测中，同步 `start_simulation` 容易超时
- 异步 + 轮询更稳

### Phase 5：刷新结果

1. `cst-results.close_project`
2. `cst-results.open_project(..., allow_interactive=true)`
3. `cst-results.list_result_items`
4. `cst-results.list_run_ids`

说明：
- 不要假设仿真结果会自动出现在旧的 results session 中
- 必须刷新后再读取

### Phase 6：读取指标

以 `S11` 为例：

1. 定位 tree path：`1D Results\S-Parameters\S1,1`
2. 获取最新 `run_id`
3. 调用 `cst-results.get_1d_result`
4. 必要时导出为 CSV 到 `exports/`

复数 `S11` 转 dB 的规则：

```python
import math

mag = math.hypot(real, imag)
s11_db = 20 * math.log10(max(mag, 1e-15))
```

### Phase 7：记录结果

至少记录：

- 本轮参数组合
- 目标频点指标值
- 是否出现新结果树项目
- 是否出现异常告警
- 运行耗时
- 是否存在卡点

### Phase 8：收尾

1. 关闭 `results` 项目
2. 退出当前任务相关的 CST 会话
3. 更新 `summary.md`
4. 更新 `status.json`
5. 把卡点写入 `logs/`

## 当前已验证经验

基于 `task_001_ref_10ghz_match / run_001` 的测试，当前已知：

1. 初始看不到 `S11` 时，不一定是结果树 bug。
   更可能是仿真没有完整结束并落盘。

2. 对当前工程，稳定链路是：
   `start_simulation_async` → `is_simulation_running` 轮询 → `save_project` → `results.close/open`

3. 即使 `projects/working/SP/` 目录为空，也不代表结果不可用。
   当前更可靠的验收方式是：
   结果树是否出现 `1D Results\S-Parameters\S1,1`

4. 当前测试得到的一个基线样例：
   - `10 GHz` 处 `S11 = -32.821529 dB`

5. 当前仍存在两个风险：
   - 端口模式退化告警
   - 求解器因达到最大 pulse widths 而停止，而不是稳态完全满足

## 常见卡点

### 1. 看不到 S 参数结果

排查顺序：

1. 仿真是否真的完成
2. 是否执行了 `save_project()`
3. 是否刷新了 `results` 会话
4. 是否读取了正确的 `run_id`

### 2. 同步仿真超时

处理方式：

1. 改用异步仿真
2. 用轮询判断是否结束
3. 不要把超时直接等同于仿真失败

### 3. 工程复制失败或目录被锁

处理方式：

1. 先关闭当前任务相关的 CST 窗口
2. 再执行复制
3. 不随意清理其他未知会话

### 4. 结果树刷新后仍为空

处理方式：

1. 检查 `Model.log` / `output.txt`
2. 看求解器是否真正结束
3. 看是否有 `Creating parametric 1D results` 之类的完成迹象

## 日志规范

默认使用中文记录。

允许保留英文的部分：
- MCP 工具名
- 结果树路径
- 报错原文
- 文件名和字段名

推荐日志文件：

- `summary.md`
  用于记录本轮结论、基线值、下一步建议

- `logs/baseline_test_blockers.md`
  用于记录测试卡点、排查过程、复测结果

- `logs/*.md`
  按测试主题继续扩展，例如：
  - `parameter_scan_round_001.md`
  - `farfield_export_issues.md`

## 当前骨架不负责的内容

以下内容后续再填充：

- 自动采样策略
- 评分函数
- 多目标优化
- 自动生成最终报告
- 参数敏感度知识库
- 特定天线类型的专用经验

## 后续补强方向

后续可按测试结果逐步补充：

1. 单参数扫描模板
2. 小步长扰动策略
3. 失败样本自动回退策略
4. 结果评分和排序逻辑
5. 远场导出和方向图评分闭环
