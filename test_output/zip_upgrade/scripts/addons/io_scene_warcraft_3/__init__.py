
bl_info = {
    'name': 'WarCraft 3 .mdx importer',
    'author': 'Torenjk, Pavel_Blend, Nekuromu',
    'version': (1, 2, 1),
    'blender': (4, 0, 0),
    'category': 'Import-Export',
    'location': 'File > Import',
    'description': 'Import *.mdx files (3d models of WarCraft 3)',
    'wiki_url': 'https://github.com/Torenjk/blender-mdx-importer',
    'tracker_url': 'https://github.com/Torenjk/blender-mdx-importer/issues'
    }


import importlib
import sys


# Blender reloads the package entry point on ZIP updates, but does not reload
# its imported modules. Without this, the displayed version can be new while
# the registered operator and parser still run the previous implementation.
_old_plugin = sys.modules.get(__name__ + '.plugin')
if _old_plugin is not None:
    if getattr(_old_plugin.types.WarCraft3ArmatureProperties, 'is_registered', False):
        _old_plugin.unregister()
    for _module_name in (
        'constants', 'binary', 'classes', 'effects_data', 'animation', 'textures',
        'utils', 'types', 'preferences', 'ui', 'effects', 'importer', 'parser',
        'operators', 'plugin',
    ):
        _module = sys.modules.get(__name__ + '.' + _module_name)
        if _module is not None:
            importlib.reload(_module)

from .plugin import register, unregister
