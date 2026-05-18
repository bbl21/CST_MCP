"""modeling.py — modeling 工具定义"""
from . import _register_tool_defs


TOOL_DEFS = {
"activate-post-process": {
    "category": "modeling",
    "risk": "write",
    "description": "Activate or deactivate a post-processing operation.",
    "handler": "tool_activate_post_process",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "operation": "envelop", "enable": True},
},

"add-to-history": {
    "category": "modeling",
    "risk": "write",
    "description": "Execute a raw VBA command via add_to_history for operations not covered by other tools.",
    "handler": "tool_add_to_history",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "command": "Solid.Add \"Component1:solid1\", \"Component1:solid2\"", "history_name": "custom boolean add"},
},

"boolean-add": {
    "category": "modeling",
    "risk": "write",
    "description": "Unite two solids (boolean union).",
    "handler": "tool_boolean_add",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape1": "Component1:part1", "shape2": "Component1:part2"},
},

"boolean-insert": {
    "category": "modeling",
    "risk": "write",
    "description": "Insert one solid into another (boolean insert).",
    "handler": "tool_boolean_insert",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape1": "Component1:outer", "shape2": "Component1:insert"},
},

"boolean-intersect": {
    "category": "modeling",
    "risk": "write",
    "description": "Intersect two solids (boolean intersection).",
    "handler": "tool_boolean_intersect",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape1": "Component1:part1", "shape2": "Component1:part2"},
},

"boolean-subtract": {
    "category": "modeling",
    "risk": "write",
    "description": "Subtract one solid from another (boolean difference).",
    "handler": "tool_boolean_subtract",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "target": "Component1:outer", "tool": "Component1:inner"},
},

"change-material": {
    "category": "modeling",
    "risk": "write",
    "description": "Change the material of a geometry entity. Use list-materials to see available names.",
    "handler": "tool_change_material",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape_name": "Component1:my_brick", "material": "Copper (pure)"},
},

"create-component": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a new component in the CST project.",
    "handler": "tool_create_component",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "component_name": "MyComponent"},
},

"create-hollow-sweep": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a hollow loft sweep with outer and inner walls.",
    "handler": "tool_create_hollow_sweep",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "horn", "component": "HornAntenna", "material": "PEC", "x_min1": -10, "x_max1": 10, "y_min1": -10, "y_max1": 10, "z1": 0, "x_min2": -35, "x_max2": 35, "y_min2": -35, "y_max2": 35, "z2": 50, "wall_thickness": 2.0},
},

"create-horn-segment": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a horn segment (outer cone - inner cone).",
    "handler": "tool_create_horn_segment",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "segment_id": 1, "bottom_radius": 8, "top_radius": 25, "z_min": 0, "z_max": 30},
},

"create-loft-sweep": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a loft sweep between two 2D profiles in one step.",
    "handler": "tool_create_loft_sweep",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "horn_shell", "component": "HornAntenna", "material": "PEC", "x_min1": -10, "x_max1": 10, "y_min1": -10, "y_max1": 10, "z1": 0, "x_min2": -35, "x_max2": 35, "y_min2": -35, "y_max2": 35, "z2": 50},
},

"create-mesh-group": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a mesh group and add items.",
    "handler": "tool_create_mesh_group",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "group_name": "fine_mesh", "items": ["solid1", "solid2"]},
},

"define-analytical-curve": {
    "category": "modeling",
    "risk": "write",
    "description": "Define an analytical curve using parametric equations.",
    "handler": "tool_define_analytical_curve",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "exp_curve", "curve": "curve1", "law_x": "C1*exp(R*t)+C2", "law_y": "0", "law_z": "t", "param_start": "0", "param_end": "10"},
},

"define-brick": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a rectangular brick in the CST project.",
    "handler": "tool_define_brick",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "my_brick", "component": "Component1", "material": "PEC", "x_min": -10, "x_max": 10, "y_min": -10, "y_max": 10, "z_min": 0, "z_max": 20},
},

"define-cone": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a cone in the CST project.",
    "handler": "tool_define_cone",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "my_cone", "component": "Component1", "material": "PEC", "bottom_radius": 5, "top_radius": 15, "axis": "z", "z_min": 0, "z_max": 30, "x_center": 0, "y_center": 0},
},

"define-cylinder": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a cylinder in the CST project.",
    "handler": "tool_define_cylinder",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "my_cylinder", "component": "Component1", "material": "PEC", "outer_radius": 5, "inner_radius": 0, "axis": "z", "z_min": 0, "z_max": 20, "x_center": 0, "y_center": 0},
},

"define-extrude-curve": {
    "category": "modeling",
    "risk": "write",
    "description": "Extrude a curve profile into a solid.",
    "handler": "tool_define_extrude_curve",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "extruded_part", "component": "Component1", "material": "PEC", "curve": "curve1:my_polygon", "thickness": 5},
},

"define-loft": {
    "category": "modeling",
    "risk": "write",
    "description": "Execute a loft between pre-picked faces.",
    "handler": "tool_define_loft",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "loft_result", "component": "Component1", "material": "PEC", "tangency": 0, "minimize_twist": True},
},

"define-material-from-mtd": {
    "category": "modeling",
    "risk": "write",
    "description": "Define a CST material from .mtd file by material name. Material must exist in references/Materials/. Use list-materials to see available names.",
    "handler": "tool_define_material_from_mtd",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "material_name": "Copper (pure)"},
},

"define-polygon-3d": {
    "category": "modeling",
    "risk": "write",
    "description": "Define a 3D polygon curve from a list of points.",
    "handler": "tool_define_polygon_3d",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "my_polygon", "curve": "curve1", "points": [["-10", "0", "0"], ["10", "0", "0"], ["10", "0", "10"], ["-10", "0", "10"], ["-10", "0", "0"]]},
},

"define-rectangle": {
    "category": "modeling",
    "risk": "write",
    "description": "Create a 2D rectangle on a curve in the CST project.",
    "handler": "tool_define_rectangle",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "name": "my_rect", "curve": "curve1", "x_min": -10, "x_max": 10, "y_min": -5, "y_max": 5},
},

"define-units": {
    "category": "modeling",
    "risk": "write",
    "description": "Set the CST project unit system.",
    "handler": "tool_define_units",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "length": "mm", "frequency": "GHz"},
},

"delete-entity": {
    "category": "modeling",
    "risk": "write",
    "description": "Delete a geometry entity from the CST project.",
    "handler": "tool_delete_entity",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "component": "Component1", "name": "temp_shape"},
},

"delete-monitor": {
    "category": "modeling",
    "risk": "write",
    "description": "Delete a monitor by name.",
    "handler": "tool_delete_monitor",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "monitor_name": "farfield (f=10)"},
},

"delete-probe": {
    "category": "modeling",
    "risk": "write",
    "description": "Delete a probe by its ID.",
    "handler": "tool_delete_probe",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "probe_id": "1"},
},

"export-e-field": {
    "category": "modeling",
    "risk": "filesystem-write",
    "description": "Export E-field data at a given frequency to ASCII.",
    "handler": "tool_export_e_field",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "frequency": "10", "file_path": "C:\\path\\to\\run\\exports"},
},

"export-surface-current": {
    "category": "modeling",
    "risk": "filesystem-write",
    "description": "Export surface current data at a given frequency to ASCII.",
    "handler": "tool_export_surface_current",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "frequency": "10", "file_path": "C:\\path\\to\\run\\exports"},
},

"export-voltage": {
    "category": "modeling",
    "risk": "filesystem-write",
    "description": "Export voltage monitor data to ASCII.",
    "handler": "tool_export_voltage",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "voltage_index": "0", "file_path": "C:\\path\\to\\run\\exports"},
},

"list-entities": {
    "category": "modeling",
    "risk": "read",
    "description": "List geometry entities from the verified CST working project.",
    "handler": "tool_list_entities",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "component": ""},
},

"list-materials": {
    "category": "modeling",
    "risk": "read",
    "description": "List available CST material names from the Materials library.",
    "handler": "tool_list_materials",
    "direct_flags": True,
    "args_template": {},
},

"pick-face": {
    "category": "modeling",
    "risk": "write",
    "description": "Select a face by ID for loft operations (zero-thickness entities only).",
    "handler": "tool_pick_face",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "component": "Component1", "name": "profile_wall", "face_id": "1"},
},

"rename-entity": {
    "category": "modeling",
    "risk": "write",
    "description": "Rename a geometry entity.",
    "handler": "tool_rename_entity",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "old_name": "Component1:old_name", "new_name": "Component1:new_name"},
},

"set-background-with-space": {
    "category": "modeling",
    "risk": "write",
    "description": "Set background space distances.",
    "handler": "tool_set_background_with_space",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"set-efield-monitor": {
    "category": "modeling",
    "risk": "write",
    "description": "Set an E-field monitor over a frequency range.",
    "handler": "tool_set_efield_monitor",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "start_freq": 2.0, "end_freq": 18.0, "step": 1},
},

"set-entity-color": {
    "category": "modeling",
    "risk": "write",
    "description": "Set the display color of a geometry entity.",
    "handler": "tool_set_entity_color",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape_name": "Component1:my_brick", "r": 255, "g": 0, "b": 0},
},

"set-farfield-monitor": {
    "category": "modeling",
    "risk": "write",
    "description": "Set a farfield monitor over a frequency range.",
    "handler": "tool_set_farfield_monitor",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "start_freq": 2.0, "end_freq": 18.0, "step": 1},
},

"set-farfield-plot-cuts": {
    "category": "modeling",
    "risk": "write",
    "description": "Set farfield plot cut angles.",
    "handler": "tool_set_farfield_plot_cuts",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"set-field-monitor": {
    "category": "modeling",
    "risk": "write",
    "description": "Set a field monitor (e.g. H-field) over a frequency range.",
    "handler": "tool_set_field_monitor",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "field_type": "H", "start_frequency": "2", "end_frequency": "18", "num_samples": "10"},
},

"set-probe": {
    "category": "modeling",
    "risk": "write",
    "description": "Set a field probe at a specified position.",
    "handler": "tool_set_probe",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "field_type": "E", "x_pos": "0", "y_pos": "0", "z_pos": "5"},
},

"show-bounding-box": {
    "category": "modeling",
    "risk": "write",
    "description": "Toggle bounding box display.",
    "handler": "tool_show_bounding_box",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"transform-curve": {
    "category": "modeling",
    "risk": "write",
    "description": "Mirror a curve.",
    "handler": "tool_transform_curve",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "curve_name": "curve1:my_curve", "center_x": "0", "center_y": "0", "center_z": "0", "plane_normal_x": "0", "plane_normal_y": "1", "plane_normal_z": "0"},
},

"transform-shape": {
    "category": "modeling",
    "risk": "write",
    "description": "Mirror or rotate a geometry shape.",
    "handler": "tool_transform_shape",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "shape_name": "Component1:my_shape", "transform_type": "mirror", "center_x": "0", "center_y": "0", "center_z": "0", "plane_normal_x": "0", "plane_normal_y": "1", "plane_normal_z": "0"},
},
}


# --- Handlers ---

from ..core import modeling as _md
from ..core.utils import project_path_from_args


def tool_define_material_from_mtd(args: dict) -> dict:
    return _md.define_material_from_mtd(
        project_path=project_path_from_args(args),
        material_name=str(args.get("material_name", "")),
    )


def tool_define_brick(args: dict) -> dict: return _md.define_brick(**args)
def tool_define_cylinder(args: dict) -> dict: return _md.define_cylinder(**args)
def tool_define_cone(args: dict) -> dict: return _md.define_cone(**args)
def tool_define_rectangle(args: dict) -> dict: return _md.define_rectangle(**args)
def tool_boolean_subtract(args: dict) -> dict: return _md.boolean_subtract(**args)
def tool_boolean_add(args: dict) -> dict: return _md.boolean_add(**args)
def tool_boolean_intersect(args: dict) -> dict: return _md.boolean_intersect(**args)
def tool_boolean_insert(args: dict) -> dict: return _md.boolean_insert(**args)
def tool_delete_entity(args: dict) -> dict: return _md.delete_entity(**args)
def tool_create_component(args: dict) -> dict: return _md.create_component(**args)
def tool_change_material(args: dict) -> dict: return _md.change_material(**args)
def tool_rename_entity(args: dict) -> dict: return _md.rename_entity(**args)
def tool_set_entity_color(args: dict) -> dict: return _md.set_entity_color(**args)
def tool_define_units(args: dict) -> dict: return _md.define_units(**args)
def tool_set_farfield_monitor(args: dict) -> dict: return _md.set_farfield_monitor(**args)
def tool_set_efield_monitor(args: dict) -> dict: return _md.set_efield_monitor(**args)
def tool_set_field_monitor(args: dict) -> dict: return _md.set_field_monitor(**args)
def tool_set_probe(args: dict) -> dict: return _md.set_probe(**args)
def tool_delete_probe(args: dict) -> dict: return _md.delete_probe_by_id(**args)
def tool_delete_monitor(args: dict) -> dict: return _md.delete_monitor(**args)
def tool_set_background_with_space(args: dict) -> dict: return _md.set_background_with_space(**args)
def tool_set_farfield_plot_cuts(args: dict) -> dict: return _md.set_farfield_plot_cuts(**args)
def tool_show_bounding_box(args: dict) -> dict: return _md.show_bounding_box(**args)
def tool_activate_post_process(args: dict) -> dict: return _md.activate_post_process_operation(**args)
def tool_create_mesh_group(args: dict) -> dict: return _md.create_mesh_group(**args)
def tool_define_polygon_3d(args: dict) -> dict: return _md.define_polygon_3d(**args)
def tool_define_analytical_curve(args: dict) -> dict: return _md.define_analytical_curve(**args)
def tool_define_extrude_curve(args: dict) -> dict: return _md.define_extrude_curve(**args)
def tool_transform_shape(args: dict) -> dict: return _md.transform_shape(**args)
def tool_transform_curve(args: dict) -> dict: return _md.transform_curve(**args)
def tool_create_horn_segment(args: dict) -> dict: return _md.create_horn_segment(**args)
def tool_create_loft_sweep(args: dict) -> dict: return _md.create_loft_sweep(**args)
def tool_create_hollow_sweep(args: dict) -> dict: return _md.create_hollow_sweep(**args)
def tool_add_to_history(args: dict) -> dict: return _md.add_to_history(**args)
def tool_pick_face(args: dict) -> dict: return _md.pick_face(**args)
def tool_define_loft(args: dict) -> dict: return _md.define_loft(**args)
def tool_export_e_field(args: dict) -> dict: return _md.export_e_field(**args)
def tool_export_surface_current(args: dict) -> dict: return _md.export_surface_current(**args)
def tool_export_voltage(args: dict) -> dict: return _md.export_voltage(**args)


_register_tool_defs(TOOL_DEFS)
