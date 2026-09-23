
import bpy
from . import utils


class WarCraft3SequenceBinding(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    target: bpy.props.EnumProperty(items=[('OBJECT', 'Object', ''), ('KEY', 'Shape Keys', '')])


class WarCraft3ArmatureSequenceList(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    action: bpy.props.PointerProperty(type=bpy.types.Action)
    bindings: bpy.props.CollectionProperty(type=WarCraft3SequenceBinding)


class WarCraft3ArmatureProperties(bpy.types.PropertyGroup):
    bpy_type = bpy.types.Armature
    sequencesList: bpy.props.CollectionProperty(type=WarCraft3ArmatureSequenceList)
    sequencesListIndex: bpy.props.IntProperty(update=utils.set_animation)


class WarCraft3BoneProperties(bpy.types.PropertyGroup):
    bpy_type = bpy.types.Bone
    nodeType: bpy.props.EnumProperty(
        items=[
            ('NONE', 'None', ''),
            ('BONE', 'Bone', ''),
            ('HELPER', 'Helper', ''),
            ('PARTICLE', 'Particle Emitter 2', ''),
            ('RIBBON', 'Ribbon Emitter', ''),
            ('ATTACHMENT', 'Attachment', ''),
            ('EVENT', 'Event', ''),
            ('COLLISION_SHAPE', 'Collision Shape', '')
            ],
        name='Node Type',
        update=utils.set_bone_node_type,
        default='NONE'
        )
