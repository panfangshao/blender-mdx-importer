
import bpy
from . import operators
from . import preferences
from . import types
from . import ui


def menu_import_mdx(self, context):
    self.layout.operator(operators.WarCraft3OperatorImportMDX.bl_idname, text='WarCraft 3 (.mdx)')


def register_class_safe(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        bpy.utils.unregister_class(cls)
        bpy.utils.register_class(cls)

def register():
    register_class_safe(preferences.WarCraft3Preferences)
    register_class_safe(operators.WarCraft3OperatorImportMDX)
    bpy.types.TOPBAR_MT_file_import.append(menu_import_mdx)
    register_class_safe(operators.WarCraft3OperatorAddSequenceToArmature)
    register_class_safe(operators.WarCraft3OperatorRemoveSequenceToArmature)
    register_class_safe(operators.WarCraft3OperatorUpdateBoneSettings)
    register_class_safe(types.WarCraft3ArmatureSequenceList)
    register_class_safe(types.WarCraft3ArmatureProperties)
    types.WarCraft3ArmatureProperties.bpy_type.warcraft_3 = bpy.props.PointerProperty(type=types.WarCraft3ArmatureProperties)
    register_class_safe(types.WarCraft3BoneProperties)
    types.WarCraft3BoneProperties.bpy_type.warcraft_3 = bpy.props.PointerProperty(type=types.WarCraft3BoneProperties)
    register_class_safe(ui.WarCraft3PanelArmature)
    register_class_safe(ui.WarCraft3PanelBone)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_import_mdx)
    bpy.utils.unregister_class(operators.WarCraft3OperatorImportMDX)
    bpy.utils.unregister_class(ui.WarCraft3PanelBone)
    bpy.utils.unregister_class(ui.WarCraft3PanelArmature)
    if hasattr(types.WarCraft3BoneProperties.bpy_type, 'warcraft_3'):
        del types.WarCraft3BoneProperties.bpy_type.warcraft_3
    bpy.utils.unregister_class(types.WarCraft3BoneProperties)
    if hasattr(types.WarCraft3ArmatureProperties.bpy_type, 'warcraft_3'):
        del types.WarCraft3ArmatureProperties.bpy_type.warcraft_3
    bpy.utils.unregister_class(types.WarCraft3ArmatureProperties)
    bpy.utils.unregister_class(types.WarCraft3ArmatureSequenceList)
    bpy.utils.unregister_class(operators.WarCraft3OperatorUpdateBoneSettings)
    bpy.utils.unregister_class(operators.WarCraft3OperatorRemoveSequenceToArmature)
    bpy.utils.unregister_class(operators.WarCraft3OperatorAddSequenceToArmature)
    bpy.utils.unregister_class(preferences.WarCraft3Preferences)
