"""Portable binary integration and simulator checks, without user assets."""
import sys
import importlib.util
import tempfile
from pathlib import Path
from types import SimpleNamespace
import bpy
from mathutils import Matrix

test_dir = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('smoke', test_dir / 'blender_mdx_smoke.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
from io_scene_warcraft_3 import effects, effects_data, parser, binary, classes

pack, chunk = smoke.pack, smoke.chunk


def node(name, index):
    return pack('I', 96) + name.encode().ljust(80, b'\0') + pack('III', index, 0, 0)


particle = node('ParticleTest', 1)
particle += pack('8f', 20, 0.5, 30, 9.8, 0.5, 10, 2, 2)
particle += pack('4I', 1, 2, 2, 2)  # Additive, atlas, both head and tail.
particle += pack('2f', 0.1, 0.5) + pack('9f', 1, 0, 0, 0, 1, 0, 0, 0, 1)
particle += pack('3B', 255, 200, 0) + pack('3f', 1, 2, 0)
particle += pack('12I', *([0, 4, 1]*4)) + pack('iIiI', 0, 0, 0, 0)
particle = pack('I', len(particle)+4) + particle
ribbon = node('RibbonTest', 2) + pack('7f', 2, 2, 0.5, 1, 1, 1, 0.3)
ribbon += pack('4Iif', 0, 20, 1, 1, 0, 0)
ribbon = pack('I', len(ribbon)+4) + ribbon
data = smoke.data + chunk('PRE2', particle) + chunk('RIBB', ribbon) + chunk('PIVT', pack('6f', 0, 0, 1, 0, 0, 2))
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'effects.mdx'
    path.write_bytes(data)
    assert bpy.ops.warcraft_3.import_mdx(filepath=str(path), effectsFPS=10, globalScale=1) == {'FINISHED'}
    rig = bpy.context.object
    assert rig['warcraft_3_effects'] == 2
    effect_objects = [o for o in bpy.data.objects if o.parent == rig and o.get('warcraft_3_effect')]
    bpy.context.scene.frame_set(15)
    for obj in effect_objects:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
        assert max(v.co.length for v in evaluated.vertices) > 1
        assert max(v.value for v in evaluated.attributes['MDXAlpha'].data) > 0
        assert obj.data.shape_keys.animation_data.action_slot is not None
        if obj.get('warcraft_3_effect') == 'particle':
            assert obj.data.materials[0].surface_render_method == 'BLENDED'
    assert bpy.ops.warcraft_3.import_mdx(filepath=str(path), importEffects=False) == {'FINISHED'}
    assert not bpy.context.object.get('warcraft_3_effects')

emitter = effects_data.read_emitters(particle, binary.Reader, parser.parse_node, 'particle')[0]
assert emitter.head_tail == 2 and emitter.node.parent == 0
sequence = SimpleNamespace(interval_start=100, interval_end=1100)
sim = effects.Particles(emitter, sequence, [], 32)
first = sim.step(0, 0.1, Matrix.Identity(4))
assert len(first) == 4  # Two head planes and two tail planes.
again = effects.Particles(emitter, sequence, [], 32).step(0, 0.1, Matrix.Identity(4))
assert first == again
emitter.squirt = 1
emitter.tracks['emission_rate'] = dict(times=[0, 500], values=[(3,), (2,)],
                                      incoming=[], outgoing=[], interpolation=0, global_id=0)
sim = effects.Particles(emitter, sequence, [1000], 32)
assert len(sim.step(0, 0.1, Matrix.Identity(4))) == 12
assert len(sim.step(0.6, 0.6, Matrix.Identity(4))) == 8
assert len(sim.step(1.1, 0.5, Matrix.Identity(4))) == 12
try:
    effects_data.read_emitters(pack('I', 99999) + particle[4:], binary.Reader, parser.parse_node, 'particle')
except ValueError:
    pass
else:
    raise AssertionError('Corrupt emitter was accepted')
print('PASS: synthetic PRE2/RIBB binary import, both heads/tails, attributes, FX disabled,',
      'determinism, global squirt loops, malformed record rejection')
