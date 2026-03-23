import cst
import cst.interface
import os
import re
from typing import Union
from mcp.server import FastMCP

# 创建MCP实例
mcp = FastMCP("cst_interface", log_level="ERROR")

# ============================================================
# 全局变量
# ============================================================
_current_project = None
_current_fullpath = None
global_parameters = {}
call_counts = {
    'cylinder': 0,
    'cone': 0,
    'port': 0,
    'brick': 0
}
line_break = '\n'
defined_materials = set()


# ============================================================
# 全局辅助函数
# ============================================================

def save_project_object(project, fullpath):
    """保存project对象到全局变量"""
    global _current_project, _current_fullpath
    _current_project = project
    _current_fullpath = fullpath

def get_project_object():
    """从全局变量获取当前project对象"""
    global _current_project, _current_fullpath
    if _current_project is not None:
        return {'project': _current_project, 'fullpath': _current_fullpath}
    return None

def clear_project_object():
    """清除当前project对象"""
    global _current_project, _current_fullpath, global_parameters, call_counts, defined_materials
    _current_project = None
    _current_fullpath = None
    global_parameters.clear()
    defined_materials.clear()
    call_counts = {'cylinder': 0, 'cone': 0, 'port': 0, 'brick': 0}

def _generate_unique_param_name(name):
    """生成唯一的参数名"""
    global global_parameters
    if name not in global_parameters:
        return name
    if "_" in name:
        parts = name.rsplit("_", 1)
        base_name = parts[0] if parts[1].isdigit() else name
    else:
        base_name = name
    max_suffix = 0
    prefix = f"{base_name}_"
    for p_name in global_parameters:
        if p_name == base_name:
            max_suffix = 1
        elif p_name.startswith(prefix):
            try:
                suffix = int(p_name[len(prefix):])
                if suffix > max_suffix:
                    max_suffix = suffix
            except ValueError:
                pass
    return f"{base_name}_{max_suffix + 1}"


# ============================================================
# 🎛️ 控制类工具（不使用 add_to_history，共10个）
# 直接调用 CST API，不可使用 VBA 替代
# ============================================================

# ---------- 项目管理（4个）----------

@mcp.tool()
def init_cst_project(path: str, base_name: str, ext: str):
    """初始化CST项目"""
    global global_parameters, call_counts, defined_materials
    global_parameters.clear()
    defined_materials.clear()
    call_counts = {'cylinder': 0, 'cone': 0, 'port': 0, 'brick': 0}

    idx = 0
    while True:
        filename = f"{base_name}_{idx}{ext}"
        fullpath = os.path.join(path, filename)
        if not os.path.exists(fullpath):
            break
        idx += 1

    de = cst.interface.DesignEnvironment.new()
    project = de.new_mws()
    project.save(fullpath)
    save_project_object(project, fullpath)
    return {"status": "success", "fullpath": fullpath}

@mcp.tool()
def open_project(fullpath: str):
    """打开现有CST项目"""
    global global_parameters, call_counts, defined_materials
    global_parameters.clear()
    defined_materials.clear()
    call_counts = {'cylinder': 0, 'cone': 0, 'port': 0, 'brick': 0}

    if os.path.isdir(fullpath):
        return {"status": "error", "message": f"路径是文件夹，不是项目文件: {fullpath}"}

    if not fullpath.endswith('.cst'):
        cst_path = fullpath + '.cst'
        if os.path.exists(cst_path):
            fullpath = cst_path
        else:
            return {"status": "error", "message": f"项目文件不存在: {fullpath}"}

    if not os.path.exists(fullpath) or not os.path.isfile(fullpath):
        return {"status": "error", "message": f"项目文件不存在: {fullpath}"}

    try:
        de = cst.interface.DesignEnvironment()
        project = de.open_project(fullpath)
        save_project_object(project, fullpath)
        return {"status": "success", "fullpath": fullpath}
    except Exception as e:
        error_msg = str(e)
        if "cannot be opened" in error_msg.lower() or "正在使用" in error_msg:
            return {"status": "error", "message": f"项目文件正在被其他程序使用，请先关闭 CST Studio Suite\n路径: {fullpath}"}
        else:
            return {"status": "error", "message": f"打开项目失败: {error_msg}\n路径: {fullpath}"}

@mcp.tool()
def save_project():
    """保存当前项目"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    try:
        project_data['project'].save()
        return {"status": "success", "message": f"项目已保存: {project_data['fullpath']}"}
    except Exception as e:
        return {"status": "error", "message": f"保存项目失败: {str(e)}"}

@mcp.tool()
def close_project():
    """关闭当前项目"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    try:
        project_data['project'].close()
        clear_project_object()
        return {"status": "success", "message": f"项目已关闭: {project_data['fullpath']}"}
    except Exception as e:
        return {"status": "error", "message": f"关闭项目失败: {str(e)}"}

# ---------- 仿真运行（6个）----------

@mcp.tool()
def start_simulation():
    """开始仿真（同步执行，等待完成）"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        project.modeler.run_solver()
        return {"status": "success", "message": "仿真已成功完成"}
    except Exception as e:
        return {"status": "error", "message": f"仿真失败: {str(e)}"}

@mcp.tool()
def start_simulation_async():
    """异步开始仿真（启动后立即返回）"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        project.modeler.start_solver()
        return {"status": "success", "message": "仿真已成功启动"}
    except Exception as e:
        return {"status": "error", "message": f"仿真启动失败: {str(e)}"}

@mcp.tool()
def is_simulation_running():
    """检查仿真状态"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        running = project.modeler.is_solver_running()
        return {"status": "success", "message": f"仿真状态: {'运行中' if running else '未运行'}", "running": running}
    except Exception as e:
        return {"status": "error", "message": f"检查仿真状态失败: {str(e)}"}

@mcp.tool()
def pause_simulation():
    """暂停仿真"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        project.modeler.pause_solver()
        return {"status": "success", "message": "仿真已成功暂停"}
    except Exception as e:
        return {"status": "error", "message": f"暂停仿真失败: {str(e)}"}

@mcp.tool()
def resume_simulation():
    """恢复仿真"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        project.modeler.resume_solver()
        return {"status": "success", "message": "仿真已成功恢复"}
    except Exception as e:
        return {"status": "error", "message": f"恢复仿真失败: {str(e)}"}

@mcp.tool()
def stop_simulation():
    """停止仿真"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    try:
        project.modeler.abort_solver()
        return {"status": "success", "message": "仿真已成功停止"}
    except Exception as e:
        return {"status": "error", "message": f"停止仿真失败: {str(e)}"}


# ============================================================
# 🔧 使用 add_to_history 的工具（共28个）
# 可直接使用 VBA 代码替代
# ============================================================

# ---------- 自定义操作（1个）----------

@mcp.tool()
def add_to_history(command: str, history_name: str = None):
    """直接添加VBA命令到CST历史记录"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    if history_name is None:
        history_name = "CustomCommand"
    sCommand = command.replace('\\n', line_break).replace('\n', line_break)
    try:
        project.modeler.add_to_history(history_name, sCommand)
        return {"status": "success", "message": f"命令已添加到历史记录: {history_name}"}
    except Exception as e:
        return {"status": "error", "message": f"添加命令失败: {str(e)}"}

# ---------- 参数管理（1个）----------

def _parse_value_for_modeling(param_prefix: str, value: Union[float, str]) -> str:
    """解析建模参数值，支持数字、参数名或简单表达式"""
    if isinstance(value, (int, float)):
        result = parameter_set(f"{param_prefix}", value)
        return result["message"].split()[1]
    else:
        result = parameter_set(f"{param_prefix}", str(value))
        return result["message"].split()[1]

@mcp.tool()
def parameter_set(name: str, value=None):
    """设置CST参数"""
    global global_parameters
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    param_name = _generate_unique_param_name(name)
    if isinstance(value, (int, float)):
        sCommand = f'MakeSureParameterExists("{param_name}", "{value:.6f}")'
    else:
        sCommand = f'MakeSureParameterExists("{param_name}", "{value}")'
    if project.modeler is not None:
        project.modeler.add_to_history('StoreParameter', sCommand)
    global_parameters[param_name] = value
    return {"status": "success", "message": f"Parameter {param_name} set to {value}"}

# ---------- 建模工具（14个）----------

@mcp.tool()
def define_brick(name: str, component: str, material: str,
                x_min: Union[float, str], x_max: Union[float, str],
                y_min: Union[float, str], y_max: Union[float, str],
                z_min: Union[float, str], z_max: Union[float, str]):
    """定义长方体"""
    global call_counts, global_parameters, line_break
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    call_counts['brick'] += 1

    material_result = _define_material(material)
    if material_result['status'] == 'error':
        return material_result

    param_prefix = f"brick_{name}_"
    x_min_param = _parse_value_for_modeling(f"{param_prefix}x_min", x_min)
    x_max_param = _parse_value_for_modeling(f"{param_prefix}x_max", x_max)
    y_min_param = _parse_value_for_modeling(f"{param_prefix}y_min", y_min)
    y_max_param = _parse_value_for_modeling(f"{param_prefix}y_max", y_max)
    z_min_param = _parse_value_for_modeling(f"{param_prefix}z_min", z_min)
    z_max_param = _parse_value_for_modeling(f"{param_prefix}z_max", z_max)

    VBA_code = [
        "With Brick", "    .Reset",
        f"    .Name \"{name}\"", f"    .Component \"{component}\"", f"    .Material \"{material}\"",
        f"    .Xrange {x_min_param}, {x_max_param}", f"    .Yrange {y_min_param}, {y_max_param}",
        f"    .Zrange {z_min_param}, {z_max_param}", "    .Create", "End With"
    ]
    sCommand = line_break.join(VBA_code)
    try:
        project.modeler.add_to_history(f"Define Brick:{name}", sCommand)
        return {"status": "success", "message": f"Brick {name} created successfully"}
    except Exception as e:
        return {"status": "error", "message": f"创建长方体失败: {str(e)}", "command": sCommand}

@mcp.tool()
def define_cylinder(name: str, component: str, material: str,
                   outer_radius: Union[float, str], inner_radius: Union[float, str],
                   axis: str, range_min: Union[float, str] = None, range_max: Union[float, str] = None,
                   z_min: Union[float, str] = None, z_max: Union[float, str] = None,
                   center1: Union[float, str] = 0.0, center2: Union[float, str] = 0.0,
                   x_center: Union[float, str] = None, y_center: Union[float, str] = None,
                   segments: int = 0):
    """定义圆柱体"""
    if range_min is None and z_min is not None: range_min = z_min
    if range_max is None and z_max is not None: range_max = z_max
    if center1 is None and x_center is not None: center1 = x_center
    if center2 is None and y_center is not None: center2 = y_center
    if range_min is None or range_max is None:
        return {"status": "error", "message": "缺少必要参数: range_min 或 range_max"}

    global call_counts, line_break
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    call_counts['cylinder'] += 1

    material_result = _define_material(material)
    if material_result['status'] == 'error':
        return material_result

    param_prefix = f"cylinder_{name}_"
    outer_radius_param = _parse_value_for_modeling(f"{param_prefix}outer_radius", outer_radius)
    inner_radius_param = _parse_value_for_modeling(f"{param_prefix}inner_radius", inner_radius)
    range_min_param = _parse_value_for_modeling(f"{param_prefix}range_min", range_min)
    range_max_param = _parse_value_for_modeling(f"{param_prefix}range_max", range_max)
    center1_param = _parse_value_for_modeling(f"{param_prefix}center1", center1)
    center2_param = _parse_value_for_modeling(f"{param_prefix}center2", center2)

    axis_lower = axis.lower()
    if axis_lower == "x":
        range_param = f"Xrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Ycenter", ".Zcenter"
    elif axis_lower == "y":
        range_param = f"Yrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Xcenter", ".Zcenter"
    else:
        range_param = f"Zrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Xcenter", ".Ycenter"

    VBA_code = [
        "With Cylinder", "    .Reset",
        f"    .Name \"{name}\"", f"    .Component \"{component}\"", f"    .Material \"{material}\"",
        f"    .OuterRadius {outer_radius_param}", f"    .InnerRadius {inner_radius_param}",
        f"    .Axis \"{axis}\"", f"    .{range_param}",
        f"    {center1_vba} {center1_param}", f"    {center2_vba} {center2_param}",
        f"    .Segments \"{segments}\"", "    .Create", "End With"
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Cylinder:{name}", sCommand)
    return {"status": "success", "message": f"Cylinder {name} created successfully"}

@mcp.tool()
def define_cone(name: str, component: str, material: str,
              bottom_radius: Union[float, str], top_radius: Union[float, str],
              axis: str, range_min: Union[float, str] = None, range_max: Union[float, str] = None,
              z_min: Union[float, str] = None, z_max: Union[float, str] = None,
              center1: Union[float, str] = 0.0, center2: Union[float, str] = 0.0,
              x_center: Union[float, str] = None, y_center: Union[float, str] = None,
              segments: int = 0):
    """定义圆锥体"""
    if range_min is None and z_min is not None: range_min = z_min
    if range_max is None and z_max is not None: range_max = z_max
    if center1 is None and x_center is not None: center1 = x_center
    if center2 is None and y_center is not None: center2 = y_center
    if range_min is None or range_max is None:
        return {"status": "error", "message": "缺少必要参数: range_min 或 range_max"}

    global call_counts, line_break
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    call_counts['cone'] += 1

    material_result = _define_material(material)
    if material_result['status'] == 'error':
        return material_result

    param_prefix = f"cone_{name}_"
    bottom_radius_param = _parse_value_for_modeling(f"{param_prefix}bottom_radius", bottom_radius)
    top_radius_param = _parse_value_for_modeling(f"{param_prefix}top_radius", top_radius)
    range_min_param = _parse_value_for_modeling(f"{param_prefix}range_min", range_min)
    range_max_param = _parse_value_for_modeling(f"{param_prefix}range_max", range_max)
    center1_param = _parse_value_for_modeling(f"{param_prefix}center1", center1)
    center2_param = _parse_value_for_modeling(f"{param_prefix}center2", center2)

    axis_lower = axis.lower()
    if axis_lower == "x":
        range_param = f"Xrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Ycenter", ".Zcenter"
    elif axis_lower == "y":
        range_param = f"Yrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Xcenter", ".Zcenter"
    else:
        range_param = f"Zrange {range_min_param}, {range_max_param}"
        center1_vba, center2_vba = ".Xcenter", ".Ycenter"

    VBA_code = [
        "With Cone", "    .Reset",
        f"    .Name \"{name}\"", f"    .Component \"{component}\"", f"    .Material \"{material}\"",
        f"    .BottomRadius {bottom_radius_param}", f"    .TopRadius {top_radius_param}",
        f"    .Axis \"{axis}\"", f"    .{range_param}",
        f"    {center1_vba} {center1_param}", f"    {center2_vba} {center2_param}",
        f"    .Segments \"{segments}\"", "    .Create", "End With"
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Cone:{name}", sCommand)
    return {"status": "success", "message": f"Cone {name} created successfully"}

@mcp.tool()
def define_rectangle(name: str, curve: str, x_min: Union[float, str], x_max: Union[float, str],
                    y_min: Union[float, str], y_max: Union[float, str]):
    """定义长方形"""
    global line_break
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']

    param_prefix = f"rect_{name}_"
    x_min_param = _parse_value_for_modeling(f"{param_prefix}x_min", x_min)
    x_max_param = _parse_value_for_modeling(f"{param_prefix}x_max", x_max)
    y_min_param = _parse_value_for_modeling(f"{param_prefix}y_min", y_min)
    y_max_param = _parse_value_for_modeling(f"{param_prefix}y_max", y_max)

    VBA_code = [
        'With Rectangle', '    .Reset',
        f'    .Name "{name}"', f'    .Curve "{curve}"',
        f'    .Xrange {x_min_param}, {x_max_param}', f'    .Yrange {y_min_param}, {y_max_param}',
        '    .Create', 'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Rectangle:{name}", sCommand)
    return {"status": "success", "message": f"Rectangle {name} created successfully"}

@mcp.tool()
def boolean_subtract(target: str, tool: str):
    """布尔差集运算"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solid.Subtract \"{target}\", \"{tool}\"'
    project.modeler.add_to_history(f"boolean subtract shapes: {target}, {tool}", sCommand)
    return {"status": "success", "message": f"Boolean subtract {target} - {tool} completed"}

@mcp.tool()
def boolean_add(shape1: str, shape2: str):
    """布尔和运算"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solid.Add \"{shape1}\", \"{shape2}\"'
    project.modeler.add_to_history(f"boolean add shapes: {shape1}, {shape2}", sCommand)
    return {"status": "success", "message": f"Boolean add {shape1} + {shape2} completed"}

@mcp.tool()
def boolean_intersect(shape1: str, shape2: str):
    """布尔交集运算"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solid.Intersect \"{shape1}\", \"{shape2}\"'
    project.modeler.add_to_history(f"boolean intersect shapes: {shape1}, {shape2}", sCommand)
    return {"status": "success", "message": f"Boolean intersect {shape1} & {shape2} completed"}

@mcp.tool()
def boolean_insert(shape1: str, shape2: str):
    """布尔插入运算"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solid.Insert \"{shape1}\", \"{shape2}\"'
    project.modeler.add_to_history(f"boolean insert shapes: {shape1}, {shape2}", sCommand)
    return {"status": "success", "message": f"Boolean insert {shape1} insert {shape2} completed"}

@mcp.tool()
def delete_entity(component: str, name: str):
    """删除几何实体"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    full_name = f"{component}:{name}"
    sCommand = f'Solid.Delete \"{full_name}\"'
    try:
        project.modeler.add_to_history(f"delete entity: {full_name}", sCommand)
        return {"status": "success", "message": f"已删除几何实体 {full_name}"}
    except Exception as e:
        return {"status": "error", "message": f"删除实体失败: {str(e)}"}

@mcp.tool()
def create_horn_segment(segment_id: int, bottom_radius: float, top_radius: float, z_min: float, z_max: float):
    """创建喇叭段（外圆台+内圆台+布尔差集）"""
    define_cone(name=str(segment_id), component="component1", material="PEC",
                bottom_radius=f"{bottom_radius}+d", top_radius=f"{top_radius}+d", axis="z",
                z_min=z_min, z_max=z_max)
    define_cone(name=f"solid{segment_id}", component="component1", material="PEC",
                bottom_radius=bottom_radius, top_radius=top_radius, axis="z",
                z_min=z_min, z_max=z_max)
    boolean_subtract(f"component1:{segment_id}", f"component1:solid{segment_id}")
    return {"status": "success", "message": f"Horn segment {segment_id} created successfully"}

# ---------- 材料定义（1个）----------

def read_mtd_file(file_path):
    """读取.mtd文件内容"""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception:
        return None

def parse_mtd_definition(mtd_content):
    """解析.mtd文件中的[Definition]部分"""
    commands = []
    lines = mtd_content.split('\n')
    in_definition = False
    for line in lines:
        line = line.strip()
        if line == '[Definition]':
            in_definition = True
            continue
        elif line.startswith('[') and line.endswith(']'):
            break
        if in_definition and line:
            commands.append(line)
    return commands

def generate_material_vba(name, definition_commands):
    """从解析后的命令生成材料定义VBA脚本"""
    vba_lines = ["With Material", "    .Reset", f"    .Name \"{name}\"", "    .Folder \"\""]
    has_create = False
    for command in definition_commands:
        vba_lines.append(f"    {command}")
        if command.strip() == ".Create":
            has_create = True
    if not has_create:
        vba_lines.append("    .Create")
    vba_lines.append("End With")
    return '\n'.join(vba_lines)

def _define_material(material_name: str):
    """内部函数：定义材料，带记忆功能"""
    global defined_materials
    if material_name in defined_materials:
        return {"status": "success", "message": f"材料 {material_name} 已经定义过"}
    if material_name in ["Vacuum", "PEC"]:
        defined_materials.add(material_name)
        return {"status": "success", "message": f"材料 {material_name} 是系统默认材料"}

    # Copper 别名映射
    copper_aliases = {"Copper": "Copper (pure)"}
    if material_name in copper_aliases:
        material_name = copper_aliases[material_name]

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']

    material_library_path = r"c:/Users/z1376/Documents/CST_MCP/.trae/skills/cst-overview/reference/Materials"
    file_path = material_library_path + "/" + f"{material_name}.mtd"

    mtd_content = read_mtd_file(file_path)
    if not mtd_content:
        return {"status": "error", "message": f"无法读取文件: {file_path}"}

    definition_commands = parse_mtd_definition(mtd_content)
    if not definition_commands:
        return {"status": "error", "message": f"文件中没有找到[Definition]部分: {file_path}"}

    vba_script = generate_material_vba(material_name, definition_commands)
    try:
        project.modeler.add_to_history(f"Define Material: {material_name}", vba_script)
        defined_materials.add(material_name)
        return {"status": "success", "message": f"材料 {material_name} 已从文件 {file_path} 成功定义"}
    except Exception as e:
        return {"status": "error", "message": f"定义材料失败: {str(e)}"}

@mcp.tool()
def define_material_from_mtd(material_name: str):
    """从.mtd文件定义材料"""
    return _define_material(material_name)

# ---------- 仿真设置（7个）----------

@mcp.tool()
def change_parameter(para_name: str, para_value: float):
    """修改模型参数"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'StoreDoubleParameter "{para_name}", {para_value}'
    project.modeler.add_to_history('ChangeParameter', sCommand)
    return {"status": "success", "message": f"参数 {para_name} 已修改为 {para_value}"}

@mcp.tool()
def change_frequency_range(min_frequency: str, max_frequency: str):
    """修改仿真频率范围"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solver.FrequencyRange "{min_frequency}", "{max_frequency}"'
    project.modeler.add_to_history('ChangeFrequency', sCommand)
    return {"status": "success", "message": f"频率范围已修改为 {min_frequency}-{max_frequency} GHz"}

@mcp.tool()
def define_frequency_range(start_freq: float, end_freq: float):
    """定义频率范围"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Solver.FrequencyRange \"{start_freq}\", \"{end_freq}\"'
    project.modeler.add_to_history('define frequency range', sCommand)
    return {"status": "success", "message": f"Frequency range set to {start_freq}-{end_freq}"}

@mcp.tool()
def define_background():
    """定义背景"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    vba_code = ['With Background', '.ResetBackground', '.Type "Normal"', 'End With']
    sCommand = line_break.join(vba_code)
    project.modeler.add_to_history('define background', sCommand)
    return {"status": "success", "message": "Background defined"}

@mcp.tool()
def define_boundary():
    """定义边界条件"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    vba_code = [
        'With Boundary',
        '.Xmin "expanded open"', '.Xmax "expanded open"',
        '.Ymin "expanded open"', '.Ymax "expanded open"',
        '.Zmin "expanded open"', '.Zmax "expanded open"',
        '.Xsymmetry "none"', '.Ysymmetry "none"', '.Zsymmetry "none"',
        'End With'
    ]
    sCommand = line_break.join(vba_code)
    project.modeler.add_to_history('define boundary', sCommand)
    return {"status": "success", "message": "Boundary conditions defined"}

@mcp.tool()
def define_mesh(steps_per_wave_near: int = 5, steps_per_wave_far: int = 5,
                steps_per_box_near: int = 5, steps_per_box_far: int = 1,
                edge_refinement_ratio: int = 2, edge_refinement_buffer_lines: int = 3,
                ratio_limit_geometry: int = 10, equilibrate_value: float = 1.5,
                use_gpu: bool = True):
    """定义网格"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']

    VBA_code = [
        'With Mesh', '     .MeshType "PBA" ', '     .SetCreator "High Frequency"', 'End With ',
        'With MeshSettings ', '     .SetMeshType "Hex" ', '     .Set "Version", 1%',
        "     'MAX CELL - WAVELENGTH REFINEMENT",
        f'     .Set "StepsPerWaveNear", "{steps_per_wave_near}" ',
        f'     .Set "StepsPerWaveFar", "{steps_per_wave_far}" ',
        '     .Set "WavelengthRefinementSameAsNear", "1" ',
        "     'MAX CELL - GEOMETRY REFINEMENT",
        f'     .Set "StepsPerBoxNear", "{steps_per_box_near}" ',
        f'     .Set "StepsPerBoxFar", "{steps_per_box_far}" ',
        '     .Set "MaxStepNear", "0" ', '     .Set "MaxStepFar", "0" ',
        '     .Set "ModelBoxDescrNear", "maxedge" ', '     .Set "ModelBoxDescrFar", "maxedge" ',
        '     .Set "UseMaxStepAbsolute", "0" ', '     .Set "GeometryRefinementSameAsNear", "0" ',
        "     'MIN CELL",
        '     .Set "UseRatioLimitGeometry", "1" ',
        f'     .Set "RatioLimitGeometry", "{ratio_limit_geometry}" ',
        '     .Set "MinStepGeometryX", "0" ', '     .Set "MinStepGeometryY", "0" ',
        '     .Set "MinStepGeometryZ", "0" ', '     .Set "UseSameMinStepGeometryXYZ", "1" ',
        'End With',
        'With MeshSettings', '     .SetMeshType "Hex" ', '     .Set "PlaneMergeVersion", "2" ', 'End With',
        'With MeshSettings', '     .SetMeshType "Hex" ',
        '     .Set "FaceRefinementOn", "0" ', '     .Set "FaceRefinementPolicy", "2" ',
        '     .Set "FaceRefinementRatio", "2" ', '     .Set "FaceRefinementStep", "0" ',
        '     .Set "FaceRefinementNSteps", "2" ', '     .Set "EllipseRefinementOn", "0" ',
        '     .Set "EllipseRefinementPolicy", "2" ', '     .Set "EllipseRefinementRatio", "2" ',
        '     .Set "EllipseRefinementStep", "0" ', '     .Set "EllipseRefinementNSteps", "2" ',
        '     .Set "FaceRefinementBufferLines", "3" ',
        '     .Set "EdgeRefinementOn", "1" ', '     .Set "EdgeRefinementPolicy", "1" ',
        f'     .Set "EdgeRefinementRatio", "{edge_refinement_ratio}" ',
        '     .Set "EdgeRefinementStep", "0" ',
        f'     .Set "EdgeRefinementBufferLines", "{edge_refinement_buffer_lines}" ',
        '     .Set "RefineEdgeMaterialGlobal", "0" ', '     .Set "RefineAxialEdgeGlobal", "0" ',
        '     .Set "BufferLinesNear", "3" ', '     .Set "UseDielectrics", "1" ',
        '     .Set "EquilibrateOn", "1" ', f'     .Set "Equilibrate", "{equilibrate_value}" ',
        '     .Set "IgnoreThinPanelMaterial", "0" ', 'End With ',
        'With MeshSettings ', '     .SetMeshType "Hex" ',
        '     .Set "SnapToAxialEdges", "1"', '     .Set "SnapToPlanes", "1"',
        '     .Set "SnapToSpheres", "1"', '     .Set "SnapToEllipses", "1"',
        '     .Set "SnapToCylinders", "1"', '     .Set "SnapToCylinderCenters", "1"',
        '     .Set "SnapToEllipseCenters", "1"', 'End With ',
        'With Mesh ', '     .ConnectivityCheck "True"', '     .UsePecEdgeModel "True" ',
        '     .PointAccEnhancement "0" ', '     .TSTVersion "0"',
        '     .PBAVersion "2023042623" ', '     .SetCADProcessingMethod "MultiThread22", "-1" ',
        f'     .SetGPUForMatrixCalculationDisabled "{not use_gpu}" ', 'End With',
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history("Define Mesh", sCommand)
    return {"status": "success", "message": f"Mesh defined with steps_per_wave={steps_per_wave_near}, steps_per_box={steps_per_box_near}"}

@mcp.tool()
def define_solver():
    """定义求解器"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    VBA_code = [
        'Mesh.SetCreator "High Frequency" ',
        'With Solver ',
        '     .Method "Hexahedral"', '     .CalculationType "TD-S"',
        '     .StimulationPort "All"', '     .StimulationMode "All"',
        '     .SteadyStateLimit "-40"', '     .MeshAdaption "False"',
        '     .AutoNormImpedance "True"', '     .NormingImpedance "50"',
        '     .CalculateModesOnly "False"', '     .SParaSymmetry "False"',
        '     .StoreTDResultsInCache  "False"', '     .RunDiscretizerOnly "False"',
        '     .FullDeembedding "False"', '     .SuperimposePLWExcitation "False"',
        '     .UseSensitivityAnalysis "False"',
        'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history("Define Solver", sCommand)
    return {"status": "success", "message": "Solver defined"}

# ---------- 端口与监视器（4个）----------

@mcp.tool()
def define_port(port_number: str, x_min: float, x_max: float, y_min: float, y_max: float,
               z_min: float, z_max: float, orientation: str):
    """定义端口"""
    global call_counts, line_break
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    call_counts['port'] += 1

    param_prefix = f"port_{port_number}_"
    x_min_param = parameter_set(f"{param_prefix}x_min", x_min)["message"].split()[1]
    x_max_param = parameter_set(f"{param_prefix}x_max", x_max)["message"].split()[1]
    y_min_param = parameter_set(f"{param_prefix}y_min", y_min)["message"].split()[1]
    y_max_param = parameter_set(f"{param_prefix}y_max", y_max)["message"].split()[1]
    z_min_param = parameter_set(f"{param_prefix}z_min", z_min)["message"].split()[1]
    z_max_param = parameter_set(f"{param_prefix}z_max", z_max)["message"].split()[1]

    VBA_code = [
        'With Port', '    .Reset', f'    .PortNumber "{port_number}"',
        '    .Label ""', '    .Folder ""', '    .NumberOfModes "1"',
        '    .AdjustPolarization "False"', '    .PolarizationAngle "0.0"',
        '    .ReferencePlaneDistance "0"', '    .TextSize "50"',
        '    .TextMaxLimit "1"', '    .Coordinates "Free"',
        f'    .Orientation "{orientation}"', '    .PortOnBound "False"',
        '    .ClipPickedPortToBound "False"',
        f'    .Xrange {x_min_param}, {x_max_param}',
        f'    .Yrange {y_min_param}, {y_max_param}',
        f'    .Zrange {z_min_param}, {z_max_param}',
        '    .XrangeAdd "0.0", "0.0"', '    .YrangeAdd "0.0", "0.0"',
        '    .ZrangeAdd "0.0", "0.0"', '    .SingleEnded "False"',
        '    .WaveguideMonitor "False"', '    .Create', 'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Port:{port_number}", sCommand)
    project.modeler.add_to_history('ZoomToStructure', 'Plot.ZoomToStructure')
    return {"status": "success", "message": f"Port {port_number} created successfully"}

@mcp.tool()
def define_monitor(start_freq: float, end_freq: float, step: float):
    """定义远场方向图监视器"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    VBA_code = [
        'With Monitor', '.Reset ', '.Domain "Frequency"',
        '.FieldType "Farfield"', '.ExportFarfieldSource "False" ',
        '.UseSubvolume "False" ', '.Coordinates "Structure" ',
        '.SetSubvolume "-17.7", "17.7", "-17.7", "17.7", "0", "20" ',
        '.SetSubvolumeOffset "10", "10", "10", "10", "10", "10" ',
        '.SetSubvolumeInflateWithOffset "False" ',
        '.SetSubvolumeOffsetType "FractionOfWavelength" ',
        '.EnableNearfieldCalculation "True" ',
        f'.CreateUsingLinearStep \"{start_freq}\", \"{end_freq}\", \"{step}\"',
        'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history("Define Monitor", sCommand)
    return {"status": "success", "message": f"Farfield monitor created"}

@mcp.tool()
def set_field_monitor(field_type: str, start_frequency: str, end_frequency: str, num_samples: str):
    """设置场监视器"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Monitor.Reset{line_break}Monitor.Domain "Frequency"{line_break}Monitor.FieldType "{field_type}field"{line_break}Monitor.Dimension "Volume"{line_break}Monitor.CreateUsingLinearSamples "{start_frequency}", "{end_frequency}", "{num_samples}"'
    project.modeler.add_to_history(f"Set{field_type}Monitor", sCommand)
    return {"status": "success", "message": f"{field_type}场监视器已设置，频率范围 {start_frequency}-{end_frequency} GHz"}

@mcp.tool()
def set_probe(field_type: str, x_pos: str, y_pos: str, z_pos: str):
    """设置探针"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Probe.Reset{line_break}Probe.AutoLabel 1{line_break}Probe.Field "{field_type}field"{line_break}Probe.Orientation "All"{line_break}Probe.Xpos "{x_pos}"{line_break}Probe.Ypos "{y_pos}"{line_break}Probe.Zpos "{z_pos}"{line_break}Probe.Create'
    project.modeler.add_to_history(f"Set{field_type}Probe", sCommand)
    return {"status": "success", "message": f"{field_type}场探针已设置于 ({x_pos}, {y_pos}, {z_pos})"}

@mcp.tool()
def delete_probe_by_id(probe_id: str):
    """删除探针"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'Probe.DeleteById "{probe_id}"'
    project.modeler.add_to_history(f"DeleteProbe{probe_id}", sCommand)
    return {"status": "success", "message": f"探针 {probe_id} 已删除"}

@mcp.tool()
def show_bounding_box():
    """显示边界框"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = 'Plot.DrawBox "True"'
    project.modeler.add_to_history('switch bounding box', sCommand)
    return {"status": "success", "message": "Bounding box displayed"}

# ---------- 数据导出（4个）----------

@mcp.tool()
def export_s_parameter(file_path: str, format_type: str = "csv"):
    """导出S参数数据"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'SelectTreeItem "1D Results\\S-Parameters"{line_break}ASCIIExport.Reset{line_break}ASCIIExport.FileName "{file_path}"{line_break}ASCIIExport.Execute'
    project.modeler.add_to_history('ExportSParameter', sCommand)
    return {"status": "success", "message": f"S参数已导出至 {file_path}"}

@mcp.tool()
def export_e_field_data(frequency: str, file_path: str):
    """导出电场仿真数据"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'SelectTreeItem "2D/3D Results\\E-Field\\e-field (f={frequency}) [pw]"{line_break}ASCIIExport.Reset{line_break}ASCIIExport.FileName "{file_path}\\E-field-{frequency}GHz.txt"{line_break}ASCIIExport.Execute'
    project.modeler.add_to_history('ExportEField', sCommand)
    return {"status": "success", "message": f"电场数据已导出至 {file_path}"}

@mcp.tool()
def export_surface_current_data(frequency: str, file_path: str):
    """导出表面电流仿真数据"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'SelectTreeItem "2D/3D Results\\Surface Current\\surface current (f={frequency}) [pw]"{line_break}ASCIIExport.Reset{line_break}ASCIIExport.FileName "{file_path}\\Surface-Current-{frequency}GHz.txt"{line_break}ASCIIExport.Execute'
    project.modeler.add_to_history('ExportSurfaceCurrent', sCommand)
    return {"status": "success", "message": f"表面电流数据已导出至 {file_path}"}

@mcp.tool()
def export_voltage_data(voltage_index: str, file_path: str):
    """导出电压监视器数据"""
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}
    project = project_data['project']
    sCommand = f'SelectTreeItem "1D Results\\Voltage Monitors\\voltage{voltage_index} [pw]"{line_break}ASCIIExport.Reset{line_break}ASCIIExport.FileName "{file_path}\\voltage-{voltage_index}.txt"{line_break}ASCIIExport.Execute'
    project.modeler.add_to_history(f"ExportVoltage{voltage_index}", sCommand)
    return {"status": "success", "message": f"电压数据 (index={voltage_index}) 已导出至 {file_path}"}


# ============================================================
# 主函数
# ============================================================
if __name__ == "__main__":
    mcp.run(transport='stdio')
