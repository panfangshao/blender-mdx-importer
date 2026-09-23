"""Run with BLENDER_USER_SCRIPTS pointing at an isolated test directory."""
import sys
from pathlib import Path
import bpy
import addon_utils

archive = Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.preferences.addon_install(filepath=str(archive), overwrite=True)
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
import io_scene_warcraft_3 as addon
from io_scene_warcraft_3 import plugin, effects
assert addon.bl_info['version'] == (1, 2, 1)
assert 'zip_install' in addon.__file__, addon.__file__
assert addon_utils.check('io_scene_warcraft_3') == (True, True)
assert plugin.menu_import_mdx in bpy.types.TOPBAR_MT_file_import.draw._draw_funcs
assert bpy.ops.warcraft_3.import_mdx.get_rna_type().properties['importEffects'].default
for _ in range(2):
    bpy.ops.preferences.addon_disable(module='io_scene_warcraft_3')
    bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
assert bpy.types.TOPBAR_MT_file_import.draw._draw_funcs.count(plugin.menu_import_mdx) == 1
print('PASS: ZIP install, version 1.2.1, enable, import menu, FX defaults, disable/re-enable:', addon.__file__)
