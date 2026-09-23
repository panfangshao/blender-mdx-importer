"""Integration validation against a user-supplied MDX; file is not distributed."""
import sys
import math
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root.parent))
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')
from io_scene_warcraft_3 import parser, classes

args = sys.argv[sys.argv.index('--')+1:]
props = classes.MDXImportProperties()
props.mdx_file_path = args[0]
props.set_team_color = 'RED'
props.bone_size = 5
props.effects_fps = 5 if '--quick' in args else 20
props.max_particles = 64 if '--quick' in args else 256
props.calculate_frame_time()
rig = parser.load_mdx(props)
assert rig.get('warcraft_3_effects') == 4
effects = [o for o in bpy.data.objects if o.get('warcraft_3_effect')]
assert len(effects) == 4
assert len(rig.data.warcraft_3.sequencesList) == 12
count = len(bpy.data.objects)


def snapshot():
    graph = bpy.context.evaluated_depsgraph_get()
    result = []
    for obj in effects:
        mesh = obj.evaluated_get(graph).data
        assert len(mesh.vertices) == len(obj.data.vertices)//3
        assert all(name in mesh.attributes for name in ('MDXColor', 'MDXAlpha', 'MDXUV'))
        assert all(math.isfinite(v) for vertex in mesh.vertices for v in vertex.co)
        coordinates = tuple(round(v, 5) for vertex in mesh.vertices for v in vertex.co)
        result.append(coordinates)
    return result


rig.data.warcraft_3.sequencesListIndex = 1
bpy.context.scene.frame_set(12)
stand = snapshot()
assert any(abs(v) > 0.001 for values in stand for v in values)
for obj, values in zip(effects, stand):
    if obj.get('warcraft_3_emitter_id') in (40, 41):
        assert all(v == 0 for v in values), 'Inactive spell/ribbon should be hidden'
bpy.context.scene.frame_set(25)
assert snapshot() != stand
bpy.context.scene.frame_set(12)
assert snapshot() == stand
rig.data.warcraft_3.sequencesListIndex = 4
bpy.context.scene.frame_set(12)
attack = snapshot()
assert attack != stand
assert any(abs(v) > 0.001 for obj, values in zip(effects, attack)
           if obj.get('warcraft_3_emitter_id') == 41 for v in values)
rig.data.warcraft_3.sequencesListIndex = 7  # Stand Victory enables Spell_Fire.
bpy.context.scene.frame_set(12)
assert any(abs(v) > 0.001 for obj, values in zip(effects, snapshot())
           if obj.get('warcraft_3_emitter_id') == 40 for v in values)
rig.data.warcraft_3.sequencesListIndex = 0
assert all(all(v == 0 for v in values) for values in snapshot())
rig.data.warcraft_3.sequencesListIndex = 1
bpy.context.scene.frame_set(12)
assert snapshot() == stand
assert len(bpy.data.objects) == count
print('FX WARNINGS:', rig.get('warcraft_3_warnings', 'none'))
out = root / 'test_output'
out.mkdir(exist_ok=True)
path = out / ('nefarian_fx_quick.blend' if '--quick' in args else 'nefarian_fx.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(path))
name = rig.name
bpy.ops.wm.open_mainfile(filepath=str(path))
rig = bpy.data.objects[name]
effects = [o for o in bpy.data.objects if o.get('warcraft_3_effect')]
rig.data.warcraft_3.sequencesListIndex = 4
rig.data.warcraft_3.sequencesListIndex = 1
bpy.context.scene.frame_set(12)
assert snapshot() == stand
print('PASS: four real emitters, evaluated mesh attributes, seek/backwards, clip switch,',
      'unanimated hidden, no object deletion, save/reopen:', path)
