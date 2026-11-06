"""Models built here rather than borrowed: Ainz's long robe and cape, his staff, and the
skeleton chickens.

Every part is authored in its bone's own frame, the way the game's parts are: x across the
body (left is +x), y up, z forward (the Boomeranger's feet and the starter sword both
point +z). The hip joint sits at the waist and the legs hang about ten voxels below it, so
the robe is a hollow skirt down to there and the cape hangs from the pack bone on the
upper back. The staff is the one model here that is borrowed: Death Lord's, recoloured. Those lengths are estimates (the skeleton itself is not readable here) and are
the knobs to turn after an in-game look.
"""

from pathlib import Path

from tools.blueprint import Voxel, decode_blueprint
from tools.theme import (
    GLOWING_TYPES,
    ROBE_BRIGHT,
    ROBE_DARK,
    ROBE_LIGHT,
    ROBE_MID,
    SPECTRAL,
    TRIM,
    VOID,
)

SOLID, GLOWING_SOLID = 21, 55

# Below the hip joint to the soles, and from the pack joint (upper back) to the ground.
ROBE_DROP = 10
CAPE_DROP = 18

# The Staff of Ainz Ooal Gown is Death Lord's own: NeodymiumP modelled it with the seven
# serpents twisting up the shaft and a jewel for each in the head. Its seven glowing gems
# stay as authored; only its neon yellow becomes the hood's gold so the set matches.
GEMS = ((50, 166, 228), (0, 13, 253), (255, 116, 2), (181, 0, 0), (0, 213, 11),
        (181, 41, 233), (255, 249, 13))
GOLD_DARK = (150, 116, 28)
STAFF_GOLD = {(255, 249, 13): TRIM, (181, 145, 0): GOLD_DARK}


def _box(voxels):
    """Shift voxels given in bone coordinates into a grid, returning (voxels, pos)."""
    low = tuple(min(point[axis] for point in voxels) for axis in range(3))
    grid = [Voxel(x - low[0], y - low[1], z - low[2], *colour, 0, kind)
            for (x, y, z), (colour, kind) in voxels.items()]
    return grid, low


def _paint(voxels, point, colour, kind=SOLID):
    voxels[tuple(point)] = (colour, kind)


def robe():
    """A hollow skirt from the waist to the feet, widening as it falls.

    Purple outside with a darker lining showing at the front slit, a gold belt at the top,
    gold edging down both sides of the slit and a gold hem.
    """
    voxels = {}
    for step in range(ROBE_DROP + 2):
        y = 1 - step
        fall = step / (ROBE_DROP + 1)
        half_x = 3 + round(2.5 * fall)
        half_z = 3 + round(1.5 * fall)
        slit = 1 if step >= 3 else 0
        for x in range(-half_x, half_x + 1):
            for z in range(-half_z, half_z + 1):
                edge_x, edge_z = abs(x) == half_x, abs(z) == half_z
                corner = edge_x and edge_z
                if not (edge_x or edge_z) or corner:
                    continue
                front = z == half_z
                if front and abs(x) < slit:
                    _paint(voxels, (x, y, z - 1), VOID)
                    continue
                if step == 0:
                    colour = TRIM
                elif step == ROBE_DROP + 1:
                    colour = TRIM
                elif front and abs(x) == slit and slit:
                    colour = TRIM
                elif front or (edge_x and z > 0):
                    colour = ROBE_LIGHT if step % 4 == 2 else ROBE_MID
                else:
                    colour = ROBE_DARK if abs(x) == half_x and z < 0 else ROBE_MID
                _paint(voxels, (x, y, z), colour)
        # The corners are bevelled one voxel in, so the skirt reads round, not boxy.
        for sx in (-1, 1):
            for sz in (-1, 1):
                colour = TRIM if step in (0, ROBE_DROP + 1) else ROBE_DARK
                _paint(voxels, (sx * (half_x - 1), y, sz * (half_z - 1)), colour)
    return _box(voxels)


def cape():
    """A long cape off the upper back, flaring out behind at the bottom, with a high gold
    collar of spikes standing up behind the hood."""
    voxels = {}
    for step in range(CAPE_DROP + 1):
        y = 1 - step
        fall = step / CAPE_DROP
        half_x = 4 + round(3 * fall)
        back = -3 - round(2 * fall * fall)
        for x in range(-half_x, half_x + 1):
            side = abs(x) == half_x
            if step == CAPE_DROP or side:
                outer = TRIM
            elif abs(x) == half_x - 2 and step > 1:
                outer = ROBE_LIGHT
            else:
                outer = ROBE_MID if (x + step) % 5 else ROBE_DARK
            _paint(voxels, (x, y, back), outer)
            _paint(voxels, (x, y, back + 1), VOID if not side else TRIM)
    # The collar: gold spikes rising behind the head, tallest in the middle.
    for x in range(-4, 5):
        height = 4 - abs(x) // 2 if x % 2 == 0 else 2
        for rise in range(1, height + 1):
            _paint(voxels, (x, 1 + rise, -3), TRIM if rise < height else ROBE_BRIGHT)
    return _box(voxels)


def staff(source):
    """Death Lord's Staff of Ainz Ooal Gown, gold matched to the robe, gems untouched.

    It keeps its author's grip (the origin, where the hand holds it) and its orientation:
    the head points +z, the way the starter sword's blade does.
    """
    decoded = decode_blueprint((Path(source) / "equipment_weapon_staff_dragon_flux.blueprint").read_bytes())
    voxels = []
    for v in decoded.voxels:
        colour = (v.r, v.g, v.b)
        if v.t not in GLOWING_TYPES:
            if colour not in STAFF_GOLD:
                raise ValueError(f"the staff has an unreviewed painted colour {colour}")
            colour = STAFF_GOLD[colour]
        voxels.append(Voxel(v.x, v.y, v.z, *colour, v.w, v.t))
    return voxels, decoded.pos


CHICKEN_PARTS = ("head", "beak", "crest", "l_eye", "r_eye", "l_wing", "r_wing", "l_foot", "r_foot")


def skeleton_chicken(part, source):
    """One part of the Boomeranger's chicken, rebuilt from the undead skin's bony chicken:
    the bone keeps its own shading and only the glowing red eye turns spectral green."""
    decoded = decode_blueprint((Path(source) / f"c_c_quchik_undead_{part}.blueprint").read_bytes())
    voxels = [Voxel(v.x, v.y, v.z, *SPECTRAL, v.w, v.t) if v.t in GLOWING_TYPES else v
              for v in decoded.voxels]
    return voxels, decoded.pos
