"""End-to-end import of a generated classic MDX triangle with animation."""
import sys
import struct
import tempfile
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
bpy.ops.preferences.addon_enable(module='io_scene_warcraft_3')


def pack(fmt, *values):
    return struct.pack('<' + fmt, *values)


def chunk(tag, data):
    return tag.encode() + pack('I', len(data)) + data


def array(tag, count, fmt, *values):
    return tag.encode() + pack('I', count) + pack(fmt, *values)


extent = pack('7f', 1, 0, 0, 0, 1, 1, 1)
model = b'Smoke'.ljust(80, b'\0') + bytes(260) + extent + pack('I', 0)
sequence = b'Stand'.ljust(80, b'\0') + pack('IIfIfI', 100, 1100, 0, 0, 0, 0) + extent
translation = b'KGTR' + pack('III', 3, 1, 0xffffffff)
for time, x in [(100, 0), (600, 10), (1100, 0)]:
    translation += pack('I3f', time, x, 0, 0)
node = b'Root'.ljust(80, b'\0') + pack('III', 0, 0xffffffff, 256) + translation
bone = pack('I', len(node) + 4) + node + pack('II', 0xffffffff, 0xffffffff)
layer = pack('6If', 28, 0, 0, 0, 0xffffffff, 0, 1)
material = pack('III', 20 + len(layer), 0, 0) + b'LAYS' + pack('I', 1) + layer
texture = pack('I', 0) + b'missing.png'.ljust(260, b'\0') + pack('I', 0)
geo = array('VRTX', 3, '9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
geo += array('NRMS', 3, '9f', 0, 0, 1, 0, 0, 1, 0, 0, 1)
geo += array('PTYP', 1, 'I', 4) + array('PCNT', 1, 'I', 3)
geo += array('PVTX', 3, '3H', 0, 1, 2) + array('GNDX', 3, '3B', 0, 0, 0)
geo += array('MTGC', 1, 'I', 1) + array('MATS', 1, 'I', 0)
geo += pack('III', 0, 0, 0) + extent + pack('I', 0)
geo += b'UVAS' + pack('I', 1) + array('UVBS', 3, '6f', 0, 0, 1, 0, 0, 1)
data = b'MDLX' + chunk('VERS', pack('I', 800)) + chunk('MODL', model)
data += chunk('SEQS', sequence) + chunk('TEXS', texture) + chunk('MTLS', material)
data += chunk('GEOS', pack('I', len(geo) + 4) + geo)
data += chunk('BONE', bone) + chunk('PIVT', pack('3f', 0, 0, 0))

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'smoke.mdx'
    path.write_bytes(data)
    bpy.context.scene.render.fps = 30
    assert bpy.ops.warcraft_3.import_mdx(filepath=str(path), globalScale=1) == {'FINISHED'}
    rig = bpy.context.object
    assert rig.type == 'ARMATURE'
    assert len(rig.data.warcraft_3.sequencesList) == 2
    bpy.context.scene.frame_set(15)
    assert abs(rig.pose.bones['Root'].location.x - 10) < 0.0001
    mesh = next(obj for obj in bpy.context.scene.objects
                if any(mod.type == 'ARMATURE' and mod.object == rig for mod in obj.modifiers))
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert abs(evaluated.data.vertices[0].co.x - 10) < 0.0001
    assert (bpy.context.scene.frame_start, bpy.context.scene.frame_end) == (0, 30)
print('PASS: MDX binary -> import operator -> mesh/material/rig -> animated vertex, Blender', bpy.app.version_string)
