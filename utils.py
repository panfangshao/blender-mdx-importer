
import bpy
from . import constants
from .animation import assign_action


ACTION_NAME_UNANIMATED = '#UNANIMATED'


def set_animation(self, context):
    # Resolve the property owner, not the currently selected object.
    armature_data = self.id_data
    index = self.sequencesListIndex
    if not 0 <= index < len(self.sequencesList):
        return
    sequence = self.sequencesList[index]
    action = sequence.action
    if action is None:
        action = bpy.data.actions.get(sequence.name)
    if action is None:
        return
    owners = [obj for obj in context.scene.objects
              if obj.type == 'ARMATURE' and obj.data == armature_data]
    if not owners:
        return
    for obj in owners:
        assign_action(obj, action)
    for binding in sequence.bindings:
        if binding.object and binding.action:
            target = binding.object.data.shape_keys if binding.target == 'KEY' else binding.object
            if target:
                assign_action(target, binding.action)
    if sequence.action is None:
        # Old files have names only; restrict fallback to this rig's meshes.
        for obj in context.scene.objects:
            if any(mod.type == 'ARMATURE' and mod.object in owners
                   for mod in obj.modifiers):
                mesh_action = bpy.data.actions.get(sequence.name + ' ' + obj.name)
                if mesh_action:
                    assign_action(obj, mesh_action)
    import math
    scene = context.scene
    scene.frame_start = math.floor(action.frame_range[0])
    scene.frame_end = max(scene.frame_start + 1, math.ceil(action.frame_range[1]))
    if scene.use_preview_range:
        scene.frame_preview_start = scene.frame_start
        scene.frame_preview_end = scene.frame_end
    scene.frame_set(scene.frame_start)
    if context.screen:
        for area in context.screen.areas:
            area.tag_redraw()


def set_team_color_property(self, context):
    self.teamColor = constants.TEAM_COLORS[self.setTeamColor]


def set_bone_node_type(self, context):
    bone = context.active_bone
    if bone:
        nodeType = bone.warcraft_3.nodeType
        obj = context.object
        if obj and obj.type == 'ARMATURE':
            collection_name = nodeType.lower() + 's'
            bone_collection = obj.data.collections.get(collection_name)
            
            if not bone_collection:
                if nodeType in {'BONE', 'ATTACHMENT', 'COLLISION_SHAPE', 'EVENT', 'HELPER', 'PARTICLE', 'RIBBON'}:
                    bone_collection = obj.data.collections.new(collection_name)
            
            if bone_collection:
                # Remove from other collections first? 
                # For now just assign to the new one, bones can be in multiple.
                # But to emulate old behavior (single group), we might want to unassign from others?
                # Keeping it simple: Just assign.
                if hasattr(bone, "bone"): # PoseBone
                    bone_collection.assign(bone.bone)
                else: # Bone or EditBone
                    bone_collection.assign(bone)
