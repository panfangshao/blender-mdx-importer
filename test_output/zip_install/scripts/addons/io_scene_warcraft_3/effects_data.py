"""Classic MDX emitter records and track evaluation (no Blender dependency)."""
from bisect import bisect_right
from types import SimpleNamespace


PARTICLE_TRACKS = dict(KP2S=('speed', 'f'), KP2R=('variation', 'f'),
                      KP2L=('latitude', 'f'), KP2G=('gravity', 'f'),
                      KP2E=('emission_rate', 'f'), KP2N=('width', 'f'),
                      KP2W=('length', 'f'), KP2V=('visibility', 'f'))
RIBBON_TRACKS = dict(KRHA=('height_above', 'f'), KRHB=('height_below', 'f'),
                    KRAL=('alpha', 'f'), KRCO=('color', '3f'),
                    KRTX=('texture_slot', 'I'), KRVS=('visibility', 'f'))


def read_track(reader, fmt='f'):
    count, interpolation, global_id = reader.getf('<III')
    result = dict(times=[], values=[], incoming=[], outgoing=[], interpolation=interpolation,
                  global_id=global_id)
    if interpolation not in (0, 1, 2, 3):
        raise ValueError('Unsupported MDX interpolation: %s' % interpolation)
    for _ in range(count):
        result['times'].append(reader.getf('<I')[0])
        result['values'].append(reader.getf('<' + fmt))
        if interpolation > 1:
            result['incoming'].append(reader.getf('<' + fmt))
            result['outgoing'].append(reader.getf('<' + fmt))
    return result


def read_emitters(data, reader_type, read_node, kind):
    reader = reader_type(data)
    result = []
    while reader.offset < len(data):
        start = reader.offset
        size = reader.getf('<I')[0]
        end = start + size
        if size < 4 or end > len(data):
            raise ValueError('Invalid MDX emitter size')
        emitter = SimpleNamespace(type=kind, node=read_node(reader), tracks={})
        if kind == 'particle':
            for field in ('speed', 'variation', 'latitude', 'gravity', 'lifespan',
                          'emission_rate', 'width', 'length'):
                setattr(emitter, field, reader.getf('<f')[0])
            emitter.filter_mode, emitter.rows, emitter.columns, emitter.head_tail = reader.getf('<4I')
            emitter.tail_length, emitter.middle = reader.getf('<2f')
            emitter.colors = [reader.getf('<3f') for _ in range(3)]
            emitter.alphas = tuple(x / 255 for x in reader.getf('<3B'))
            emitter.scales = reader.getf('<3f')
            emitter.intervals = [reader.getf('<3I') for _ in range(4)]
            emitter.texture_id, emitter.squirt, emitter.priority, emitter.replaceable_id = reader.getf('<iIiI')
            track_map = PARTICLE_TRACKS
        else:
            emitter.height_above, emitter.height_below, emitter.alpha = reader.getf('<3f')
            emitter.color = reader.getf('<3f')
            emitter.lifespan = reader.getf('<f')[0]
            emitter.texture_slot, emitter.emission_rate, emitter.rows, emitter.columns, emitter.material_id = reader.getf('<4Ii')
            emitter.gravity = reader.getf('<f')[0]
            track_map = RIBBON_TRACKS
        while reader.offset < end:
            tag = reader.getid(tuple(track_map))
            field, fmt = track_map[tag]
            emitter.tracks[field] = read_track(reader, fmt)
        if reader.offset != end:
            raise ValueError('MDX emitter record overrun')
        result.append(emitter)
    return result


def sample(track, time_ms, interval, globals_, default, elapsed_ms=0):
    """Evaluate only keys belonging to the sequence, or a global loop."""
    if not track or not track['times']:
        return default
    times, values = track['times'], track['values']
    global_id = track['global_id']
    if global_id != 0xffffffff:
        if global_id >= len(globals_) or globals_[global_id] <= 0:
            return default
        time_ms = elapsed_ms % globals_[global_id]
        low, high = 0, len(times)
    else:
        low = bisect_right(times, interval[0] - 1)
        high = bisect_right(times, interval[1])
        if low == high:
            # A sole key at zero is commonly a constant shared by all clips.
            if len(times) == 1 and times[0] == 0:
                return values[0][0] if len(values[0]) == 1 else values[0]
            return default
    left = max(low, min(high - 1, bisect_right(times, time_ms, low, high) - 1))
    right = min(left + 1, high - 1)
    a, b = values[left], values[right]
    t = max(0, min(1, (time_ms - times[left]) / max(1, times[right] - times[left])))
    mode = track['interpolation']
    if left == right or mode == 0:
        value = a
    elif mode == 1:
        value = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        out_tan, in_tan = track['outgoing'][left], track['incoming'][right]
        if mode == 2:
            weights = (2*t**3 - 3*t*t + 1, -2*t**3 + 3*t*t, t**3 - 2*t*t + t, t**3 - t*t)
        else:
            weights = ((1-t)**3, t**3, 3*t*(1-t)**2, 3*t*t*(1-t))
        value = tuple(sum(w*v for w, v in zip(weights, components))
                      for components in zip(a, b, out_tan, in_tan))
    return value[0] if len(value) == 1 else value


def parameter(emitter, field, seconds, sequence, globals_, default=None):
    if default is None:
        default = getattr(emitter, field, 1.0 if field == 'visibility' else 0.0)
    return sample(emitter.tracks.get(field), sequence.interval_start + seconds * 1000,
                  (sequence.interval_start, sequence.interval_end), globals_, default, seconds * 1000)
