"""Render the real-model regression artifact for visual review."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent))
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
bpy.ops.wm.open_mainfile(filepath=str(root / 'test_output/nefarian_fx.blend'))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
rig.data.warcraft_3.sequencesListIndex = 4
scene.frame_set(13)
for obj in scene.objects:
    if obj.name in ('Cube', 'Light', 'Camera'):
        obj.hide_render = True
image = bpy.data.images.load(r'C:\Users\Administrator\Downloads\Nefarian\Nefarian\Nefarian\Nefarian2.png')
for material in bpy.data.materials:
    if material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image and node.image.get('warcraft_3_source') == 'Nefarian.blp':
                node.image = image
meshes = [o for o in scene.objects if o.type == 'MESH' and not o.get('warcraft_3_effect') and not o.hide_render]
graph = bpy.context.evaluated_depsgraph_get()
points = [o.matrix_world @ v.co for o in meshes for v in o.evaluated_get(graph).data.vertices]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = (low + high)*0.5
size = max(high-low)
camera_data = bpy.data.cameras.new('FX preview')
camera = bpy.data.objects.new('FX preview', camera_data)
scene.collection.objects.link(camera)
camera.location = center + Vector((1, -2, 0.6)).normalized()*size*2.3
camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'
camera_data.ortho_scale = size*1.25
scene.camera = camera
light_data = bpy.data.lights.new('Preview light', 'AREA')
light_data.energy = 1500
light_data.shape = 'DISK'
light_data.size = size
light = bpy.data.objects.new('Preview light', light_data)
scene.collection.objects.link(light)
light.location = center + Vector((1, -2, 3))*size
light.rotation_euler = (center-light.location).to_track_quat('-Z', 'Y').to_euler()
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.09, 0.09, 0.09, 1)
scene.render.engine = 'BLENDER_EEVEE' if '--eevee' in sys.argv else 'CYCLES'
scene.cycles.samples = 16
scene.render.resolution_x = 768
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = str(root / ('test_output/nefarian_fx_eevee.png' if '--eevee' in sys.argv else 'test_output/nefarian_fx_preview.png'))
bpy.ops.render.render(write_still=True)
print('PREVIEW', scene.render.filepath)
