"""Ainz Ooal Gown's palette over the donor models' voxel colours.

Both donor mods shade with flat runs of a handful of colours, so this is an exact table
rather than a colour-space transform: what a voxel was painted *as* decides what it
becomes, and the same red is robe when it is painted and spectral green when it glows.
"""

from tools.blueprint import Voxel

VOID = (11, 6, 16)
ROBE_DARK = (32, 18, 48)
ROBE_MID = (56, 32, 82)
ROBE_LIGHT = (86, 50, 124)
ROBE_BRIGHT = (122, 74, 168)
TRIM = (198, 160, 42)
BONE = (232, 227, 208)
BONE_SHADOW = (156, 149, 131)
SPECTRAL = (60, 240, 158)
SPECTRAL_DEEP = (22, 120, 78)

GLOWING_TYPES = (55, 56)

PALETTE = {VOID, ROBE_DARK, ROBE_MID, ROBE_LIGHT, ROBE_BRIGHT, TRIM, BONE, BONE_SHADOW, SPECTRAL, SPECTRAL_DEEP}

# Elise's dark reds and Death Lord's greys are the cloth: they walk up a purple ladder.
PAINTED = {
    (0, 0, 0): VOID,
    (10, 0, 0): ROBE_DARK, (12, 0, 0): ROBE_DARK, (22, 0, 0): ROBE_DARK, (24, 0, 0): ROBE_DARK,
    (26, 25, 30): ROBE_DARK, (30, 30, 30): ROBE_DARK, (41, 35, 28): ROBE_DARK, (47, 40, 32): ROBE_DARK,
    (31, 0, 0): ROBE_MID, (43, 0, 0): ROBE_MID, (61, 0, 0): ROBE_MID, (62, 0, 0): ROBE_MID,
    (42, 98, 43): ROBE_MID, (53, 45, 36): ROBE_MID, (62, 53, 42): ROBE_MID,
    (85, 0, 8): ROBE_LIGHT, (115, 0, 9): ROBE_LIGHT, (118, 0, 0): ROBE_LIGHT, (120, 0, 0): ROBE_LIGHT,
    (141, 0, 0): ROBE_BRIGHT, (150, 0, 0): ROBE_BRIGHT, (151, 0, 0): ROBE_BRIGHT,
    (181, 41, 233): ROBE_BRIGHT, (183, 0, 0): ROBE_BRIGHT,
    # Bone, metal and the two greys the donors use for trim shadows.
    (63, 62, 26): BONE_SHADOW, (66, 65, 28): BONE_SHADOW, (69, 84, 36): BONE_SHADOW,
    (71, 70, 30): BONE_SHADOW, (72, 71, 30): BONE_SHADOW, (75, 75, 75): BONE_SHADOW,
    (76, 76, 30): BONE_SHADOW, (77, 76, 31): BONE_SHADOW, (77, 77, 36): BONE_SHADOW,
    (82, 82, 31): BONE_SHADOW, (89, 60, 29): BONE_SHADOW, (105, 72, 37): BONE_SHADOW,
    (129, 129, 129): BONE_SHADOW, (162, 106, 73): BONE_SHADOW, (223, 155, 116): BONE_SHADOW,
    (171, 171, 171): BONE, (172, 152, 152): BONE, (182, 227, 155): BONE, (202, 188, 188): BONE,
    (202, 202, 202): BONE, (209, 201, 175): BONE, (209, 244, 187): BONE, (210, 210, 210): BONE,
    (225, 173, 131): BONE, (255, 198, 156): BONE,
    # Death Lord's yellow is paint, not glow, and it lands on the skull and the trim.
    (143, 127, 54): TRIM, (165, 134, 62): TRIM, (181, 145, 0): TRIM,
    (231, 194, 89): TRIM, (255, 249, 13): TRIM,
}

# Every emissive voxel becomes spectral green, dark where the donor was dark so the glow
# keeps the model's shading instead of flattening into one colour.
GLOWING = {
    (0, 0, 0): SPECTRAL_DEEP, (31, 0, 0): SPECTRAL_DEEP, (55, 136, 182): SPECTRAL_DEEP,
    (75, 75, 75): SPECTRAL_DEEP, (85, 0, 8): SPECTRAL_DEEP, (120, 0, 0): SPECTRAL_DEEP,
    (0, 13, 253): SPECTRAL_DEEP,
    (69, 155, 205): SPECTRAL, (97, 178, 224): SPECTRAL, (108, 0, 0): SPECTRAL,
    (141, 0, 0): SPECTRAL, (150, 0, 0): SPECTRAL, (181, 0, 0): SPECTRAL,
    (181, 41, 233): SPECTRAL, (255, 116, 2): SPECTRAL, (255, 249, 13): SPECTRAL,
    (0, 213, 11): SPECTRAL, (50, 166, 228): SPECTRAL,
}

_ROBE_LADDER = ((16, VOID), (48, ROBE_DARK), (80, ROBE_MID), (140, ROBE_LIGHT), (220, ROBE_BRIGHT))


def _table(kind):
    return GLOWING if kind in GLOWING_TYPES else PAINTED


def target_for(colour, kind):
    """The Ainz colour for one source voxel colour under one material type."""
    table = _table(kind)
    if colour in table:
        return table[colour]
    return _fallback(colour, kind in GLOWING_TYPES)


def _fallback(colour, glowing):
    brightness = max(colour)
    if glowing:
        return SPECTRAL if brightness >= 140 else SPECTRAL_DEEP
    for cutoff, rung in _ROBE_LADDER:
        if brightness < cutoff:
            return rung
    return BONE


def recolor(voxels):
    """Re-painted voxels plus the source colours that had to fall back, so a build can
    refuse to ship a colour nobody reviewed."""
    painted = []
    unmapped = set()
    for voxel in voxels:
        colour = (voxel.r, voxel.g, voxel.b)
        if colour not in _table(voxel.t):
            unmapped.add(colour)
        red, green, blue = target_for(colour, voxel.t)
        painted.append(Voxel(voxel.x, voxel.y, voxel.z, red, green, blue, voxel.w, voxel.t))
    return painted, sorted(unmapped)
