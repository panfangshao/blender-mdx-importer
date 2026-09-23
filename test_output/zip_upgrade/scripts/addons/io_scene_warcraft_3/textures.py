"""Resolve model-relative textures and provide explicit missing-FX previews."""
from pathlib import Path
import bpy
from . import constants


def load_images(model, preferences, team):
    result = []
    roots = [Path(getattr(model, 'source_dir', '.'))]
    for value in (preferences.alternativeResourceFolder, preferences.resourceFolder):
        if value:
            roots.append(Path(bpy.path.abspath(value)))
    extension = preferences.textureExtension.lstrip('.') or 'png'
    for texture in model.textures:
        if texture.replaceable_id in (1, 2):
            name = (constants.TEAM_COLOR_IMAGES if texture.replaceable_id == 1
                    else constants.TEAM_GLOW_IMAGES)[team]
        else:
            name = texture.image_file_name
        relative = Path(name.replace('\\', '/'))
        candidates = []
        for root in roots:
            for file in (relative, Path(relative.name)):
                if file.suffix.lower() == '.blp':
                    candidates.extend(root / file.with_suffix('.' + ext)
                                      for ext in dict.fromkeys((extension, 'png', 'tga', 'dds')))
                else:
                    candidates.append(root / file)
        image = None
        for path in candidates:
            if path.is_file():
                try:
                    image = bpy.data.images.load(str(path), check_existing=True)
                    break
                except RuntimeError:
                    pass
        if image is None and texture.replaceable_id in (1, 2):
            image = preview_image(name, color=constants.TEAM_COLORS[team],
                                  soft=texture.replaceable_id == 2)
        if image is None:
            image = bpy.data.images.new(relative.stem or 'Missing texture', 1, 1)
            image.source = 'FILE'
            image.filepath = str(candidates[0]) if candidates else name
            image['warcraft_3_missing'] = name
        image['warcraft_3_source'] = name
        result.append(image)
    return result


def preview_image(name, rows=1, columns=1, color=(1, 1, 1), soft=True):
    # A procedural soft spot is a fallback preview, not the original game image.
    rows, columns = max(1, rows), max(1, columns)
    size = min(512, max(64, 16 * max(rows, columns)))
    image = bpy.data.images.new(name + ' [preview]', size, size, alpha=True)
    pixels = []
    for y in range(size):
        for x in range(size):
            u = ((x + 0.5) * columns / size) % 1 * 2 - 1
            v = ((y + 0.5) * rows / size) % 1 * 2 - 1
            alpha = max(0, 1 - u*u - v*v)**2 if soft else 1
            pixels.extend((*color, alpha))
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def effect_image(model, texture_id, rows=1, columns=1, replaceable_id=0):
    if replaceable_id in (1, 2):
        return preview_image('Replaceable FX', rows, columns,
                             color=constants.TEAM_COLORS.get(getattr(model, 'team_color', 'RED'), (1, 0, 0)),
                             soft=replaceable_id == 2)
    images = getattr(model, 'blender_images', [])
    if 0 <= texture_id < len(images):
        image = images[texture_id]
        if not image.get('warcraft_3_missing'):
            return image
        missing = image['warcraft_3_missing']
    else:
        missing = 'texture ID %s' % texture_id
    warning = 'Missing FX texture: %s (soft preview used)' % missing
    if warning not in model.import_warnings:
        model.import_warnings.append(warning)
    cache = getattr(model, '_effect_preview_images', None)
    if cache is None:
        cache = model._effect_preview_images = {}
    key = (missing, rows, columns)
    if key not in cache:
        cache[key] = preview_image(missing, rows, columns)
    return cache[key]
