# 天线自动调优原型开发指导

> 目标：基于现有 CST MCP 能力，快速搭建一个“CST 外置化”的天线性能自动调优原型，用于验证产品想法，而不是一开始就做重型正式系统。

---

## 1. 项目目标

构建一个可交互的原型系统，完成以下闭环：

1. 用户配置调优任务
2. 外部系统生成参数样本
3. 调用 CST 执行仿真
4. 读取/导出结果
5. 计算性能指标
6. 对候选参数进行评分与排序
7. 展示历史任务、结果对比
8. 导出任务报告

这个原型的重点不是“高精度全自动优化算法”，而是先验证下面这件事是否成立：

**是否可以把 CST 作为单纯的仿真与结果导出执行器，在外部实现一套更灵活的天线调优流程。**

---

## 2. 已确定的核心原则

### 2.1 CST 的角色

CST 只负责两件事：

- 仿真执行
- 结果导出

不依赖 CST 内部的：

- 参数扫描系统
- 内置优化器
- 内部任务编排逻辑

也就是说，后续原型中的参数搜索、评分、排序、历史管理、报告导出，全部在外部实现。

### 2.2 优化策略

原型阶段优先采用：

**随机采样 / 分层采样 + 排行**

原因：

- 实现快
- 容易解释
- 适合验证流程闭环
- 能较快产出“看起来合理”的结果
- 便于后续替换为贝叶斯优化、遗传算法或其他更复杂策略

### 2.3 结果获取策略

采用混合模式：

#### 常规 1D 结果
优先直接读取接口结果，例如：

- S 参数
- 阻抗类曲线
- 其他 0D/1D 结果

#### 远场结果
不走“直接二进制解析 farfield 内部结果”的路线，而采用：

1. 根据结果文件名 / 结果树名称规则定位准确 farfield 名称
2. 注入 VBA 或等效导出指令
3. 导出 ASCII / TXT
4. 再由外部程序解析与评分

这个路线更稳，也更符合当前已有能力。

---

## 3. 原型范围（MVP）

本次原型不是只做一个脚本，而是做一个完整 MVP，至少包含：

### 3.1 任务配置界面
用户可以配置：

- 目标 CST 工程路径
- 调优参数及范围
- 样本数量
- 频段范围
- 指标权重
- 输出目录

### 3.2 优化流程执行
系统可以：

- 自动生成样本
- 批量调用 CST 仿真
- 采集结果
- 计算指标
- 生成分数与排名

### 3.3 历史任务管理
支持查看：

- 历史任务列表
- 每个任务的配置
- 每个任务的运行状态
- 历史最优结果

### 3.4 结果对比
支持对多个候选方案做可视化比较，例如：

- S11 曲线对比
- 增益对比
- 平坦度对比
- 综合评分对比

### 3.5 报告导出
至少支持导出一份结构化报告，内容包括：

- 任务配置
- 参数空间
- 最优结果
- Top-N 候选
- 关键图表
- 指标总结

---

## 4. 推荐技术栈

原型阶段建议：

- **Python**：主语言
- **Streamlit**：快速搭界面
- **SQLite**：存储任务、运行记录、指标、报告索引
- **Plotly**：绘图与交互展示
- **Jinja2 + HTML**：报告生成

理由：

- 开发速度快
- 学习成本低
- 与现有 Python 代码和 CST MCP 能力兼容
- 后续可平滑迁移到更正式架构

---

## 5. 推荐目录结构

建议在仓库下新建：

```text
<repo>/prototype_optimizer/
├─ app.py
├─ requirements.txt
├─ config/
│  └─ default_config.json
├─ data/
│  ├─ optimizer.db
│  ├─ runs/
│  └─ reports/
├─ core/
│  ├─ orchestrator.py
│  ├─ sampler.py
│  ├─ evaluator.py
│  ├─ scorer.py
│  └─ models.py
├─ adapters/
│  ├─ cst_adapter.py
│  ├─ result_reader.py
│  └─ farfield_exporter.py
├─ storage/
│  ├─ db.py
│  ├─ task_repo.py
│  ├─ run_repo.py
│  └─ report_repo.py
├─ ui/
│  ├─ pages/
│  │  ├─ 1_Task_Config.py
│  │  ├─ 2_Run_History.py
│  │  ├─ 3_Result_Compare.py
│  │  └─ 4_Report_Export.py
├─ reports/
│  ├─ generator.py
│  └─ templates/
│     └─ report_template.html
└─ tests/
   ├─ test_sampler.py
   ├─ test_scorer.py
   └─ test_evaluator.py
```

---

## 6. 核心模块职责

## 6.1 orchestrator.py

负责任务主流程编排：

- 创建任务
- 生成样本
- 循环执行仿真
- 采集结果
- 计算指标
- 打分排序
- 汇总任务结果
- 生成报告

这是原型的主控制器。

### 参考伪代码

```python
for sample in samples:
    create_run_record()
    apply_parameters(sample)
    run_simulation()
    read_s11_result()
    export_farfield_if_needed()
    evaluate_metrics()
    compute_score()
    save_run_result()

update_task_summary()
generate_report()
```

---

## 6.2 sampler.py

负责参数样本生成。

原型阶段支持：

- 随机采样
- 简单分层采样

输入示例：

```python
{
    "g": [4.0, 8.0],
    "thr": [2.0, 6.0],
    "R": [0.01, 0.03]
}
```

输出示例：

```python
[
    {"g": 4.8, "thr": 3.6, "R": 0.018},
    {"g": 5.5, "thr": 4.1, "R": 0.022},
]
```

要求：

- 可复现（支持随机种子）
- 后续易扩展到更高级算法

---

## 6.3 cst_adapter.py

负责封装与 CST 的交互。

建议接口：

```python
class CSTAdapter:
    def __init__(self, project_path: str):
        ...

    def open(self) -> None:
        ...

    def apply_parameters(self, params: dict) -> None:
        ...

    def run_simulation(self) -> dict:
        ...

    def read_s11(self) -> dict:
        ...

    def export_farfield(self, frequency: float, out_dir: str) -> str:
        ...

    def close(self) -> None:
        ...
```

设计原则：

- 屏蔽底层细节
- 上层编排逻辑不直接关心具体 MCP 调用细节
- 后续如果结果获取路线调整，只改 adapter 层

---

## 6.4 result_reader.py

负责处理结果读取。

建议拆为两类：

### 1D 结果读取
读取：

- S11
- 其他可直接读取的曲线

### 导出文件解析
解析：

- farfield ASCII/TXT
- 其他导出后的文本数据

输出尽量统一成标准数据结构，例如：

```python
{
    "x": [...],
    "y": [...],
    "meta": {...}
}
```

---

## 6.5 evaluator.py

负责从原始结果中提取指标。

建议至少支持这些指标：

- `worst_s11_db`：频带内最差 S11
- `avg_s11_db`：频带内平均 S11
- `s11_pass_ratio`：满足阈值的频点占比
- `avg_gain_db`：平均增益
- `gain_flatness_db`：增益平坦度
- `sim_ok`：仿真是否成功
- `export_ok`：导出是否成功

输出示例：

```python
{
    "worst_s11_db": -8.2,
    "avg_s11_db": -11.5,
    "s11_pass_ratio": 0.67,
    "avg_gain_db": 9.8,
    "gain_flatness_db": 1.4,
    "sim_ok": True,
    "export_ok": True
}
```

---

## 6.6 scorer.py

负责综合评分。

建议默认权重：

- 匹配：0.45
- 增益：0.30
- 平坦度：0.20
- 稳定性：0.05

示例：

```python
def compute_score(metrics: dict, weights: dict) -> float:
    ...
```

原则：

- 分数规则透明
- 每个指标的贡献可解释
- 后续支持用户自定义权重

---

## 7. 数据存储设计

推荐使用 SQLite。

至少包含以下表：

## 7.1 tasks

存储任务级信息：

- id
- name
- project_path
- parameter_space_json
- target_config_json
- sample_count
- status
- created_at
- finished_at

## 7.2 runs

存储每次样本运行：

- id
- task_id
- run_index
- parameter_json
- score
- status
- result_dir
- sim_message
- created_at

## 7.3 metrics

存储每次运行的核心指标：

- id
- run_id
- worst_s11_db
- avg_s11_db
- s11_pass_ratio
- avg_gain_db
- gain_flatness_db
- sim_ok
- export_ok

## 7.4 reports

存储报告记录：

- id
- task_id
- report_path
- created_at

### 数据设计原则

- 每个 run 都可追溯
- 原始指标必须保留
- 不要只存最终分数
- 允许后续重新评分

---

## 8. UI 页面规划

建议先做 4 个页面。

## 8.1 任务配置页

功能：

- 选择 CST 工程
- 填写参数空间
- 设置样本数量
- 设置目标频段
- 设置评分权重
- 启动任务

## 8.2 运行历史页

功能：

- 查看历史任务列表
- 查看任务状态
- 查看最优分数
- 查看每个任务的 Top-N 结果

## 8.3 结果对比页

功能：

- 选中多个 run
- 对比 S11 曲线
- 对比增益曲线/点值
- 对比综合评分
- 标出最优候选

## 8.4 报告导出页

功能：

- 选择任务
- 预览报告摘要
- 导出 HTML 报告
- 后续可再扩展 PDF

---

## 9. 报告内容建议

报告至少包括：

1. 任务概览
2. 参数空间说明
3. 样本数量与执行成功率
4. Top-N 候选参数
5. 最优方案关键指标
6. S11 对比图
7. 增益/平坦度图
8. 结论与建议

建议先输出 HTML 报告，因为：

- 开发快
- 展示效果好
- 容易嵌图表
- 后续再转 PDF 也方便

---

## 10. 推荐开发顺序

按下面顺序做，能最快出原型。

### 第一阶段：跑通最小闭环

目标：先不做漂亮界面，只要能完成一次完整任务。

1. 建立目录结构
2. 实现 SQLite 基础存储
3. 实现参数采样器
4. 封装 CST 适配层
5. 实现 S11 读取
6. 实现 farfield 导出与解析
7. 实现指标计算
8. 实现综合评分
9. 实现命令行/简单页面触发一次任务

### 第二阶段：补交互界面

1. 做任务配置页
2. 做运行历史页
3. 做结果对比页
4. 做报告导出页

### 第三阶段：补产品感

1. 加任务摘要卡片
2. 加运行进度展示
3. 加异常提示
4. 加报告模板美化
5. 加配置默认值与参数校验

---

## 11. 风险与处理建议

## 11.1 CST 调用不稳定

风险：

- 打开工程失败
- 仿真超时
- 导出失败

建议：

- 每次 run 记录详细状态
- 对失败 run 保留错误信息
- 原型阶段允许个别 run 失败，不要因为单次失败中断整个任务

## 11.2 远场结果命名不稳定

风险：

- farfield 结果名称随工程或端口配置变化

建议：

- 先做“结果定位函数”
- 把准确名称记录到 run 元数据
- 不要在代码里写死某个 farfield 名称

## 11.3 指标定义容易反复修改

风险：

- 用户后续会调整评分口径

建议：

- 指标计算与评分拆开
- 数据库存原始指标
- 评分函数支持热更新/配置化

## 11.4 原型容易做成一次性脚本

风险：

- 越写越乱，后面难扩展

建议：

- 一开始就分层：adapter / core / storage / ui
- 即使原型，也不要把所有逻辑堆进一个文件

---

## 12. 默认参数建议

用于第一版原型的默认配置建议：

### 任务默认值

- 样本数：20
- S11 阈值：-10 dB
- 默认目标频段：按具体项目填写
- 报告输出：`prototype_optimizer/data/reports/`

### 默认评分权重

```json
{
  "match": 0.45,
  "gain": 0.30,
  "flatness": 0.20,
  "stability": 0.05
}
```

---

## 13. 第一版完成标准

满足以下条件，就算第一版原型可用：

1. 能从界面配置一个任务
2. 能自动生成一批参数样本
3. 能驱动 CST 完成仿真
4. 能读到 S11
5. 能导出并解析远场数据
6. 能算出指标与综合分数
7. 能展示 Top-N 结果
8. 能查看历史任务
9. 能导出一份 HTML 报告

---

## 14. 后续扩展方向

第一版跑通后，再考虑：

- 贝叶斯优化
- 遗传算法
- 多目标 Pareto 排序
- 多任务并发调度
- 任务中断恢复
- PDF 报告导出
- 更正式的 Web 前端
- 用户权限与项目管理

这些都不该阻碍 MVP 启动。

---

## 15. 新对话启动时的开发建议

如果后续重新开启新对话并正式进入开发，建议按这个顺序开始：

1. 先创建 `prototype_optimizer/` 目录结构
2. 先实现数据模型与 SQLite
3. 再实现 `cst_adapter.py`
4. 跑通单次 sample 仿真流程
5. 再逐步补 UI 与报告功能

一句话总结：

**先把闭环跑通，再把体验做完整。不要先陷入“完美优化算法”或者“复杂前端界面”。**

---

## 16. 最终结论

这个原型的正确定位不是“做一个依赖 CST 内部系统的包装壳”，而是：

**做一个以 CST 为执行器、以外部 Python 系统为核心的大脑型调优原型。**

这条路线更灵活，也更适合快速验证产品方向。
