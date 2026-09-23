"""Action compatibility for Blender 4.0 and newer."""

import bpy


def _channelbag(action, slot, layer, strip):
    """Get/create a channelbag across the Blender 4.4-5.2 API variants."""
    try:
        from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
        return action_ensure_channelbag_for_slot(action, slot)
    except (ImportError, AttributeError):
        try:
            return strip.channelbag(slot, ensure=True)
        except TypeError:
            return strip.channelbag(slot)


def create_action_fcurves(name, obj, sequence=None, target='OBJECT'):
    action = bpy.data.actions.new(name=name)
    if sequence is not None:
        if obj.type == 'ARMATURE' and target == 'OBJECT':
            sequence.action = action
        else:
            binding = sequence.bindings.add()
            binding.object = obj
            binding.action = action
            binding.target = target
    # Sequences are assigned on demand; keep inactive actions when saving.
    action.use_fake_user = True
    if hasattr(action, 'slots'):
        slot = action.slots.new(id_type=target, name=obj.name)
        layer = action.layers.new(name='Animation')
        strip = layer.strips.new(type='KEYFRAME')
        return _channelbag(action, slot, layer, strip).fcurves
    return action.fcurves


def assign_action(obj, action):
    animation_data = obj.animation_data_create()
    animation_data.action = action
    if hasattr(action, 'slots') and len(action.slots):
        # Imported actions contain exactly one slot for their object.
        animation_data.action_slot = action.slots[0]
