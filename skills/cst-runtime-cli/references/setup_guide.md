# 首次初始化手册

安装 Skill 后，agent 自动执行以下流程使环境就绪。

## 自动流程

在工作目录（测试区或任务目录）执行，不在 skill 目录：

```powershell
# 1. 引导模式：入口脚本从 skill 目录加载模块，在工作目录创建 .venv/
python <skill-root>\scripts\cst_runtime_cli.py health-check --auto-fix true

# 2. 通过后切换到生产模式：使用工作目录下隔离的 .venv
uv run python -m cst_runtime usage-guide
uv run python -m cst_runtime list-tools
uv run python -m cst_runtime list-pipelines
```

> `.venv` 只能在其所在目录通过 `uv run` 激活。切换到不同目录后 `uv run` 会自动重建或报错——这是隔离设计，不是 bug。
- Python 版本（≥3.12）
- uv 包管理器
- 工作区初始化（`init-workspace`）
- CST 安装扫描 + pyproject.toml 配置
- Python 导入验证
- 虚拟环境安装（`uv sync`）
- 最终验证（`uv run doctor`）

## 环境隔离说明

`cst_runtime` 是 skill 自带的本地模块（`<skill-root>/scripts/cst_runtime/`），不是 pip 包。

- **禁止**从 skill 目录复制 `cst_runtime/` 到工作区——那会产生过时副本
- 工作区只需 `pyproject.toml` + `.venv`（由 `health-check --auto-fix` 创建）
- 所有命令通过 skill 入口运行，模块从 skill 目录加载

## 入口模式

| 模式 | 命令 | 条件 | 原理 |
|------|------|------|------|
| 引导 | `python <skill-root>\scripts\cst_runtime_cli.py` | 首次运行，零配置 | 入口脚本自动将 `scripts/` 加入 `sys.path`，加载 skill 目录内的模块 |
| 生产 | `uv run python -m cst_runtime` | `health-check --auto-fix` 通过后 | `uv sync` 在工作区创建 `.venv`，模块在该 uv 环境中可解析 |

> 引导模式在任何目录都可运行。生产模式只能在跑过 `health-check` 的目录下用 `uv run`。

## 上下游工具安装

### Python 3.12+

```powershell
# 静默安装（仅当前用户）
python-3.12.7-amd64.exe /quiet InstallAllUsers=0 PrependPath=1
```

Python 安装后若 `python` 仍不可用，注销重登录或手动刷新 PATH。

### uv 包管理器

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### CST Studio Suite 2026

需 GUI 安装 + 商业许可。安装后确认 `python_cst_libraries` 目录存在于：
```
C:\Program Files\CST Studio Suite 2026\AMD64\python_cst_libraries
```

## 常见问题

### health-check 报 Python 版本不足
运行 `python --version` 确认。如果版本 < 3.12，安装 Python 3.12+。

### pyproject.toml 创建失败
检查工作区目录写权限，或手动创建空 `pyproject.toml` 后重试。

### CST 导入验证失败
确认 CST Studio Suite 2026 已安装，`python_cst_libraries` 路径正确。
可指定自定义路径：
```powershell
python <skill-root>\scripts\cst_runtime_cli.py install-cst-libraries --cst-path "D:\CST\AMD64\python_cst_libraries"
```

### uv sync 失败
确认 `pyproject.toml` 存在、Python ≥3.12、网络正常。
