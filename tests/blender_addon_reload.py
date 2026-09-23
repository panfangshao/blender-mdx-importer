"""The same update path that previously displayed 1.2.0 with a 1.1 operator."""
import sys
import importlib
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
import io_scene_warcraft_3 as addon
from io_scene_warcraft_3 import importer, operators

old_importer = importer.load_warcraft_3_model
old_operator = operators.WarCraft3OperatorImportMDX
for enabled in (False, True):
    if not enabled:
        bpy.ops.preferences.addon_disable(module='io_scene_warcraft_3')
    importlib.reload(addon)
    addon.register()
    assert importer.load_warcraft_3_model is not old_importer
    assert operators.WarCraft3OperatorImportMDX is not old_operator
    assert 'create_effects' in importer.load_warcraft_3_model.__code__.co_names
    assert bpy.ops.warcraft_3.import_mdx.get_rna_type().properties['importEffects'].default
    assert bpy.types.TOPBAR_MT_file_import.draw._draw_funcs.count(addon.plugin.menu_import_mdx) == 1
    old_importer = importer.load_warcraft_3_model
    old_operator = operators.WarCraft3OperatorImportMDX

print('PASS: disabled/enabled package reload refreshes submodules, operator properties, single import menu')
