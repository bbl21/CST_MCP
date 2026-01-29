# CST MCP Project
# CST MCP 项目

This project is a Python package that integrates with CST Studio Suite and MCP (Model Center Platform).
本项目是一个集成了 CST Studio Suite 和 MCP (Model Center Platform) 的 Python 包。

## Project Structure
## 项目结构

- `Materials/`: Contains material definitions for CST Studio Suite
- `Materials/`: 包含 CST Studio Suite 的材料定义
- `.gitignore`: Git ignore file
- `.gitignore`: Git 忽略文件
- `.python-version`: Python version specification
- `.python-version`: Python 版本规范
- `pyproject.toml`: Project configuration file
- `pyproject.toml`: 项目配置文件

## Prerequisites
## 先决条件

- Python 3.13 or higher
- Python 3.13 或更高版本
- CST Studio Suite 2026
- CST Studio Suite 2026
- MCP (Model Center Platform) 1.25.0 or higher
- MCP (Model Center Platform) 1.25.0 或更高版本
- uv package manager
- uv 包管理器

### Installing uv
### 安装 uv

```bash
# Install uv using pip
# 使用 pip 安装 uv
pip install uv

# Or install uv directly
# 或直接安装 uv
# For Windows:
# Windows系统：
winget install uv.uv

# For macOS:
# macOS系统：
brew install uv

# For Linux:
# Linux系统：
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation
## 安装

### Using uv (Recommended)
### 使用 uv（推荐）

1. **Clone the repository**
1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd CST_MCP
   ```

2. **Create and activate virtual environment using uv**
2. **使用 uv 创建并激活虚拟环境**
   ```bash
   # Create virtual environment
   # 创建虚拟环境
   uv venv

   # Activate virtual environment
   # 激活虚拟环境
   # Windows:
   # Windows系统：
   .venv\Scripts\activate
   # macOS/Linux:
   # macOS/Linux系统：
   source .venv/bin/activate
   ```

3. **Install dependencies using uv**
3. **使用 uv 安装依赖**
   ```bash
   uv add .
   ```

### Using Traditional pip
### 使用传统 pip

1. **Clone the repository**
1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd CST_MCP
   ```

2. **Create a virtual environment**
2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
3. **激活虚拟环境**
   - Windows:
   - Windows系统：
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
   - macOS/Linux系统：
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
4. **安装依赖**
   ```bash
   uv pip install -e .
   ```

## Dependencies
## 依赖项

- `cst-studio-suite-link`: CST Studio Suite Python libraries
- `cst-studio-suite-link`: CST Studio Suite Python 库
- `mcp[cli]>=1.25.0`: Model Center Platform CLI
- `mcp[cli]>=1.25.0`: Model Center Platform 命令行工具

## Usage
## 使用方法

### Basic Usage
### 基本用法


### Adding the MCP in Trae
### 在 Trae 中添加 MCP

> **Note:** This MCP relies on the uv package manager for virtual environment management and startup.
> **注意：** 此 MCP 依赖 uv 包管理器进行虚拟环境管理和启动。

#### Method 1: Using JSON Configuration
#### 方法 1: 使用 JSON 配置

1. **Create a JSON configuration file** with the following content:
1. **创建一个 JSON 配置文件**，内容如下：

```json
{
  "mcpServers": {
    "cst_interface": {
      "command": "uv",
      "args": [
        "--directory",
        "...\\CST_MCP",
        "run",
        "advanced_mcp.py"
      ]
    }
  }
}
```

#### About the uv Startup Configuration
#### 关于 uv 启动配置

The JSON configuration uses `uv` as the command to start the MCP, which:
JSON 配置使用 `uv` 作为启动 MCP 的命令，它会：

1. **Sets the working directory** to the project folder using `--directory`
1. **设置工作目录** 到项目文件夹，使用 `--directory`
2. **Runs the advanced_mcp.py script** using `uv run`
2. **运行 advanced_mcp.py 脚本**，使用 `uv run`
3. **Automatically uses the virtual environment** created by uv
3. **自动使用** uv 创建的虚拟环境

This ensures that the MCP runs with all the necessary dependencies installed in the uv-managed virtual environment.
这确保了 MCP 在 uv 管理的虚拟环境中运行，包含所有必要的依赖项。

2. **Import the JSON file** in Trae:
2. **在 Trae 中导入 JSON 文件**：
   - Open Trae IDE
   - 打开 Trae IDE
   - Navigate to the MCP section
   - 导航到 MCP 部分
   - Click on "Import MCP Configuration" or similar option
   - 点击 "导入 MCP 配置" 或类似选项
   - Select the JSON file you created
   - 选择你创建的 JSON 文件
   - Confirm the import
   - 确认导入

### Verifying the MCP in Trae
### 在 Trae 中验证 MCP

1. **Check the MCP list** in Trae
1. **检查 Trae 中的 MCP 列表**
2. **Ensure the CST MCP project is listed**
2. **确保 CST MCP 项目已列出**
3. **Test the MCP** by running a simple workflow
3. **通过运行简单工作流测试 MCP**

## Materials
## 材料

The project includes a comprehensive set of material definitions in the `Materials/` directory, including:
项目在 `Materials/` 目录中包含了一套全面的材料定义，包括：

- Conductors (Aluminum, Copper, Gold, etc.)
- 导体（铝、铜、金等）
- Dielectrics (FR-4, PTFE, etc.)
- 电介质（FR-4、PTFE 等）
- Absorbers (ECCOSORB series)
- 吸收体（ECCOSORB 系列）
- Semiconductors (Gallium Arsenide)
- 半导体（砷化镓）
- And many more...
- 以及更多...

## Configuration
## 配置

The project is configured using `pyproject.toml`, which specifies:
项目使用 `pyproject.toml` 进行配置，其中指定了：

- Project metadata
- 项目元数据
- Python version requirements
- Python 版本要求
- Dependencies
- 依赖项
- Source locations for CST Studio Suite libraries
- CST Studio Suite 库的源位置

## Troubleshooting
## 故障排除

### Common Issues
### 常见问题

1. **CST Studio Suite path not found**
1. **找不到 CST Studio Suite 路径**
   - Ensure CST Studio Suite 2026 is installed in the default location
   - 确保 CST Studio Suite 2026 安装在默认位置
   - Verify the path in `pyproject.toml` is correct
   - 验证 `pyproject.toml` 中的路径是否正确

2. **Python version compatibility**
2. **Python 版本兼容性**
   - Ensure you're using Python 3.13 or higher
   - 确保使用 Python 3.13 或更高版本
   - Check the `.python-version` file for the recommended version
   - 查看 `.python-version` 文件了解推荐版本


