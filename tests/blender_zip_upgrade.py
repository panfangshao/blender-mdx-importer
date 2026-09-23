"""Run in an isolated Blender user scripts directory."""
import sys
from pathlib import Path
import bpy

old, new = sys.argv[sys.argv.index('--')+1:]
bpy.ops.preferences.addon_install(filepath=old, overwrite=True)
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
import io_scene_warcraft_3 as addon
assert addon.bl_info['version'] == (1, 1, 2)
assert 'importEffects' not in bpy.ops.warcraft_3.import_mdx.get_rna_type().properties
bpy.ops.preferences.addon_disable(module='io_scene_warcraft_3')
bpy.ops.preferences.addon_install(filepath=new, overwrite=True)
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
assert addon.bl_info['version'] == (1, 2, 1)
assert 'importEffects' in bpy.ops.warcraft_3.import_mdx.get_rna_type().properties
assert 'create_effects' in addon.importer.load_warcraft_3_model.__code__.co_names
assert bpy.types.TOPBAR_MT_file_import.draw._draw_funcs.count(addon.plugin.menu_import_mdx) == 1
print('PASS: live ZIP upgrade 1.1.2 -> 1.2.1 refreshes cached importer and registered UI')
