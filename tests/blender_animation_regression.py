"""Run with blender --background --factory-startup --python this_file."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import io_scene_warcraft_3 as addon
from io_scene_warcraft_3 import classes, importer, utils

addon.register()


def track(values):
    return SimpleNamespace(tracks_count=len(values), times=[100, 600, 1100][:len(values)],
                           values=values, interpolation_type=1)


def import_fixture(distance):
    model = classes.WarCraft3Model()
    model.name = 'Regression'
    model.pivot_points = [(0, 0, 0), (0, 2, 0), (0, 4, 0)]
    # Deliberately unordered IDs, root ID zero, duplicate and escaped names.
    for node_id, parent in [(2, 0), (0, None), (1, 2)]:
        bone = classes.WarCraft3Bone()
        bone.node = classes.WarCraft3Node()
        bone.node.id, bone.node.parent = node_id, parent
        bone.node.name = 'Node"\\'
        if node_id == 0:
            bone.node.translations = track([(0, 0, 0), (distance, 0, 0), (0, 0, 0)])
        model.nodes.append(bone)
    model.sequences = [SimpleNamespace(name='Stand', interval_start=100, interval_end=2100),
                       SimpleNamespace(name='Walk', interval_start=3000, interval_end=4000)]
    mesh = bpy.data.objects.new('Regression mesh', bpy.data.meshes.new('Regression mesh'))
    bpy.context.collection.objects.link(mesh)
    mesh.vertex_groups.new(name='2')
    geo = classes.WarCraft3GeosetAnimation()
    geo.geoset_id = 0
    geo.animation_color = track([(1, 0, 0), (0, 1, 0), (0, 0, 1)])
    geo.animation_alpha = track([1, 0.5, 1])
    model.geoset_animations = [geo]
    original = importer.create_mesh_objects
    importer.create_mesh_objects = lambda *args: [mesh]
    try:
        props = SimpleNamespace(set_team_color='RED', bone_size=1, global_scale=1, frame_time=100)
        rig = importer.load_warcraft_3_model(model, props)
    finally:
        importer.create_mesh_objects = original
    root = rig.pose.bones[model.nodes[1].node.blender_bone_name]
    assert rig.data.bones[model.nodes[0].node.blender_bone_name].parent == root.bone
    assert rig.data.bones[model.nodes[2].node.blender_bone_name].parent.name == model.nodes[0].node.blender_bone_name
    assert bpy.context.object == rig and rig.select_get()
    assert rig.animation_data.action == rig.data.warcraft_3.sequencesList[1].action
    assert rig.animation_data.action_slot is not None
    assert (bpy.context.scene.frame_start, bpy.context.scene.frame_end) == (0, 20)
    bpy.context.scene.frame_set(5)
    assert abs(root.location.x - distance) < 0.0001, root.location[:]
    assert abs(mesh.color[1] - 1) < 0.0001
    return rig, mesh, root.name


rig1, mesh1, root1 = import_fixture(10)
action1 = rig1.animation_data.action
rig2, mesh2, root2 = import_fixture(30)
assert rig2.animation_data.action != action1
# Renames must not break action or mesh bindings.
rig2.animation_data.action.name = 'Renamed action'
mesh2.name = 'Renamed mesh'
bpy.context.view_layer.objects.active = mesh1
bpy.context.scene.use_preview_range = True
rig2.data.warcraft_3.sequencesListIndex = 2
assert rig1.animation_data.action == action1
assert rig2.pose.bones[root2].location.length == 0
assert bpy.context.scene.frame_current == 0
assert bpy.context.scene.frame_preview_end == 10
rig2.data.warcraft_3.sequencesListIndex = 1
bpy.context.scene.frame_set(5)
assert abs(rig2.pose.bones[root2].location.x - 30) < 0.0001
assert abs(mesh2.color[1] - 1) < 0.0001
rig2.data.warcraft_3.sequencesListIndex = 999
rig2.data.warcraft_3.sequencesListIndex = -1
rig2.data.warcraft_3.sequencesListIndex = 1
# Actual curves all resolve, including duplicate names and quotes/backslashes.
action = rig2.animation_data.action
bag = action.layers[0].strips[0].channelbag(rig2.animation_data.action_slot)
assert len(bag.fcurves) == 27
for curve in bag.fcurves:
    rig2.path_resolve(curve.data_path)

rig_name, mesh_name = rig2.name, mesh2.name
with tempfile.TemporaryDirectory() as directory:
    path = str(Path(directory) / 'regression.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    rig = bpy.data.objects[rig_name]
    assert len(rig.data.warcraft_3.sequencesList) == 3
    rig.data.warcraft_3.sequencesListIndex = 2
    rig.data.warcraft_3.sequencesListIndex = 1
    bpy.context.scene.frame_set(5)
    assert abs(rig.pose.bones[root2].location.x - 30) < 0.0001
    assert rig.data.warcraft_3.sequencesList[1].bindings[0].object == bpy.data.objects[mesh_name]

print('PASS: Blender', bpy.app.version_string,
      'import, ID hierarchy, escaped names, action slots, duplicate imports, renamed bindings,',
      'owner context, frame/preview ranges, pose evaluation, invalid indices, save/reopen')
