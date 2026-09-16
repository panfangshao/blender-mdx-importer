
import bpy
import mathutils
import math
from . import constants
from .animation import create_action_fcurves


def load_warcraft_3_model(model, importProperties):
    bpyObjects = create_mesh_objects(model, importProperties.set_team_color)
    armatureObject = create_armature_object(model, bpyObjects, importProperties.bone_size)

    if hasattr(importProperties, 'global_scale'):
        s = importProperties.global_scale
        armatureObject.scale = (s, s, s)

        for obj in bpyObjects:
            obj.rotation_euler[2] = -math.radians(90.0)
            obj.scale = (s, s, s)
    
    armatureObject.rotation_euler[2] = -math.radians(90.0)

    create_armature_actions(armatureObject, model, importProperties.frame_time)
    create_object_actions(model, bpyObjects, importProperties.frame_time)


def create_mesh_objects(model, setTeamColor):
    preferences = bpy.context.preferences.addons['io_scene_warcraft_3'].preferences
    
    # Safely get string properties
    resourceFolder = getattr(preferences, 'resourceFolder', '')
    alternativeResourceFolder = getattr(preferences, 'alternativeResourceFolder', '')
    textureExc = getattr(preferences, 'textureExtension', '')
    
    # Ensure they are strings (handle potential PropertyDeferred objects)
    resourceFolder = str(resourceFolder) if resourceFolder else ''
    alternativeResourceFolder = str(alternativeResourceFolder) if alternativeResourceFolder else ''
    textureExc = str(textureExc) if textureExc else 'png' # Default fallback

    if not textureExc:
         textureExc = '.png'
    elif textureExc[0] != '.':
        textureExc = '.' + textureExc
    model.normalize_meshes_names()
    bpyImages = []
    for texture in model.textures:
        if texture.replaceable_id == 1:    # Team Color
            imageFile = constants.TEAM_COLOR_IMAGES[setTeamColor]
        elif texture.replaceable_id == 2:    # Team Glow
            imageFile = constants.TEAM_GLOW_IMAGES[setTeamColor]
        else:
            imageFile = texture.image_file_name
        bpyImage = bpy.data.images.new(imageFile.split('\\')[-1].split('.')[0], 0, 0)
        bpyImage.source = 'FILE'
        imageFileExt = imageFile.split('\\')[-1].split('.')[-1]
        if imageFileExt == 'blp':
            bpyImage.filepath = alternativeResourceFolder + imageFile.split('.')[0] + textureExc
        else:
            bpyImage.filepath = resourceFolder + imageFile
        bpyImages.append(bpyImage)
    bpyMaterials = []
    for material in model.materials:
        bpyImagesOfLayer = []
        for layer in material.layers:
            bpyImagesOfLayer.append(bpyImages[layer.texture_id])
        materialName = bpyImagesOfLayer[-1].filepath.split('\\')[-1].split('.')[0]
        bpyMaterial = bpy.data.materials.new(name=materialName)
        bpyMaterial.use_nodes = True
        bsdf = bpyMaterial.node_tree.nodes.get('Principled BSDF')
        if not bsdf:
            bsdf = bpyMaterial.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        
        # Handle alpha properly for Eevee
        if hasattr(bpyMaterial, 'surface_render_method'):
            bpyMaterial.surface_render_method = 'BLENDED'
        else:
            bpyMaterial.blend_method = 'BLEND'
        
        if bpyImagesOfLayer:
            texImage = bpyMaterial.node_tree.nodes.new('ShaderNodeTexImage')
            texImage.image = bpyImagesOfLayer[-1]
            
            objInfo = bpyMaterial.node_tree.nodes.new('ShaderNodeObjectInfo')
            mixRGB = bpyMaterial.node_tree.nodes.new('ShaderNodeMixRGB')
            mixRGB.blend_type = 'MULTIPLY'
            mixRGB.inputs[0].default_value = 1.0
            
            bpyMaterial.node_tree.links.new(objInfo.outputs['Color'], mixRGB.inputs[1])
            bpyMaterial.node_tree.links.new(texImage.outputs['Color'], mixRGB.inputs[2])
            
            bpyMaterial.node_tree.links.new(mixRGB.outputs['Color'], bsdf.inputs['Base Color'])
            bpyMaterial.node_tree.links.new(texImage.outputs['Alpha'], bsdf.inputs['Alpha'])

        bpyMaterials.append(bpyMaterial)
    bpyObjects = []
    for warCraft3Mesh in model.meshes:
        bpyMesh = bpy.data.meshes.new(warCraft3Mesh.name)
        bpyObject = bpy.data.objects.new(warCraft3Mesh.name, bpyMesh)
        bpy.context.collection.objects.link(bpyObject)
        bpyMesh.from_pydata(warCraft3Mesh.vertices, (), warCraft3Mesh.triangles)
        bpyMesh.uv_layers.new()
        uvLayer = bpyMesh.uv_layers.active.data
        for tris in bpyMesh.polygons:
            for loopIndex in range(tris.loop_start, tris.loop_start + tris.loop_total):
                vertexIndex = bpyMesh.loops[loopIndex].vertex_index
                uvLayer[loopIndex].uv = (warCraft3Mesh.uvs[vertexIndex])
        bpyMaterial = bpyMaterials[warCraft3Mesh.material_id]
        bpyMesh.materials.append(bpyMaterial)

        for vertexGroupId in warCraft3Mesh.vertex_groups_ids:
            bpyObject.vertex_groups.new(name=str(vertexGroupId))
        for vertexIndex, vertexGroupIds in enumerate(warCraft3Mesh.vertex_groups):
            for vertexGroupId in vertexGroupIds:
                bpyObject.vertex_groups[str(vertexGroupId)].add([vertexIndex, ], 1.0, 'REPLACE')
        bpyObjects.append(bpyObject)
    return bpyObjects


def create_armature_object(model, bpyObjects, boneSize):
    nodes = model.nodes
    pivotPoints = model.pivot_points
    bpyArmature = bpy.data.armatures.new(model.name + ' Nodes')
    bpyArmature.display_type = 'STICK'
    bpyObject = bpy.data.objects.new(model.name + ' Nodes', bpyArmature)
    bpyObject.show_in_front = True
    bpy.context.collection.objects.link(bpyObject)
    bpy.context.view_layer.objects.active = bpyObject
    bpy.ops.object.mode_set(mode='EDIT')
    nodeTypes = set()
    boneTypes = {}
    for indexNode, node in enumerate(nodes):
        nodePosition = pivotPoints[indexNode]
        boneName = node.node.name
        nodeTypes.add(node.type)
        bone = bpyArmature.edit_bones.new(boneName)
        bone.head = nodePosition
        bone.tail = nodePosition
        bone.tail[1] += boneSize
        boneTypes[boneName] = node.type
    nodeTypes = list(nodeTypes)
    nodeTypes.sort()
    for indexNode, node in enumerate(nodes):
        bone = bpyObject.data.edit_bones[indexNode]
        if node.node.parent:
            parent = bpyObject.data.edit_bones[node.node.parent]
            bone.parent = parent
    for mesh in bpyObjects:
        mesh.modifiers.new(name='Armature', type='ARMATURE')
        mesh.modifiers['Armature'].object = bpyObject
        for vertexGroup in mesh.vertex_groups:
            vertexGroupIndex = int(vertexGroup.name)
            boneName = bpyObject.data.edit_bones[vertexGroupIndex].name
            vertexGroup.name = boneName
    bpy.ops.object.mode_set(mode='POSE')
    
    # Updated for Blender 4.0+ Bone Collections
    for nodeType in nodeTypes:
        collection_name = nodeType + 's'
        bone_collection = bpyObject.data.collections.get(collection_name)
        if not bone_collection:
            bone_collection = bpyObject.data.collections.new(collection_name)
        
        # Map old themes to approximate new usage if possible, or just leave default
        # Bone Collections in 4.0 don't exactly match old Bone Group themes
    
    for bone in bpyObject.pose.bones:
        bone.rotation_mode = 'XYZ'
        # Assign to collection based on type
        node_type = boneTypes[bone.name]
        collection_name = node_type + 's'
        bone_collection = bpyObject.data.collections.get(collection_name)
        if bone_collection:
            bone_collection.assign(bone.bone)

    for bone in bpyObject.data.bones:
        bone.warcraft_3.nodeType = boneTypes[bone.name].upper()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = None
    return bpyObject


def add_sequence_to_armature(sequenceName, armatureObject):
    warcraft3data = armatureObject.data.warcraft_3
    sequence = warcraft3data.sequencesList.add()
    sequence.name = sequenceName


def create_armature_actions(armatureObject, model, frameTime):
    nodes = model.nodes
    sequences = model.sequences
    fcurves = create_action_fcurves('#UNANIMATED', armatureObject)
    add_sequence_to_armature('#UNANIMATED', armatureObject)
    for node in nodes:
        boneName = node.node.name
        dataPath = 'pose.bones["' + boneName + '"]'
        locationFcurveX = fcurves.new(data_path=dataPath + '.location', index=0)
        locationFcurveY = fcurves.new(data_path=dataPath + '.location', index=1)
        locationFcurveZ = fcurves.new(data_path=dataPath + '.location', index=2)
        locationFcurveX.keyframe_points.insert(0.0, 0.0)
        locationFcurveY.keyframe_points.insert(0.0, 0.0)
        locationFcurveZ.keyframe_points.insert(0.0, 0.0)
        rotationFcurveX = fcurves.new(data_path=dataPath + '.rotation_euler', index=0)
        rotationFcurveY = fcurves.new(data_path=dataPath + '.rotation_euler', index=1)
        rotationFcurveZ = fcurves.new(data_path=dataPath + '.rotation_euler', index=2)
        rotationFcurveX.keyframe_points.insert(0.0, 0.0)
        rotationFcurveY.keyframe_points.insert(0.0, 0.0)
        rotationFcurveZ.keyframe_points.insert(0.0, 0.0)
        scaleFcurveX = fcurves.new(data_path=dataPath + '.scale', index=0)
        scaleFcurveY = fcurves.new(data_path=dataPath + '.scale', index=1)
        scaleFcurveZ = fcurves.new(data_path=dataPath + '.scale', index=2)
        scaleFcurveX.keyframe_points.insert(0.0, 1.0)
        scaleFcurveY.keyframe_points.insert(0.0, 1.0)
        scaleFcurveZ.keyframe_points.insert(0.0, 1.0)
    for sequence in sequences:
        intervalStart = sequence.interval_start
        intervalEnd = sequence.interval_end
        fcurves = create_action_fcurves(sequence.name, armatureObject)
        add_sequence_to_armature(sequence.name, armatureObject)
        for node in nodes:
            boneName = node.node.name
            dataPath = 'pose.bones["' + boneName + '"]'
            translations = node.node.translations
            rotations = node.node.rotations
            scalings = node.node.scalings
            if translations:
                locationFcurveX = None
                locationFcurveY = None
                locationFcurveZ = None
                interpolationType = constants.INTERPOLATION_TYPE_NAMES[translations.interpolation_type]
                for index in range(translations.tracks_count):
                    time = translations.times[index]
                    translation = translations.values[index]
                    if intervalStart <= time and time <= intervalEnd:
                        if not locationFcurveX:
                            locationFcurveX = fcurves.new(data_path=dataPath + '.location', index=0)
                        if not locationFcurveY:
                            locationFcurveY = fcurves.new(data_path=dataPath + '.location', index=1)
                        if not locationFcurveZ:
                            locationFcurveZ = fcurves.new(data_path=dataPath + '.location', index=2)
                        realTime = round((time - intervalStart) / frameTime, 0)
                        locationXKeyframe = locationFcurveX.keyframe_points.insert(realTime, translation[0])
                        locationYKeyframe = locationFcurveY.keyframe_points.insert(realTime, translation[1])
                        locationZKeyframe = locationFcurveZ.keyframe_points.insert(realTime, translation[2])
                        locationXKeyframe.interpolation = interpolationType
                        locationYKeyframe.interpolation = interpolationType
                        locationZKeyframe.interpolation = interpolationType
                if not locationFcurveX:
                    locationFcurveX = fcurves.new(data_path=dataPath + '.location', index=0)
                    locationFcurveX.keyframe_points.insert(0.0, 0.0)
                if not locationFcurveY:
                    locationFcurveY = fcurves.new(data_path=dataPath + '.location', index=1)
                    locationFcurveY.keyframe_points.insert(0.0, 0.0)
                if not locationFcurveZ:
                    locationFcurveZ = fcurves.new(data_path=dataPath + '.location', index=2)
                    locationFcurveZ.keyframe_points.insert(0.0, 0.0)
            if rotations:
                rotationFcurveX = None
                rotationFcurveY = None
                rotationFcurveZ = None
                interpolationType = constants.INTERPOLATION_TYPE_NAMES[rotations.interpolation_type]
                for index in range(rotations.tracks_count):
                    time = rotations.times[index]
                    rotation = rotations.values[index]
                    if intervalStart <= time and time <= intervalEnd:
                        if not rotationFcurveX:
                            rotationFcurveX = fcurves.new(data_path=dataPath + '.rotation_euler', index=0)
                        if not rotationFcurveY:
                            rotationFcurveY = fcurves.new(data_path=dataPath + '.rotation_euler', index=1)
                        if not rotationFcurveZ:
                            rotationFcurveZ = fcurves.new(data_path=dataPath + '.rotation_euler', index=2)
                        realTime = round((time - intervalStart) / frameTime, 0)
                        euler = mathutils.Quaternion(mathutils.Vector(rotation)).to_euler('XYZ')
                        rotationXKeyframe = rotationFcurveX.keyframe_points.insert(realTime, euler[0])
                        rotationYKeyframe = rotationFcurveY.keyframe_points.insert(realTime, euler[1])
                        rotationZKeyframe = rotationFcurveZ.keyframe_points.insert(realTime, euler[2])
                        rotationXKeyframe.interpolation = interpolationType
                        rotationYKeyframe.interpolation = interpolationType
                        rotationZKeyframe.interpolation = interpolationType
                if not rotationFcurveX:
                    rotationFcurveX = fcurves.new(data_path=dataPath + '.rotation_euler', index=0)
                    rotationFcurveX.keyframe_points.insert(0.0, 0.0)
                if not rotationFcurveY:
                    rotationFcurveY = fcurves.new(data_path=dataPath + '.rotation_euler', index=1)
                    rotationFcurveY.keyframe_points.insert(0.0, 0.0)
                if not rotationFcurveZ:
                    rotationFcurveZ = fcurves.new(data_path=dataPath + '.rotation_euler', index=2)
                    rotationFcurveZ.keyframe_points.insert(0.0, 0.0)
            if scalings:
                scaleFcurveX = None
                scaleFcurveY = None
                scaleFcurveZ = None
                interpolationType = constants.INTERPOLATION_TYPE_NAMES[scalings.interpolation_type]
                for index in range(scalings.tracks_count):
                    time = scalings.times[index]
                    scale = scalings.values[index]
                    if intervalStart <= time and time <= intervalEnd:
                        if not scaleFcurveX:
                            scaleFcurveX = fcurves.new(data_path=dataPath + '.scale', index=0)
                        if not scaleFcurveY:
                            scaleFcurveY = fcurves.new(data_path=dataPath + '.scale', index=1)
                        if not scaleFcurveZ:
                            scaleFcurveZ = fcurves.new(data_path=dataPath + '.scale', index=2)
                        realTime = round((time - intervalStart) / frameTime, 0)
                        scaleXKeyframe = scaleFcurveX.keyframe_points.insert(realTime, scale[0])
                        scaleYKeyframe = scaleFcurveY.keyframe_points.insert(realTime, scale[1])
                        scaleZKeyframe = scaleFcurveZ.keyframe_points.insert(realTime, scale[2])
                        scaleXKeyframe.interpolation = interpolationType
                        scaleYKeyframe.interpolation = interpolationType
                        scaleZKeyframe.interpolation = interpolationType
                if not scaleFcurveX:
                    scaleFcurveX = fcurves.new(data_path=dataPath + '.scale', index=0)
                    scaleFcurveX.keyframe_points.insert(0.0, 1.0)
                if not scaleFcurveY:
                    scaleFcurveY = fcurves.new(data_path=dataPath + '.scale', index=1)
                    scaleFcurveY.keyframe_points.insert(0.0, 1.0)
                if not scaleFcurveZ:
                    scaleFcurveZ = fcurves.new(data_path=dataPath + '.scale', index=2)
                    scaleFcurveZ.keyframe_points.insert(0.0, 1.0)


def create_object_actions(model, bpyObjects, frameTime):
    geosetAnimations = model.geoset_animations
    sequences = model.sequences
    dataPathColor = 'color'
    for geosetAnimation in geosetAnimations:
        geosetId = geosetAnimation.geoset_id
        fcurves = create_action_fcurves('#UNANIMATED' + ' ' + bpyObjects[geosetId].name, bpyObjects[geosetId])
        colorR = fcurves.new(data_path=dataPathColor, index=0)
        colorG = fcurves.new(data_path=dataPathColor, index=1)
        colorB = fcurves.new(data_path=dataPathColor, index=2)
        colorA = fcurves.new(data_path=dataPathColor, index=3)
        colorR.keyframe_points.insert(0.0, 1.0)
        colorG.keyframe_points.insert(0.0, 1.0)
        colorB.keyframe_points.insert(0.0, 1.0)
        colorA.keyframe_points.insert(0.0, 1.0)
    for sequence in sequences:
        intervalStart = sequence.interval_start
        intervalEnd = sequence.interval_end
        for geosetAnimation in geosetAnimations:
            geosetId = geosetAnimation.geoset_id
            colorAnim = geosetAnimation.animation_color
            alphaAnim = geosetAnimation.animation_alpha
            fcurves = create_action_fcurves(sequence.name + ' ' + bpyObjects[geosetId].name, bpyObjects[geosetId])
            colorR = None
            colorG = None
            colorB = None
            colorA = None
            interpolationType = constants.INTERPOLATION_TYPE_NAMES[colorAnim.interpolation_type]
            for index in range(colorAnim.tracks_count):
                time = colorAnim.times[index]
                color = colorAnim.values[index]
                if intervalStart <= time and time <= intervalEnd or time == 0:
                    if not colorR:
                        colorR = fcurves.new(data_path=dataPathColor, index=0)
                    if not colorG:
                        colorG = fcurves.new(data_path=dataPathColor, index=1)
                    if not colorB:
                        colorB = fcurves.new(data_path=dataPathColor, index=2)
                    if time == 0:
                        realTime = 0.0
                    else:
                        realTime = round((time - intervalStart) / frameTime, 0)
                    colorRKeyframe = colorR.keyframe_points.insert(realTime, color[0])
                    colorGKeyframe = colorG.keyframe_points.insert(realTime, color[1])
                    colorBKeyframe = colorB.keyframe_points.insert(realTime, color[2])
                    colorRKeyframe.interpolation = interpolationType
                    colorGKeyframe.interpolation = interpolationType
                    colorBKeyframe.interpolation = interpolationType
            if not colorR:
                colorR = fcurves.new(data_path=dataPathColor, index=0)
                colorR.keyframe_points.insert(0, 1.0)
            if not colorG:
                colorG = fcurves.new(data_path=dataPathColor, index=1)
                colorG.keyframe_points.insert(0, 1.0)
            if not colorB:
                colorB = fcurves.new(data_path=dataPathColor, index=2)
                colorB.keyframe_points.insert(0, 1.0)
            interpolationType = constants.INTERPOLATION_TYPE_NAMES[alphaAnim.interpolation_type]
            for index in range(alphaAnim.tracks_count):
                time = alphaAnim.times[index]
                alpha = alphaAnim.values[index]
                if intervalStart <= time and time <= intervalEnd or time == 0:
                    if not colorA:
                        colorA = fcurves.new(data_path=dataPathColor, index=3)
                    if time == 0:
                        realTime = 0.0
                    else:
                        realTime = round((time - intervalStart) / frameTime, 0)
                    colorAKeyframe = colorA.keyframe_points.insert(realTime, alpha)
                    colorAKeyframe.interpolation = interpolationType
            if not colorA:
                colorA = fcurves.new(data_path=dataPathColor, index=3)
                colorA.keyframe_points.insert(0, 1.0)
