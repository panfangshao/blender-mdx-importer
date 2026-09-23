"""Bake MDX PRE2/RIBB to native shape keys and geometry attributes.

No playback handlers, temporary objects, external cache files or simulations are
needed after import. Each sequence owns an Action on the effect's Key datablock.
"""
import math
import random
from array import array
import bpy
from mathutils import Vector, Euler
from .animation import create_action_fcurves, assign_action
from .effects_data import parameter
from .textures import effect_image


def attributes_modifier(obj, count):
    """Decode the baked color/UV payload, then remove its loose vertices."""
    tree = bpy.data.node_groups.new(obj.name + ' attributes', 'GeometryNodeTree')
    tree.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    source, output = nodes.new('NodeGroupInput'), nodes.new('NodeGroupOutput')
    index = nodes.new('GeometryNodeInputIndex')
    position = nodes.new('GeometryNodeInputPosition')
    geometry = source.outputs['Geometry']
    samples = []
    for offset in (count, count * 2):
        add = nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        links.new(index.outputs[0], add.inputs[0])
        add.inputs[1].default_value = offset
        sample = nodes.new('GeometryNodeSampleIndex')
        sample.data_type = 'FLOAT_VECTOR'
        sample.domain = 'POINT'
        links.new(source.outputs['Geometry'], sample.inputs['Geometry'])
        links.new(position.outputs[0], sample.inputs['Value'])
        links.new(add.outputs[0], sample.inputs['Index'])
        samples.append(sample.outputs['Value'])
    separate = nodes.new('ShaderNodeSeparateXYZ')
    links.new(samples[1], separate.inputs[0])
    for name, data_type, value in (('MDXColor', 'FLOAT_VECTOR', samples[0]),
                                   ('MDXUV', 'FLOAT_VECTOR', samples[1]),
                                   ('MDXAlpha', 'FLOAT', separate.outputs['Z'])):
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.domain, store.data_type = 'POINT', data_type
        store.inputs['Name'].default_value = name
        links.new(geometry, store.inputs['Geometry'])
        links.new(value, store.inputs['Value'])
        geometry = store.outputs['Geometry']
    compare = nodes.new('ShaderNodeMath')
    compare.operation = 'GREATER_THAN'
    compare.inputs[1].default_value = count - 0.5
    links.new(index.outputs[0], compare.inputs[0])
    delete = nodes.new('GeometryNodeDeleteGeometry')
    delete.domain = 'POINT'
    links.new(geometry, delete.inputs['Geometry'])
    links.new(compare.outputs[0], delete.inputs['Selection'])
    links.new(delete.outputs['Geometry'], output.inputs['Geometry'])
    obj.modifiers.new('MDX effect attributes', 'NODES').node_group = tree


def effect_material(model, emitter):
    if emitter.type == 'particle':
        texture_id = emitter.texture_id
        additive = emitter.filter_mode == 1
        alpha_key = emitter.filter_mode == 4
        if emitter.filter_mode in (2, 3):
            model.import_warnings.append('%s: modulate FX blend approximated with alpha blending.' % emitter.node.name)
    else:
        material = model.materials[emitter.material_id] if 0 <= emitter.material_id < len(model.materials) else None
        layer = material.layers[0] if material and material.layers else None
        texture_id = layer.texture_id if layer else -1
        additive = layer is not None and getattr(layer, 'filter_mode', 0) in (3, 4)
        alpha_key = layer is not None and getattr(layer, 'filter_mode', 0) == 1
    image = effect_image(model, texture_id, emitter.rows, emitter.columns,
                         getattr(emitter, 'replaceable_id', 0))
    material = bpy.data.materials.new(emitter.node.name + ' FX')
    material.use_nodes = True
    if hasattr(material, 'surface_render_method'):
        # EEVEE discards additive transparency in Dithered mode.
        material.surface_render_method = 'BLENDED' if additive else 'DITHERED'
    else:
        material.blend_method = 'BLEND' if additive else 'HASHED'
    material.use_backface_culling = False
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    tex.label = 'Effect sprite / atlas (replace preview here)'
    attrs = {}
    for name in ('MDXUV', 'MDXColor', 'MDXAlpha'):
        node = nodes.new('ShaderNodeAttribute')
        node.attribute_name = name
        attrs[name] = node
    links.new(attrs['MDXUV'].outputs['Vector'], tex.inputs['Vector'])
    color = nodes.new('ShaderNodeMixRGB')
    color.blend_type = 'MULTIPLY'
    color.inputs[0].default_value = 1
    links.new(tex.outputs['Color'], color.inputs[1])
    links.new(attrs['MDXColor'].outputs['Color'], color.inputs[2])
    alpha = nodes.new('ShaderNodeMath')
    alpha.operation = 'MULTIPLY'
    links.new(tex.outputs['Alpha'], alpha.inputs[0])
    links.new(attrs['MDXAlpha'].outputs['Fac'], alpha.inputs[1])
    opacity = alpha.outputs[0]
    if alpha_key:
        threshold = nodes.new('ShaderNodeMath')
        threshold.operation = 'GREATER_THAN'
        threshold.inputs[1].default_value = 0.75
        links.new(opacity, threshold.inputs[0])
        opacity = threshold.outputs[0]
    emission = nodes.new('ShaderNodeEmission')
    links.new(color.outputs['Color'], emission.inputs['Color'])
    transparent = nodes.new('ShaderNodeBsdfTransparent')
    combine = nodes.new('ShaderNodeAddShader' if additive else 'ShaderNodeMixShader')
    if additive:
        links.new(opacity, emission.inputs['Strength'])
        links.new(transparent.outputs[0], combine.inputs[0])
        links.new(emission.outputs[0], combine.inputs[1])
    else:
        links.new(opacity, combine.inputs[0])
        links.new(transparent.outputs[0], combine.inputs[1])
        links.new(emission.outputs[0], combine.inputs[2])
    links.new(combine.outputs[0], out.inputs['Surface'])
    for i, node in enumerate(nodes):
        node.location = ((i % 4) * 240, -(i // 4) * 220)
    return material


class BakedMesh:
    def __init__(self, model, rig, emitter, capacity, collection):
        self.emitter, self.capacity = emitter, capacity
        # Heads use two crossed quads; XYQuad is a single local XY plane.
        if emitter.type == 'particle':
            head_quads = 1 if emitter.node.flags & 0x100000 else 2
            self.quads = (head_quads if emitter.head_tail != 1 else 0) + (2 if emitter.head_tail != 0 else 0)
        else:
            self.quads = 1
        self.count = capacity * self.quads * 4
        mesh = bpy.data.meshes.new(emitter.node.name + ' FX')
        faces = [tuple(range(i, i+4)) for i in range(0, self.count, 4)]
        mesh.from_pydata([(0, 0, 0)] * (3 * self.count), [], faces)
        self.obj = bpy.data.objects.new(emitter.node.name + ' FX', mesh)
        collection.objects.link(self.obj)
        self.obj.parent = rig
        self.obj['warcraft_3_effect'] = emitter.type
        self.obj['warcraft_3_emitter_id'] = emitter.node.id
        self.obj['warcraft_3_particle_capacity'] = capacity
        mesh.materials.append(effect_material(model, emitter))
        self.obj.shape_key_add(name='Hidden')
        mesh.shape_keys.use_relative = False
        attributes_modifier(self.obj, self.count)
        self.curve = None

    def begin(self, sequence):
        curves = create_action_fcurves(sequence.name + ' ' + self.obj.name,
                                      self.obj, sequence, target='KEY')
        self.curve = curves.new(data_path='eval_time')

    def hidden(self, sequence):
        self.begin(sequence)
        self.curve.keyframe_points.insert(0, 0).interpolation = 'CONSTANT'

    def write(self, frame, quads):
        positions, colors, uvs = [], [], []
        for vertices, color, alpha, uv in quads[:self.capacity * self.quads]:
            for vertex, texcoord in zip(vertices, uv):
                positions.extend(vertex)
                colors.extend(color)
                uvs.extend((*texcoord, alpha))
        padding = self.count * 3 - len(positions)
        positions.extend([0.0] * padding)
        colors.extend([0.0] * padding)
        uvs.extend([0.0] * padding)
        if not quads:
            key_time = 0
        else:
            key = self.obj.shape_key_add(name='Sample %d' % len(self.obj.data.shape_keys.key_blocks))
            key.interpolation = 'KEY_LINEAR'
            key.data.foreach_set('co', array('f', positions + colors + uvs))
            key_time = key.frame
        self.curve.keyframe_points.insert(frame, key_time).interpolation = 'CONSTANT'


def atlas_uv(emitter, age, tail=False):
    middle = max(0.00001, min(0.99999, emitter.middle))
    second = age >= middle
    phase = (age-middle)/(1-middle) if second else age/middle
    start, end, repeats = emitter.intervals[(2 if tail else 0) + int(second)]
    width = max(1, end - start)
    cell = int(start + (phase * max(1, repeats) * width) % width)
    return cell_uv(cell, emitter.rows, emitter.columns)


def cell_uv(cell, rows, columns):
    rows, columns = max(1, rows), max(1, columns)
    cell = int(cell) % (rows * columns)
    u, v = (cell % columns) / columns, 1 - (cell // columns + 1) / rows
    return ((u, v), (u+1/columns, v), (u+1/columns, v+1/rows), (u, v+1/rows))


def life_value(values, age, middle):
    if age < middle:
        a, b, t = values[0], values[1], age / max(middle, 0.00001)
    else:
        a, b, t = values[1], values[2], (age-middle) / max(1-middle, 0.00001)
    if isinstance(a, (tuple, list)):
        return tuple(x + (y-x)*t for x, y in zip(a, b))
    return a + (b-a)*t


class Particles:
    def __init__(self, emitter, sequence, globals_, capacity):
        self.emitter, self.sequence, self.globals = emitter, sequence, globals_
        self.capacity, self.accumulator, self.particles = capacity, 0.0, []
        self.random = random.Random(emitter.node.id * 65537 + sequence.interval_start)
        self.previous = None

    def value(self, field, time, default=None):
        return parameter(self.emitter, field, max(0, time), self.sequence, self.globals, default)

    def step(self, time, dt, matrix):
        e = self.emitter
        self.particles = [p for p in self.particles if time - p[0] < e.lifespan]
        visible = self.value('visibility', time) > 0
        rate = max(0, self.value('emission_rate', time))
        if e.squirt:
            track = e.tracks.get('emission_rate')
            absolute = self.sequence.interval_start + max(0, time) * 1000
            previous = self.sequence.interval_start - 0.001 if self.previous is None else self.sequence.interval_start + self.previous * 1000
            if track and track['global_id'] != 0xffffffff:
                index = track['global_id']
                period = self.globals[index] if index < len(self.globals) else 0
                previous = -0.001 if self.previous is None else self.previous * 1000
                absolute = max(0, time) * 1000
                births = 0
                if period > 0:
                    for cycle in range(max(0, math.floor(previous / period)), math.floor(absolute / period) + 1):
                        births += sum(int(max(0, value[0])) for stamp, value in zip(track['times'], track['values'])
                                      if previous < stamp + cycle * period <= absolute)
            elif track:
                births = sum(int(max(0, value[0])) for stamp, value in zip(track['times'], track['values'])
                             if previous < stamp <= absolute and self.sequence.interval_start <= stamp <= self.sequence.interval_end)
            else:
                births = int(rate) if self.previous is None else 0
        else:
            self.accumulator += rate * dt if visible else 0
            births = int(self.accumulator)
            self.accumulator -= births
        self.previous = max(0, time)
        if not visible:
            births = 0
        births = min(births, max(0, self.capacity - len(self.particles)))
        rng = self.random
        for _ in range(births):
            local = Vector((rng.uniform(-0.5, 0.5)*self.value('width', time),
                            rng.uniform(-0.5, 0.5)*self.value('length', time), 0))
            angle = math.radians(self.value('latitude', time))
            rotation = Euler((0 if e.node.flags & 0x20000 else rng.uniform(-angle, angle),
                              rng.uniform(-angle, angle), math.pi/2)).to_matrix()
            speed = self.value('speed', time) * (1 + rng.uniform(-1, 1)*self.value('variation', time))
            velocity = rotation @ Vector((0, 0, speed))
            gravity = self.value('gravity', time)
            model_space = bool(e.node.flags & 0x80000)
            if not model_space:
                local = matrix @ local
                velocity = matrix.to_3x3() @ velocity
                gravity *= matrix.to_scale().z
            self.particles.append((time, local, velocity, gravity, matrix.to_scale().x))
        quads = []
        for birth, origin, velocity, gravity, scale in self.particles:
            elapsed = time - birth
            age = min(1, max(0, elapsed / max(e.lifespan, 0.00001)))
            center = origin + velocity * elapsed + Vector((0, 0, -0.5*gravity*elapsed**2))
            if e.node.flags & 0x80000:
                center = matrix @ center
            size = max(0, life_value(e.scales, age, e.middle)) * abs(scale)
            color = life_value(e.colors, age, e.middle)
            alpha = max(0, min(1, life_value(e.alphas, age, e.middle)))
            if e.head_tail != 1:
                planes = [(Vector((size, 0, 0)), Vector((0, size, 0)))] if e.node.flags & 0x100000 else [
                    (Vector((size, 0, 0)), Vector((0, 0, size))),
                    (Vector((0, size, 0)), Vector((0, 0, size)))]
                for x, y in planes:
                    quads.append(((center-x-y, center+x-y, center+x+y, center-x+y), color, alpha, atlas_uv(e, age)))
            if e.head_tail != 0:
                direction = velocity - Vector((0, 0, gravity*elapsed))
                if e.node.flags & 0x80000:
                    direction = matrix.to_3x3() @ direction
                tip = center - direction * e.tail_length
                axis = direction.normalized() if direction.length else Vector((0, 0, 1))
                side = axis.cross(Vector((0, 0, 1)))
                if side.length < 0.001:
                    side = Vector((1, 0, 0))
                side.normalize()
                for cross in (side, axis.cross(side)):
                    cross = cross * size
                    quads.append(((center-cross, center+cross, tip+cross, tip-cross), color, alpha, atlas_uv(e, age, True)))
        return quads


class Ribbon:
    def __init__(self, emitter, sequence, globals_, capacity):
        self.emitter, self.sequence, self.globals = emitter, sequence, globals_
        self.capacity, self.points, self.previous_time, self.previous_matrix = capacity, [], None, None
        self.accumulator = 0
        self.serial = 0

    def value(self, field, time):
        return parameter(self.emitter, field, max(0, time), self.sequence, self.globals)

    def step(self, time, dt, matrix):
        e = self.emitter
        self.points = [point for point in self.points if time-point[0] < e.lifespan]
        if self.value('visibility', time) > 0 and self.value('alpha', time) > 0:
            self.accumulator += max(0, e.emission_rate) * dt
            births = int(self.accumulator)
            self.accumulator -= births
            for i in range(min(births, self.capacity)):
                fraction = (i+1) / max(1, births)
                transform = self.previous_matrix.lerp(matrix, fraction) if self.previous_matrix else matrix
                birth = time - dt*(1-fraction)
                above = transform @ Vector((0, self.value('height_above', birth), 0))
                below = transform @ Vector((0, -self.value('height_below', birth), 0))
                self.points.append((birth, above, below, self.serial))
                self.serial += 1
        else:
            # A visibility gap must never connect two separate trails.
            self.serial += 1
            self.accumulator = 0
        self.previous_matrix = matrix.copy()
        self.points = self.points[-(self.capacity+1):]
        color = self.value('color', time)
        alpha = max(0, min(1, self.value('alpha', time)))
        slot = self.value('texture_slot', time)
        quads = []
        for older, newer in zip(self.points, self.points[1:]):
            if newer[3] != older[3]+1:
                continue
            drop1 = Vector((0, 0, -0.5*e.gravity*(time-older[0])**2))
            drop2 = Vector((0, 0, -0.5*e.gravity*(time-newer[0])**2))
            uv = cell_uv(slot, e.rows, e.columns)
            # Spread a texture tile over the whole living ribbon.
            left = max(0, min(1, (time-newer[0])/max(e.lifespan, 0.00001)))
            right = max(0, min(1, (time-older[0])/max(e.lifespan, 0.00001)))
            u0, u1 = uv[0][0], uv[1][0]
            v0, v1 = uv[0][1], uv[2][1]
            uv = ((u0+(u1-u0)*right, v1), (u0+(u1-u0)*right, v0),
                  (u0+(u1-u0)*left, v0), (u0+(u1-u0)*left, v1))
            quads.append(((older[1]+drop1, older[2]+drop1, newer[2]+drop2, newer[1]+drop2), color, alpha, uv))
        return quads


def create_effects(model, rig, properties):
    fps = max(5, min(60, getattr(properties, 'effects_fps', 20)))
    max_particles = getattr(properties, 'max_particles', 256)
    collection = bpy.data.collections.new(model.name + ' Effects')
    bpy.context.collection.children.link(collection)
    builders = []
    for emitter in model.effects:
        rates = [emitter.emission_rate]
        if 'emission_rate' in emitter.tracks:
            rates.extend(v[0] for v in emitter.tracks['emission_rate']['values'])
        capacity = max(1, math.ceil(max(rates) * max(0, emitter.lifespan)) + 3)
        if emitter.type == 'particle' and emitter.squirt:
            capacity = max_particles
        if capacity > max_particles:
            model.import_warnings.append('%s: particle capacity limited to %d.' % (emitter.node.name, max_particles))
        capacity = min(max_particles, capacity)
        builder = BakedMesh(model, rig, emitter, capacity, collection)
        builder.hidden(rig.data.warcraft_3.sequencesList[0])
        builders.append(builder)
    scene = bpy.context.scene
    scene_frame = scene.frame_current
    old_action = rig.animation_data.action if rig.animation_data else None
    for seq_index, sequence in enumerate(model.sequences, 1):
        duration = max(0, (sequence.interval_end-sequence.interval_start)/1000)
        times = [min(i/fps, duration) for i in range(math.ceil(duration*fps)+1)]
        entry = rig.data.warcraft_3.sequencesList[seq_index]
        assign_action(rig, entry.action)
        transforms = []
        for time in times:
            frame = time * 1000 / properties.frame_time
            scene.frame_set(int(frame), subframe=frame % 1)
            transforms.append([rig.pose.bones[b.emitter.node.blender_bone_name].matrix.copy() for b in builders])
        for effect_index, builder in enumerate(builders):
            e = builder.emitter
            simulator = (Particles if e.type == 'particle' else Ribbon)(e, sequence, model.global_sequences, builder.capacity)
            builder.begin(entry)
            # Looping idle clips start with a populated emitter instead of a flash.
            if not getattr(sequence, 'non_looping', False) and not getattr(e, 'squirt', False):
                for step in range(math.ceil(max(0, e.lifespan)*fps), 0, -1):
                    simulator.step(-step/fps, 1/fps, transforms[0][effect_index])
            previous = -1/fps
            for index, time in enumerate(times):
                quads = simulator.step(time, time-previous, transforms[index][effect_index])
                builder.write(time*1000/properties.frame_time, quads)
                previous = time
        print('WarCraft FX baked:', sequence.name, len(times), 'samples')
    if old_action:
        assign_action(rig, old_action)
    scene.frame_set(scene_frame)
    rig['warcraft_3_effects'] = len(builders)
    rig['warcraft_3_effects_fps'] = fps
