
bl_info = {
    'name': 'WarCraft 3 .mdx importer',
    'author': 'Torenjk, Pavel_Blend, Nekuromu',
    'version': (1, 1, 1),
    'blender': (4, 0, 0),
    'category': 'Import-Export',
    'location': 'File > Import',
    'description': 'Import *.mdx files (3d models of WarCraft 3)',
    'wiki_url': 'https://github.com/Torenjk/blender-mdx-importer',
    'tracker_url': 'https://github.com/Torenjk/blender-mdx-importer/issues'
    }


from .plugin import register, unregister
