
import bpy
from . import classes
from . import constants
from . import parser
from . import utils
from bpy_extras import io_utils


class WarCraft3OperatorImportMDX(bpy.types.Operator, io_utils.ImportHelper):
    bl_idname = 'warcraft_3.import_mdx'
    bl_label = 'Import *.mdx'
    bl_description = 'Import *.mdx files (3d models of WarCraft 3)'
    bl_options = {'UNDO'}

    filename_ext = '.mdx'
    filter_glob: bpy.props.StringProperty(default='*.mdx', options={'HIDDEN'})
    filepath: bpy.props.StringProperty(name='File Path', subtype='FILE_PATH', maxlen=1024, default='')
    useCustomFPS: bpy.props.BoolProperty(name='Use Custom FPS', default=False)
    animationFPS: bpy.props.FloatProperty(name='Animation FPS', default=30.0, min=1.0, max=1000.0)
    globalScale: bpy.props.FloatProperty(
        name='Global Scale',
        default=0.03,
        min=0.0001,
        max=1000.0,
        description="Scale the model on import (0.03 is good for Warcraft III models)"
    )
    boneSize: bpy.props.FloatProperty(name='Bone Size', default=5.0, min=0.0001, max=1000.0)
    importEffects: bpy.props.BoolProperty(name='Import Particles and Ribbons', default=True)
    effectsFPS: bpy.props.IntProperty(name='Effects Samples / Second', default=20, min=5, max=60)
    maxParticles: bpy.props.IntProperty(name='Max Particles per Emitter', default=256, min=16, max=2048)
    teamColor: bpy.props.FloatVectorProperty(
        name='Team Color',
        default=constants.TEAM_COLORS['RED'],
        min=0.0,
        max=1.0,
        size=3,
        subtype='COLOR',
        precision=3
        )
    setTeamColor: bpy.props.EnumProperty(
        items=[
            ('RED', 'Red', ''),
            ('DARK_BLUE', 'Dark Blue', ''),
            ('TURQUOISE', 'Turquoise', ''),
            ('VIOLET', 'Violet', ''),
            ('YELLOW', 'Yellow', ''),
            ('ORANGE', 'Orange', ''),
            ('GREEN', 'Green', ''),
            ('PINK', 'Pink', ''),
            ('GREY', 'Grey', ''),
            ('BLUE', 'Blue', ''),
            ('DARK_GREEN', 'Dark Green', ''),
            ('BROWN', 'Brown', ''),
            ('BLACK', 'Black', '')
            ],
        name='Set Team Color',
        update=utils.set_team_color_property,
        default='RED'
        )

    def draw(self, context):
        layout = self.layout
        split = layout.split(factor=0.9)
        subSplit = split.split(factor=0.5)
        subSplit.label(text='Team Color:')
        subSplit.prop(self, 'setTeamColor', text='')
        split.prop(self, 'teamColor', text='')
        layout.prop(self, 'globalScale')
        layout.prop(self, 'boneSize')
        layout.prop(self, 'importEffects')
        if self.importEffects:
            layout.prop(self, 'effectsFPS')
            layout.prop(self, 'maxParticles')
        layout.prop(self, 'useCustomFPS')
        if self.useCustomFPS:
            layout.prop(self, 'animationFPS')

    def execute(self, context):
        importProperties = classes.MDXImportProperties()
        importProperties.mdx_file_path = str(self.filepath)
        importProperties.set_team_color = str(self.setTeamColor)
        importProperties.bone_size = float(self.boneSize)
        importProperties.use_custom_fps = bool(self.useCustomFPS)
        importProperties.fps = float(self.animationFPS)
        importProperties.global_scale = float(self.globalScale)
        importProperties.import_effects = self.importEffects
        importProperties.effects_fps = self.effectsFPS
        importProperties.max_particles = self.maxParticles
        importProperties.calculate_frame_time()
        rig = parser.load_mdx(importProperties)
        if rig and rig.get('warcraft_3_warnings'):
            self.report({'WARNING'}, rig['warcraft_3_warnings'])
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WarCraft3OperatorAddSequenceToArmature(bpy.types.Operator):
    bl_idname = 'warcraft_3.add_sequence_to_armature'
    bl_label = 'WarCraft 3 Add Sequence to Armature'
    bl_description = 'WarCraft 3 Add Sequence to Armature'
    bl_options = {'UNDO'}

    def execute(self, context):
        if context.object and context.object.type == 'ARMATURE':
            warcraft3data = context.object.data.warcraft_3
            sequence = warcraft3data.sequencesList.add()
            sequence.name = '#UNANIMATED'
        return {'FINISHED'}


class WarCraft3OperatorRemoveSequenceToArmature(bpy.types.Operator):
    bl_idname = 'warcraft_3.remove_sequence_to_armature'
    bl_label = 'WarCraft 3 Remove Sequence to Armature'
    bl_description = 'WarCraft 3 Remove Sequence to Armature'
    bl_options = {'UNDO'}

    def execute(self, context):
        if context.object and context.object.type == 'ARMATURE':
            warcraft3data = context.object.data.warcraft_3
            index = warcraft3data.sequencesListIndex
            if 0 <= index < len(warcraft3data.sequencesList):
                warcraft3data.sequencesList.remove(index)
                warcraft3data.sequencesListIndex = max(0, min(index, len(warcraft3data.sequencesList) - 1))
        return {'FINISHED'}


class WarCraft3OperatorUpdateBoneSettings(bpy.types.Operator):
    bl_idname = 'warcraft_3.update_bone_settings'
    bl_label = 'WarCraft 3 Update Bone Settings'
    bl_description = 'WarCraft 3 Update Bone Settings'
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj and obj.type == 'ARMATURE':
            for bone in obj.data.bones:
                nodeType = bone.warcraft_3.nodeType
                collection_name = nodeType.lower() + 's'
                
                bone_collection = obj.data.collections.get(collection_name)
                if not bone_collection:
                    if nodeType in {'BONE', 'ATTACHMENT', 'COLLISION_SHAPE', 'EVENT', 'HELPER', 'PARTICLE', 'RIBBON'}:
                        bone_collection = obj.data.collections.new(collection_name)
                
                if bone_collection:
                    bone_collection.assign(bone)
                    
        return {'FINISHED'}
