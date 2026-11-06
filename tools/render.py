"""Orthographic previews of voxel models.

The game is off limits for this project, so the only way to judge a recoloured or
transplanted part is to draw it here: front and side, one cell per model.
"""

import PIL.Image
import PIL.ImageDraw

from tools.blueprint import Voxel

BACKGROUND = (28, 24, 34)
LABEL = (198, 194, 208)

FRONT = (0, 1, 2)   # x across, y up, z into the screen
SIDE = (2, 1, 0)    # z across, y up, x into the screen


def front(voxels, size, near="near"):
    return _project(voxels, size, FRONT, near)


def side(voxels, size, near="near"):
    return _project(voxels, size, SIDE, near)


def figure(parts, view=front):
    """Every part placed at its own `pos`, projected as one character.

    Parts are authored in their own grid, so the figure is their union shifted into the
    shared bone frame - which is the only way to see whether the set actually fits.
    """
    placed = [Voxel(voxel.x + origin[0], voxel.y + origin[1], voxel.z + origin[2],
                    voxel.r, voxel.g, voxel.b, voxel.w, voxel.t)
              for _, voxels, origin in parts for voxel in voxels]
    if not placed:
        return []
    floors = tuple(min(getattr(voxel, axis) for voxel in placed) for axis in ("x", "y", "z"))
    ceiling = tuple(max(getattr(voxel, axis) for voxel in placed) for axis in ("x", "y", "z"))
    moved = [Voxel(voxel.x - floors[0], voxel.y - floors[1], voxel.z - floors[2],
                   voxel.r, voxel.g, voxel.b, voxel.w, voxel.t) for voxel in placed]
    size = tuple(top - floor + 1 for top, floor in zip(ceiling, floors))
    return view(moved, size)


def _project(voxels, size, axes, near):
    """One colour per visible column, rows indexed by y ascending (row 0 is the floor)."""
    across, up, into = axes
    width, height = size[across], size[up]
    if not voxels or width <= 0 or height <= 0:
        return []
    grid = [[None] * width for _ in range(height)]
    visible = {}
    for voxel in voxels:
        point = (voxel.x, voxel.y, voxel.z)
        column, row, depth = point[across], point[up], point[into]
        holds = visible.get((row, column))
        if holds is not None and (holds >= depth if near == "near" else holds <= depth):
            continue
        visible[(row, column)] = depth
        grid[row][column] = (voxel.r, voxel.g, voxel.b)
    return grid


def portrait(parts, target, scale=8, gap=2):
    """The assembled figure, front then side, in one PNG."""
    first, second = figure(parts), figure(parts, view=side)
    width, height = _width(first) + gap + _width(second), max(len(first), len(second))
    image = PIL.Image.new("RGB", (width * scale, height * scale), BACKGROUND)
    draw = PIL.ImageDraw.Draw(image)
    _paint(draw, first, 0, 0, scale)
    _paint(draw, second, (_width(first) + gap) * scale, 0, scale)
    image.save(target, format="PNG")
    return image.size


def sheet(models, target, scale=6, columns=4, label_height=14):
    """`models` is (label, voxels, size) per part, laid out in a regular grid of PNG cells.

    Returns the image size, which is handy for the caller's own checks.
    """
    if not models:
        raise ValueError("no models to render")
    views = []
    for label, voxels, size in models:
        first, second = front(voxels, size), side(voxels, size)
        views.append((label, first, second, _width(first) + 1 + _width(second), max(len(first), len(second))))

    cell_width = max(view[3] for view in views)
    cell_height = max(view[4] for view in views)
    rows = -(-len(views) // columns)
    image_size = (min(columns, len(views)) * cell_width * scale, rows * (cell_height * scale + label_height))
    image = PIL.Image.new("RGB", image_size, BACKGROUND)
    draw = PIL.ImageDraw.Draw(image)

    for index, (label, first, second, _, _) in enumerate(views):
        origin_x = (index % columns) * cell_width * scale
        origin_y = (index // columns) * (cell_height * scale + label_height)
        _paint(draw, first, origin_x, origin_y, scale, cell_height)
        _paint(draw, second, origin_x + (_width(first) + 1) * scale, origin_y, scale, cell_height)
        draw.text((origin_x + 1, origin_y + cell_height * scale + 2), label, fill=LABEL)

    image.save(target, format="PNG")
    return image_size


def _width(grid):
    return len(grid[0]) if grid else 0


def _paint(draw, grid, origin_x, origin_y, scale, cell_height=None):
    """Rows are y ascending, so the grid stands on the bottom of its cell."""
    floor = len(grid) if cell_height is None else cell_height
    for row, line in enumerate(grid):
        for column, colour in enumerate(line):
            if colour is None:
                continue
            top = origin_y + (floor - 1 - row) * scale
            left = origin_x + column * scale
            draw.rectangle((left, top, left + scale - 1, top + scale - 1), fill=colour)
