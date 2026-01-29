import cst
import cst.interface
import os
from mcp.server import FastMCP

# 创建MCP实例
mcp = FastMCP("cst_interface", log_level="ERROR")

# 全局变量：暂存单个project对象和相关信息
# 用于解决MCP无法直接传递Python对象的问题
_current_project = None
_current_fullpath = None

# 全局变量：存储参数和调用计数
global_parameters = {}
call_counts = {
    'cylinder': 0,
    'cone': 0,
    'port': 0,
    'brick': 0
}
line_break = '\n'


# ==============================
# 全局辅助函数
# ==============================

def save_project_object(project, fullpath):
    """
    保存单个project对象到全局变量
    Args:
        project: CST项目对象
        fullpath: 项目文件路径
    """
    global _current_project, _current_fullpath
    _current_project = project
    _current_fullpath = fullpath

def get_project_object():
    """
    从全局变量获取当前project对象
    Returns:
        dict: 包含project和fullpath的字典，或None
    """
    global _current_project, _current_fullpath
    if _current_project is not None:
        return {
            'project': _current_project,
            'fullpath': _current_fullpath
        }
    return None

def clear_project_object():
    """
    清除当前project对象
    """
    global _current_project, _current_fullpath, global_parameters, call_counts
    _current_project = None
    _current_fullpath = None
    global_parameters.clear()
    # 重置调用计数
    call_counts = {
        'cylinder': 0,
        'cone': 0,
        'port': 0,
        'brick': 0
    }


def _generate_unique_param_name(name):
    """
    生成唯一的参数名
    Args:
        name (str): 参数名
    Returns:
        str: 唯一的参数名
    """
    global global_parameters
    if name not in global_parameters:
        return name

    # 参数已存在，生成带数字后缀的新名称
    if "_" in name:
        parts = name.rsplit("_", 1)
        if parts[1].isdigit():
            base_name = parts[0]
        else:
            base_name = name
    else:
        base_name = name

    # 查找所有以基础参数名为前缀的参数，找到最大的数字后缀
    max_suffix = 0
    prefix = f"{base_name}_"
    prefix_len = len(prefix)

    for p_name in global_parameters:
        if p_name == base_name:
            max_suffix = 1
        elif p_name.startswith(prefix):
            try:
                suffix = int(p_name[prefix_len:])
                if suffix > max_suffix:
                    max_suffix = suffix
            except ValueError:
                pass

    return f"{base_name}_{max_suffix + 1}"


# ==============================
# 项目管理函数
# ==============================

# MCP工具：初始化CST项目
@mcp.tool()
def init_cst_project(path: str, base_name: str, ext: str):
    """
    初始化CST项目
    Args:
        path (str): 项目路径
        base_name (str): 基础文件名
        ext (str): 文件扩展名
    Returns:
        dict: 包含fullpath的字典
    """
    global global_parameters, call_counts

    # 清空之前的参数和调用计数
    global_parameters.clear()
    call_counts = {
        'cylinder': 0,
        'cone': 0,
        'port': 0,
        'brick': 0
    }

    idx = 0
    while True:
        filename = f"{base_name}_{idx}{ext}"
        fullpath = os.path.join(path, filename)
        if not os.path.exists(fullpath):
            break
        idx += 1

    # 创建新的CST Design Environment实例
    de = cst.interface.DesignEnvironment.new()
    # 创建新的MWS项目
    project = de.new_mws()
    # 保存项目
    project.save(fullpath)

    # 保存project对象到全局变量
    save_project_object(project, fullpath)

    return {"status": "success", "fullpath": fullpath}


# MCP工具：保存项目
@mcp.tool()
def save_project():
    """
    保存当前项目
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    try:
        project_data['project'].save()
        return {"status": "success", "message": f"项目已保存: {project_data['fullpath']}"}
    except Exception as e:
        return {"status": "error", "message": f"保存项目失败: {str(e)}"}


# MCP工具：关闭项目
@mcp.tool()
def close_project():
    """
    关闭当前项目
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    try:
        project_data['project'].close()
        clear_project_object()
        return {"status": "success", "message": f"项目已关闭: {project_data['fullpath']}"}
    except Exception as e:
        return {"status": "error", "message": f"关闭项目失败: {str(e)}"}


# ==============================
# 参数管理函数
# ==============================

@mcp.tool()
def parameter_set(name: str, value=None):
    """
    参数设置函数，一般在建模函数内调用，禁止用于建模前设参，否则会与建模函数内的设参函数冲突
    Args:
        name (str): 参数名
        value: 参数值
    Returns:
        dict: 操作结果
    """
    global global_parameters

    # 获取当前项目对象
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    # 单个参数处理逻辑
    param_name = _generate_unique_param_name(name)

    # 根据参数类型生成不同的命令格式
    if isinstance(value, (int, float)):
        sCommand = f'MakeSureParameterExists("{param_name}", "{value:.6f}")'
    else:
        sCommand = f'MakeSureParameterExists("{param_name}", "{value}")'

    # 只有当modeler存在时才添加到history
    if project.modeler is not None:
        project.modeler.add_to_history('StoreParameter', sCommand)
    global_parameters[param_name] = value
    return {"status": "success", "message": f"Parameter {param_name} set to {value}"}


# ==============================
# 基础几何定义函数
# ==============================

# MCP工具：定义长方体
@mcp.tool()
def define_brick(name: str, component: str, material: str, x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float):
    """
    定义长方体函数，直接输入数据，禁止输入变量，参数会在函数中设置
    Args:
        name (str): 长方体名称
        component (str): 组件名称
        material (str): 材料名称
        x_min (float): X轴最小值
        x_max (float): X轴最大值
        y_min (float): Y轴最小值
        y_max (float): Y轴最大值
        z_min (float): Z轴最小值
        z_max (float): Z轴最大值
    Returns:
        dict: 操作结果
    """
    global call_counts, global_parameters, line_break

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    call_counts['brick'] += 1

    # 存储参数到CST history中，便于后期调整
    param_prefix = f"brick_{name}_"

    # 保存parameter_set返回的唯一参数名
    x_min_param = parameter_set(f"{param_prefix}x_min", x_min)["message"].split()[1]
    x_max_param = parameter_set(f"{param_prefix}x_max", x_max)["message"].split()[1]
    y_min_param = parameter_set(f"{param_prefix}y_min", y_min)["message"].split()[1]
    y_max_param = parameter_set(f"{param_prefix}y_max", y_max)["message"].split()[1]
    z_min_param = parameter_set(f"{param_prefix}z_min", z_min)["message"].split()[1]
    z_max_param = parameter_set(f"{param_prefix}z_max", z_max)["message"].split()[1]

    # 构建VBA代码
    VBA_code = [
        "With Brick",
        "    .Reset",
        f"    .Name \"{name}\"",
        f"    .Component \"{component}\"",
        f"    .Material \"{material}\"",
        f"    .Xrange {x_min_param}, {x_max_param}",
        f"    .Yrange {y_min_param}, {y_max_param}",
        f"    .Zrange {z_min_param}, {z_max_param}",
        "    .Create",
        "End With"
    ]

    sCommand = line_break.join(VBA_code)

    try:
        project.modeler.add_to_history(f"Define Brick:{name}", sCommand)
        return {"status": "success", "message": f"Brick {name} created successfully"}
    except Exception as e:
        # 捕获并返回详细错误信息
        error_msg = f"创建长方体失败: {str(e)}"
        print(f"Error in define_brick: {error_msg}")
        return {"status": "error", "message": error_msg, "command": sCommand}


# MCP工具：定义圆柱体
@mcp.tool()
def define_cylinder(name: str, component: str, material: str, outer_radius: float, inner_radius: float,
                  axis: str, z_min: float, z_max: float, x_center: float = 0.0, y_center: float = 0.0, segments: int = 0):
    """
    定义圆柱体函数，直接输入数据，参数会在函数中设置
    Args:
        name (str): 圆柱体名称
        component (str): 组件名称
        material (str): 材料名称
        outer_radius (float): 外半径
        inner_radius (float): 内半径
        axis (str): 轴线方向
        z_min (float): Z轴最小值
        z_max (float): Z轴最大值
        x_center (float, optional): X轴中心位置
        y_center (float, optional): Y轴中心位置
        segments (int, optional): 分段数
    Returns:
        dict: 操作结果
    """
    global call_counts, line_break

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    call_counts['cylinder'] += 1

    # 存储参数到CST history中，便于后期调整
    param_prefix = f"cylinder_{name}_"

    # 保存parameter_set返回的唯一参数名
    outer_radius_param = parameter_set(f"{param_prefix}outer_radius", outer_radius)["message"].split()[1]
    inner_radius_param = parameter_set(f"{param_prefix}inner_radius", inner_radius)["message"].split()[1]
    z_min_param = parameter_set(f"{param_prefix}z_min", z_min)["message"].split()[1]
    z_max_param = parameter_set(f"{param_prefix}z_max", z_max)["message"].split()[1]
    x_center_param = parameter_set(f"{param_prefix}x_center", x_center)["message"].split()[1]
    y_center_param = parameter_set(f"{param_prefix}y_center", y_center)["message"].split()[1]

    # 在VBA代码中使用存储的参数名
    VBA_code = [
        "With Cylinder",
        "    .Reset",
        f"    .Name \"{name}\"",
        f"    .Component \"{component}\"",
        f"    .Material \"{material}\"",
        f"    .OuterRadius {outer_radius_param}",
        f"    .InnerRadius {inner_radius_param}",
        f"    .Axis \"{axis}\"",
        f"    .Zrange {z_min_param}, {z_max_param}",
        f"    .Xcenter {x_center_param}",
        f"    .Ycenter {y_center_param}",
        f"    .Segments \"{segments}\"",
        "    .Create",
        "End With"
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Cylinder:{name}", sCommand)
    return {"status": "success", "message": f"Cylinder {name} created successfully"}


# MCP工具：定义圆锥体
@mcp.tool()
def define_cone(name: str, component: str, material: str, bottom_radius: float, top_radius: float,
             axis: str, z_min: float, z_max: float, x_center: float = 0.0, y_center: float = 0.0, segments: int = 0):
    """
    定义圆锥体函数，直接输入数据，参数会在函数中设置
    Args:
        name (str): 圆锥体名称
        component (str): 组件名称
        material (str): 材料名称
        bottom_radius (float): 底部半径
        top_radius (float): 顶部半径
        axis (str): 轴线方向
        z_min (float): Z轴最小值
        z_max (float): Z轴最大值
        x_center (float, optional): X轴中心位置
        y_center (float, optional): Y轴中心位置
        segments (int, optional): 分段数
    Returns:
        dict: 操作结果
    """
    global call_counts, line_break

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    call_counts['cone'] += 1

    # 存储参数到CST history中，便于后期调整
    param_prefix = f"cone_{name}_"

    # 保存parameter_set返回的唯一参数名
    bottom_radius_param = parameter_set(f"{param_prefix}bottom_radius", bottom_radius)["message"].split()[1]
    top_radius_param = parameter_set(f"{param_prefix}top_radius", top_radius)["message"].split()[1]
    z_min_param = parameter_set(f"{param_prefix}z_min", z_min)["message"].split()[1]
    z_max_param = parameter_set(f"{param_prefix}z_max", z_max)["message"].split()[1]
    x_center_param = parameter_set(f"{param_prefix}x_center", x_center)["message"].split()[1]
    y_center_param = parameter_set(f"{param_prefix}y_center", y_center)["message"].split()[1]

    # 在VBA代码中使用存储的参数名
    VBA_code = [
        "With Cone",
        "    .Reset",
        f"    .Name \"{name}\"",
        f"    .Component \"{component}\"",
        f"    .Material \"{material}\"",
        f"    .BottomRadius {bottom_radius_param}",
        f"    .TopRadius {top_radius_param}",
        f"    .Axis \"{axis}\"",
        f"    .Zrange {z_min_param}, {z_max_param}",
        f"    .Xcenter {x_center_param}",
        f"    .Ycenter {y_center_param}",
        f"    .Segments \"{segments}\"",
        "    .Create",
        "End With"
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Cone:{name}", sCommand)
    return {"status": "success", "message": f"Cone {name} created successfully"}


# MCP工具：定义长方形
@mcp.tool()
def define_rectangle(name: str, curve: str, x_min: float, x_max: float, y_min: float, y_max: float):
    """
    定义长方形函数
    Args:
        name (str): 长方形名称
        curve (str): 曲线名称
        x_min (float): X轴最小值
        x_max (float): X轴最大值
        y_min (float): Y轴最小值
        y_max (float): Y轴最大值
    Returns:
        dict: 操作结果
    """
    global line_break

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    VBA_code = [
        'With Rectangle',
        '    .Reset',
        f'    .Name "{name}"',
        f'    .Curve "{curve}"',
        f'    .Xrange {x_min}, {x_max}',
        f'    .Yrange {y_min}, {y_max}',
        '    .Create',
        'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Rectangle:{name}", sCommand)
    return {"status": "success", "message": f"Rectangle {name} created successfully"}


# ==============================
# 布尔运算函数
# ==============================

# MCP工具：布尔差集运算
@mcp.tool()
def boolean_subtract(target: str, tool: str):
    """
    布尔差集运算函数
    Args:
        target (str): 目标形状
        tool (str): 工具形状
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = f'Solid.Subtract \"{target}\", \"{tool}\"'
    history_name = f"boolean subtract shapes: {target}, {tool}"
    project.modeler.add_to_history(history_name, sCommand)
    return {"status": "success", "message": f"Boolean subtract {target} - {tool} completed"}


# MCP工具：布尔和运算
@mcp.tool()
def boolean_add(shape1: str, shape2: str):
    """
    布尔和运算函数
    Args:
        shape1 (str): 第一个形状
        shape2 (str): 第二个形状
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = f'Solid.Add \"{shape1}\", \"{shape2}\"'
    history_name = f"boolean add shapes: {shape1}, {shape2}"
    project.modeler.add_to_history(history_name, sCommand)
    return {"status": "success", "message": f"Boolean add {shape1} + {shape2} completed"}


# MCP工具：布尔交集运算
@mcp.tool()
def boolean_intersect(shape1: str, shape2: str):
    """
    布尔交集运算函数
    Args:
        shape1 (str): 第一个形状
        shape2 (str): 第二个形状
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = f'Solid.Intersect \"{shape1}\", \"{shape2}\"'
    history_name = f"boolean intersect shapes: {shape1}, {shape2}"
    project.modeler.add_to_history(history_name, sCommand)
    return {"status": "success", "message": f"Boolean intersect {shape1} & {shape2} completed"}


# MCP工具：布尔插入运算
@mcp.tool()
def boolean_insert(shape1: str, shape2: str):
    """
    布尔插入运算函数（shape1减去与shape2重合的部分，并且保留sahpe2）
    Args:
        shape1 (str): 第一个形状
        shape2 (str): 第二个形状
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = f'Solid.Insert \"{shape1}\", \"{shape2}\"'
    history_name = f"boolean insert shapes: {shape1}, {shape2}"
    project.modeler.add_to_history(history_name, sCommand)
    return {"status": "success", "message": f"Boolean insert {shape1} insert {shape2} completed"}


# ==============================
# 仿真设置函数
# ==============================

# MCP工具：定义频率范围
@mcp.tool()
def define_frequency_range(start_freq: float, end_freq: float):
    """
    定义频率范围函数
    Args:
        start_freq (float): 起始频率
        end_freq (float): 结束频率
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = f'Solver.FrequencyRange \"{start_freq}\", \"{end_freq}\"'
    project.modeler.add_to_history('define frequency range', sCommand)
    return {"status": "success", "message": f"Frequency range set to {start_freq}-{end_freq}"}


@mcp.tool()
def define_port(port_number: str, x_min: float, x_max: float, y_min: float, y_max: float, z_min: float, z_max: float, orientation: str):
    """
    定义端口函数，一般为二维，方向轴范围的min=max=在轴上的位置
    Args:
        port_number (str): 端口号
        x_min (float): X轴范围最小值
        x_max (float): X轴范围最大值
        y_min (float): Y轴范围最小值
        y_max (float): Y轴范围最大值
        z_min (float): Z轴范围最小值
        z_max (float): Z轴范围最大值
        orientation (str): 端口方向（如"xmin", "xmax", "ymin", "ymax", "zmin", "zmax"等）
    Returns:
        dict: 操作结果
    """
    global call_counts, line_break

    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    call_counts['port'] += 1

    VBA_code = [
        'With Port',
        '    .Reset',
        f'    .PortNumber "{port_number}"',
        '    .Label ""',
        '    .Folder ""',
        '    .NumberOfModes "1"',
        '    .AdjustPolarization "False"',
        '    .PolarizationAngle "0.0"',
        '    .ReferencePlaneDistance "0"',
        '    .TextSize "50"',
        '    .TextMaxLimit "1"',
        '    .Coordinates "Free"',
        f'    .Orientation "{orientation}"',
        '    .PortOnBound "True"',
        '    .ClipPickedPortToBound "False"',
        f'    .Xrange {x_min}, {x_max}',
        f'    .Yrange {y_min}, {y_max}',
        f'    .Zrange {z_min}, {z_max}',
        '    .XrangeAdd "0.0", "0.0"',
        '    .YrangeAdd "0.0", "0.0"',
        '    .ZrangeAdd "0.0", "0.0"',
        '    .SingleEnded "False"',
        '    .WaveguideMonitor "False"',
        '    .Create',
        'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history(f"Define Port:{port_number}", sCommand)
    project.modeler.add_to_history('ZoomToStructure', 'Plot.ZoomToStructure')
    return {"status": "success", "message": f"Port {port_number} created successfully"}


# MCP工具：定义远场方向图监视器
@mcp.tool()
def define_monitor(start_freq: float, end_freq: float, step: float):
    """
    定义远场方向图监视器函数
    Args:
        start_freq (float): 起始频率
        end_freq (float): 结束频率
        step (float): 频率步长
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    VBA_code = [
        'With Monitor',
              '.Reset ',
              '.Domain "Frequency"',
              '.FieldType "Farfield"',
              '.ExportFarfieldSource "False" ',
              '.UseSubvolume "False" ',
              '.Coordinates "Structure" ',
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


# MCP工具：定义背景
@mcp.tool()
def define_background():
    """
    定义背景函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    vba_code = [
        'With Background',
        '.ResetBackground',
        '.Type "Normal"',
        'End With'
    ]
    sCommand = line_break.join(vba_code)
    project.modeler.add_to_history('define background', sCommand)
    return {"status": "success", "message": "Background defined"}


# MCP工具：定义边界条件
@mcp.tool()
def define_boundary():
    """
    定义边界条件函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    vba_code = [
        'With Boundary',
        '.Xmin "expanded open"',
        '.Xmax "expanded open"',
        '.Ymin "expanded open"',
        '.Ymax "expanded open"',
        '.Zmin "expanded open"',
        '.Zmax "expanded open"',
        '.Xsymmetry "none"',
        '.Ysymmetry "none"',
        '.Zsymmetry "none"',
        'End With'
    ]
    sCommand = line_break.join(vba_code)
    project.modeler.add_to_history('define boundary', sCommand)
    return {"status": "success", "message": "Boundary conditions defined"}


# MCP工具：显示边界框
@mcp.tool()
def show_bounding_box():
    """
    显示边界框函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']
    sCommand = 'Plot.DrawBox "True"'
    project.modeler.add_to_history('switch bounding box', sCommand)
    return {"status": "success", "message": "Bounding box displayed"}


# MCP工具：定义网格
@mcp.tool()
def define_mesh():
    """
    定义网格函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    VBA_code = [
        'With Mesh',
         '     .MeshType "PBA" ',
         '     .SetCreator "High Frequency"',
        'End With ',
        'With MeshSettings ',
         '     .SetMeshType "Hex" ',
         '     .Set "Version", 1%',
         "     'MAX CELL - WAVELENGTH REFINEMENT",
         '     .Set "StepsPerWaveNear", "5" ',
         '     .Set "StepsPerWaveFar", "5" ',
         '     .Set "WavelengthRefinementSameAsNear", "1" ',
         "     'MAX CELL - GEOMETRY REFINEMENT",
         '     .Set "StepsPerBoxNear", "5" ',
         '     .Set "StepsPerBoxFar", "1" ',
         '     .Set "MaxStepNear", "0" ',
         '     .Set "MaxStepFar", "0" ',
         '     .Set "ModelBoxDescrNear", "maxedge" ',
         '     .Set "ModelBoxDescrFar", "maxedge" ',
         '     .Set "UseMaxStepAbsolute", "0" ',
         '     .Set "GeometryRefinementSameAsNear", "0" ',
         "     'MIN CELL" ,
         '     .Set "UseRatioLimitGeometry", "1" ',
         '     .Set "RatioLimitGeometry", "10" ',
         '     .Set "MinStepGeometryX", "0" ',
         '     .Set "MinStepGeometryY", "0" ',
         '     .Set "MinStepGeometryZ", "0" ',
         '     .Set "UseSameMinStepGeometryXYZ", "1" ',
        'End With',
        'With MeshSettings',
         '     .SetMeshType "Hex" ',
         '     .Set "PlaneMergeVersion", "2" ',
        'End With',
        'With MeshSettings',
         '     .SetMeshType "Hex" ',
         '     .Set "FaceRefinementOn", "0" ',
         '     .Set "FaceRefinementPolicy", "2" ',
         '     .Set "FaceRefinementRatio", "2" ',
         '     .Set "FaceRefinementStep", "0" ',
         '     .Set "FaceRefinementNSteps", "2" ',
         '     .Set "EllipseRefinementOn", "0" ',
         '     .Set "EllipseRefinementPolicy", "2" ',
         '     .Set "EllipseRefinementRatio", "2" ',
         '     .Set "EllipseRefinementStep", "0" ',
         '     .Set "EllipseRefinementNSteps", "2" ',
         '     .Set "FaceRefinementBufferLines", "3" ',
         '     .Set "EdgeRefinementOn", "1" ',
         '     .Set "EdgeRefinementPolicy", "1" ',
         '     .Set "EdgeRefinementRatio", "2" ',
         '     .Set "EdgeRefinementStep", "0" ',
         '     .Set "EdgeRefinementBufferLines", "3" ',
         '     .Set "RefineEdgeMaterialGlobal", "0" ',
         '     .Set "RefineAxialEdgeGlobal", "0" ',
         '     .Set "BufferLinesNear", "3" ',
         '     .Set "UseDielectrics", "1" ',
         '     .Set "EquilibrateOn", "1" ',
         '     .Set "Equilibrate", "1.5" ',
         '     .Set "IgnoreThinPanelMaterial", "0" ',
        'End With ',
        'With MeshSettings ',
         '     .SetMeshType "Hex" ',
         '     .Set "SnapToAxialEdges", "1"',
         '     .Set "SnapToPlanes", "1"',
         '     .Set "SnapToSpheres", "1"',
         '     .Set "SnapToEllipses", "1"',
         '     .Set "SnapToCylinders", "1"',
         '     .Set "SnapToCylinderCenters", "1"',
         '     .Set "SnapToEllipseCenters", "1"',
        'End With ',
        'With Mesh ',
         '     .ConnectivityCheck "True"',
         '     .UsePecEdgeModel "True" ',
         '     .PointAccEnhancement "0" ',
         '     .TSTVersion "0"',
         '     .PBAVersion "2023042623" ',
         '     .SetCADProcessingMethod "MultiThread22", "-1" ',
         '     .SetGPUForMatrixCalculationDisabled "False" ',
        'End With',
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history("Define Mesh", sCommand)
    return {"status": "success", "message": "Mesh defined"}


# MCP工具：定义求解器
@mcp.tool()
def define_solver():
    """
    定义求解器函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    VBA_code = [
    'Mesh.SetCreator "High Frequency" ',
    'With Solver ',
         '.Method "Hexahedral"',
         '.CalculationType "TD-S"',
         '.StimulationPort "All"',
         '.StimulationMode "All"',
         '.SteadyStateLimit "-40"',
         '.MeshAdaption "False"',
         '.AutoNormImpedance "True"',
         '.NormingImpedance "50"',
         '.CalculateModesOnly "False"',
         '.SParaSymmetry "False"',
         '.StoreTDResultsInCache  "False"',
         '.RunDiscretizerOnly "False"',
         '.FullDeembedding "False"',
         '.SuperimposePLWExcitation "False"',
         '.UseSensitivityAnalysis "False"',
    'End With'
    ]
    sCommand = line_break.join(VBA_code)
    project.modeler.add_to_history("Define Solver", sCommand)
    return {"status": "success", "message": "Solver defined"}


# ==============================
# 仿真控制函数
# ==============================

# MCP工具：同步开始仿真
@mcp.tool()
def start_simulation():
    """
    开始仿真函数（同步执行，等待仿真完成）
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 开始仿真（同步执行，直到完成）
        project.modeler.run_solver()
        return {"status": "success", "message": "仿真已成功完成"}
    except Exception as e:
        return {"status": "error", "message": f"仿真失败: {str(e)}"}


# MCP工具：异步开始仿真
@mcp.tool()
def start_simulation_async():
    """
    异步开始仿真函数（启动仿真后立即返回，不等待完成）
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 异步开始仿真（立即返回，不等待完成）
        project.modeler.start_solver()
        return {"status": "success", "message": "仿真已成功启动"}
    except Exception as e:
        return {"status": "error", "message": f"仿真启动失败: {str(e)}"}


# MCP工具：检查仿真状态
@mcp.tool()
def is_simulation_running():
    """
    检查仿真状态函数
    Returns:
        dict: 包含仿真状态的操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 检查仿真状态
        running = project.modeler.is_solver_running()
        return {"status": "success", "message": f"仿真状态: {'运行中' if running else '未运行'}", "running": running}
    except Exception as e:
        return {"status": "error", "message": f"检查仿真状态失败: {str(e)}"}


# MCP工具：暂停仿真
@mcp.tool()
def pause_simulation():
    """
    暂停仿真函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 暂停仿真
        project.modeler.pause_solver()
        return {"status": "success", "message": "仿真已成功暂停"}
    except Exception as e:
        return {"status": "error", "message": f"暂停仿真失败: {str(e)}"}


# MCP工具：恢复仿真
@mcp.tool()
def resume_simulation():
    """
    恢复仿真函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 恢复仿真
        project.modeler.resume_solver()
        return {"status": "success", "message": "仿真已成功恢复"}
    except Exception as e:
        return {"status": "error", "message": f"恢复仿真失败: {str(e)}"}


# MCP工具：停止仿真
@mcp.tool()
def stop_simulation():
    """
    停止仿真函数
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    try:
        # 停止仿真
        project.modeler.abort_solver()
        return {"status": "success", "message": "仿真已成功停止"}
    except Exception as e:
        return {"status": "error", "message": f"停止仿真失败: {str(e)}"}


# ==============================
# 特殊功能函数
# ==============================

# MCP工具：创建喇叭段
@mcp.tool()
def create_horn_segment(segment_id: int, bottom_radius: float, top_radius: float, z_min: float, z_max: float):
    """
    创建喇叭段（外圆台+内圆台+布尔差集）
    Args:
        segment_id (int): 段ID
        bottom_radius (float): 底部半径
        top_radius (float): 顶部半径
        z_min (float): Z轴最小值
        z_max (float): Z轴最大值
    Returns:
        dict: 操作结果
    """
    # 第n段喇叭外圆台
    define_cone(
        name=str(segment_id), component="component1", material="PEC",
        bottom_radius=f"{bottom_radius}+d", top_radius=f"{top_radius}+d", axis="z",
        z_min=z_min, z_max=z_max
    )
    # 第n段喇叭内圆台
    define_cone(
        name=f"solid{segment_id}", component="component1", material="PEC",
        bottom_radius=bottom_radius, top_radius=top_radius, axis="z",
        z_min=z_min, z_max=z_max
    )
    # 进行布尔差集运算
    boolean_subtract(f"component1:{segment_id}", f"component1:solid{segment_id}")

    return {"status": "success", "message": f"Horn segment {segment_id} created successfully"}


# ==============================
# 材料定义函数
# ==============================

def read_mtd_file(file_path):
    """
    读取.mtd文件内容
    Args:
        file_path (str): .mtd文件路径
    Returns:
        str: 文件内容
    """
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return None


def parse_mtd_definition(mtd_content):
    """
    解析.mtd文件中的[Definition]部分
    Args:
        mtd_content (str): .mtd文件内容
    Returns:
        list: 解析后的命令列表
    """
    commands = []

    # 查找[Definition]部分
    lines = mtd_content.split('\n')
    in_definition = False

    for line in lines:
        line = line.strip()
        if line == '[Definition]':
            in_definition = True
            continue
        elif line.startswith('[') and line.endswith(']'):
            # 遇到其他部分，结束解析
            break

        if in_definition and line:
            commands.append(line)

    return commands


def generate_material_vba(name, definition_commands):
    """
    从解析后的命令生成材料定义VBA脚本
    Args:
        name (str): 材料名称
        definition_commands (list): 解析后的命令列表
    Returns:
        str: 生成的VBA脚本
    """
    vba_lines = [
        "With Material",
        "    .Reset",
        f"    .Name \"{name}\"",
        "    .Folder \"\""
    ]

    # 添加解析后的命令
    has_create = False
    for command in definition_commands:
        vba_lines.append(f"    {command}")
        if command.strip() == ".Create":
            has_create = True

    # 如果没有包含.Create命令，则添加
    if not has_create:
        vba_lines.append("    .Create")
    vba_lines.append("End With")

    return '\n'.join(vba_lines)


# MCP工具：从.mtd文件定义材料
@mcp.tool()
def define_material_from_mtd(material_name: str):
    """
    材料不能直接使用，用此工具从.mtd文件定义材料，使用除了真空、PEC材料之前都应该先定义这些材料
    Args:
        material_name (str): 材料名称，函数会自动查找对应的.mtd文件
    Returns:
        dict: 操作结果
    """
    project_data = get_project_object()
    if not project_data:
        return {"status": "error", "message": "当前没有活动的项目"}

    project = project_data['project']

    # 材料库路径：使用指定的材料库目录
    material_library_path = r"C:/Users/z1376/Documents/cst_init/cst_init/Materials"

    # 自动构建.mtd文件路径
    file_path = os.path.join(material_library_path, f"{material_name}.mtd")

    # 读取.mtd文件
    mtd_content = read_mtd_file(file_path)
    if not mtd_content:
        return {"status": "error", "message": f"无法读取文件: {file_path}"}

    # 解析[Definition]部分
    definition_commands = parse_mtd_definition(mtd_content)
    if not definition_commands:
        return {"status": "error", "message": f"文件中没有找到[Definition]部分: {file_path}"}

    # 生成VBA脚本
    vba_script = generate_material_vba(material_name, definition_commands)

    try:
        # 执行VBA脚本
        project.modeler.add_to_history(f"Define Material: {material_name}", vba_script)
        return {"status": "success", "message": f"材料 {material_name} 已从文件 {file_path} 成功定义"}
    except Exception as e:
        return {"status": "error", "message": f"定义材料失败: {str(e)}"}


# 主函数
if __name__ == "__main__":
    mcp.run(transport='stdio')
