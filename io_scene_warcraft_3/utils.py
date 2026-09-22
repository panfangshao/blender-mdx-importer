
import bpy
from . import constants
from .animation import assign_action


ACTION_NAME_UNANIMATED = '#UNANIMATED'


def set_animation(self, context):
    armature_data = context.object.data
    setAnimationName = armature_data.warcraft_3.sequencesList[armature_data.warcraft_3.sequencesListIndex].name
    if len(setAnimationName) and bpy.data.actions.get(setAnimationName, None):
        armatureObject = context.object
        if armatureObject.animation_data == None:
            armatureObject.animation_data_create()
        setAction = bpy.data.actions[setAnimationName]
        assign_action(armatureObject, setAction)
        bpy.context.scene.frame_start = int(setAction.frame_range[0])
        bpy.context.scene.frame_end = int(setAction.frame_range[1])
        for action in bpy.data.actions:
            for object in bpy.context.scene.objects:
                setObjectAnimationName = setAnimationName + ' ' + object.name
                if action.name == setObjectAnimationName:
                    if object.animation_data == None:
                        object.animation_data_create()
                    assign_action(object, action)
    else:
        action = bpy.data.actions.get(ACTION_NAME_UNANIMATED, None)
        if action:
            armatureObject = context.object
            if armatureObject.animation_data == None:
                armatureObject.animation_data_create()
            setAction = bpy.data.actions[ACTION_NAME_UNANIMATED]
            assign_action(armatureObject, setAction)
            bpy.context.scene.frame_start = int(setAction.frame_range[0])
            bpy.context.scene.frame_end = int(setAction.frame_range[1])
            for object in bpy.context.scene.objects:
                objectActionName = ACTION_NAME_UNANIMATED + ' ' + object.name
                if bpy.data.actions.get(objectActionName, None):
                    if object.animation_data == None:
                        object.animation_data_create()
                    assign_action(object, bpy.data.actions[objectActionName])


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
                if nodeType in {'BONE', 'ATTACHMENT', 'COLLISION_SHAPE', 'EVENT', 'HELPER'}:
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
