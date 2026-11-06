"""Ainz Ooal Gown's palette over the Boomeranger's PopcornFX particle scripts.

A ``.pkfx`` is text: a flat list of objects, each a ``Class<TAB>$LOCAL$/Id`` header line
and a braced body. Particle colour lives in ``CParticleSamplerCurve`` (and ``...DoubleCurve``)
objects of ``ValueType = Float3/Float4``: either the evaluator of a ``Color``/``Color2``/...
field evolver, or a named sampler (``ColorCurveGlobal``, ``Rays_Color``...) that the scripts
sample. Textures are only masks and gradients, so the scripts are all a mod has to ship.

Each key becomes its luminance times a tint, and the original hue picks the tint: fire
and arcane light (reds, oranges, yellows, magentas, purples) turns violet, cool glows turn spectral green, greys go
by brightness. Hermite curves carry in/out slopes in ``FloatTangents``; for those one tint
and one gain (keeping the curve's
brightest channel as bright as it was) serve the whole curve, so the map stays linear and applying it to keys and slopes alike is
exact: the curve keeps its timing and shape. ``Interpolator = Linear`` curves have no slopes
and take a tint per key, which turns the vanilla orange-to-green ramps into violet-to-green.
Alpha (the fourth channel) is never touched, nor is anything that is not a colour curve.
"""

import colorsys
import re
from pathlib import Path

from tools.theme import SPECTRAL

HEADER = re.compile(r"^C\w+\t\$LOCAL\$/\S+\r?$", re.M)
LIST = re.compile(r"(\t(?:FloatValues|FloatTangents)\d* = \r?\n\t\{\r?\n)(.*?)(\t\};)", re.S)
NUMBER_LINE = re.compile(r"^(\t\t)(\S+)(,\r?)$", re.M)

LUMA = (0.2126, 0.7152, 0.0722)
# Each tint has its brightest channel at 1, so a white key becomes the pure tint.
GREEN = tuple(round(channel / max(SPECTRAL), 4) for channel in SPECTRAL)
VIOLET = (0.62, 0.22, 1.0)
# Hues (degrees) at or past ``COOL_FROM`` and before ``WARM_FROM`` count as cool.
COOL_FROM, WARM_FROM = 75, 250
# Below this saturation a key is grey or white: bright ones glow green, dim ones are smoke.
GREY_SATURATION = 0.2
GLOW_LUMA = 0.5

# The base-skin effects of the four skills Elise re-models. Heal, energy, fairy and shield
# stay vanilla: their colours tell the player what a pickup or buff does.
EFFECTS = (
    "character_pc_adventurer_ability_bomb_explosion_01",
    "character_pc_adventurer_ability_bomb_explosion_large_01",
    "character_pc_adventurer_ability_bomb_explosion_small_01",
    "character_pc_adventurer_ability_bomb_fuse_01",
    "character_pc_adventurer_ability_bomb_impact_01",
    "character_pc_adventurer_ability_bomb_projectile_01",
    "character_pc_adventurer_ability_boomerang_catch_01",
    "character_pc_adventurer_ability_boomerang_impact_01",
    "character_pc_adventurer_ability_boomerang_large_impact_01",
    "character_pc_adventurer_ability_boomerang_large_projectile_01",
    "character_pc_adventurer_ability_boomerang_projectile_01",
    "character_pc_adventurer_ability_boomerang_small_impact_01",
    "character_pc_adventurer_ability_boomerang_small_projectile_01",
    "character_pc_adventurer_ability_randomthrow_bomb_explosion_01",
    "character_pc_adventurer_ability_randomthrow_chicken_despawn_01",
    "character_pc_adventurer_ability_randomthrow_chicken_spawn_01",
    "character_pc_adventurer_ability_randomthrow_explosion_01",
    "character_pc_adventurer_ability_randomthrow_projectile_01",
    "character_pc_adventurer_gem_chickenbomb_01",
    "character_pc_adventurer_gem_chickenbomb_large_01",
    "character_pc_adventurer_gem_chickenbomb_small_01",
)


def mod_path(stem):
    """Where a mod overrides a game particle: the archive folder, lowercased."""
    return f"particles/vfx/particles/{stem}.pkfx"


def format_float(value):
    """PopcornFX's own spelling: 7 decimals and a three-digit exponent (``1.25e+000``)."""
    if value == 0:
        value = 0.0
    mantissa, exponent = f"{value:.7e}".split("e")
    return f"{mantissa}e{exponent[0]}{int(exponent[1:]):03d}"


def objects(text):
    """``(class, id, start, end)`` for every object, in file order."""
    starts = [match.start() for match in HEADER.finditer(text)] + [len(text)]
    found = []
    for start, end in zip(starts, starts[1:]):
        name, local = text[start:text.index("\n", start)].strip().split("\t")
        found.append((name, local, start, end))
    return found


def _field(body, name):
    match = re.search(rf"^\t{name} = \"?([^\"\r\n;]*)\"?;\r?$", body, re.M)
    return match.group(1) if match else None


def colour_curves(text):
    """``{id: channels}`` of the curves that hold particle colour."""
    found = objects(text)
    evaluated = set()
    for name, _, start, end in found:
        body = text[start:end]
        if name == "CParticleEvolver_Field" and re.fullmatch(r"Color\d*", _field(body, "Name") or ""):
            evaluated.add(_field(body, "Evaluator"))
    curves = {}
    for name, local, start, end in found:
        if name not in ("CParticleSamplerCurve", "CParticleSamplerDoubleCurve"):
            continue
        body = text[start:end]
        channels = {"Float3": 3, "Float4": 4}.get(_field(body, "ValueType"))
        sampler = _field(body, "SamplerName") or ""
        if channels and (local in evaluated or "color" in sampler.lower()):
            curves[local] = channels
    return curves


def luma(rgb):
    return sum(weight * channel for weight, channel in zip(LUMA, rgb))


def tint(rgb, colour, gain=1.0):
    """The linear recolour: the input's luminance, times ``gain``, carried by ``colour``."""
    return tuple(gain * luma(rgb) * channel for channel in colour)


def brightness_gain(rgbs):
    """The one gain that keeps a curve's brightest channel where it was: a saturated purple
    has little luminance, and luminance alone would turn it nearly black."""
    peak_luma = max((luma(rgb) for rgb in rgbs), default=0.0)
    return max(max(rgb) for rgb in rgbs) / peak_luma if peak_luma > 0 else 1.0


def tone(rgb):
    """The tint one colour key turns into, judged by its original hue."""
    hue, saturation, _ = colorsys.rgb_to_hsv(*(max(channel, 0.0) for channel in rgb))
    if saturation < GREY_SATURATION:
        return GREEN if luma(rgb) >= GLOW_LUMA else VIOLET
    return GREEN if COOL_FROM <= hue * 360 < WARM_FROM else VIOLET


def _groups(values, channels):
    return [values[at:at + channels] for at in range(0, len(values), channels)]


def _numbers(text):
    return [float(value) for _, value, _ in NUMBER_LINE.findall(text)]


def keys(body, channels):
    """Every colour key of a curve, from all its ``FloatValues`` lists."""
    return [key for opening, numbers, _ in LIST.findall(body) if "FloatValues" in opening
            for key in _groups(_numbers(numbers), channels)]


def is_hermite(body):
    return "FloatTangents" in body


def _recolour_body(body, channels):
    """The curve rewritten, and the tints it used."""
    used = set()
    rgbs = [key[:3] for key in keys(body, channels)]
    hermite = is_hermite(body)
    curve_tone = tone(max(rgbs, key=luma)) if hermite else None
    curve_gain = brightness_gain(rgbs) if hermite else None

    def rewrite(match):
        opening, numbers, closing = match.groups()
        lines = NUMBER_LINE.findall(numbers)
        values = _numbers(numbers)
        if len(values) % channels:
            raise ValueError(f"{len(values)} numbers do not split into {channels}-channel keys")
        out = []
        for key in _groups(values, channels):
            colour = curve_tone or tone(key[:3])
            gain = curve_gain if hermite else brightness_gain([key[:3]])
            used.add(colour)
            out.extend(tint(key[:3], colour, gain) + tuple(key[3:]))
        return opening + "".join(f"{indent}{format_float(value)}{tail}\n"
                                 for (indent, _, tail), value in zip(lines, out)) + closing

    return LIST.sub(rewrite, body), used


def recolour(text):
    """The script with every colour curve tinted; returns ``(text, {id: tints used})``."""
    curves = colour_curves(text)
    pieces, chosen, at = [], {}, 0
    for _, local, start, end in objects(text):
        if local not in curves:
            continue
        body, chosen[local] = _recolour_body(text[start:end], curves[local])
        pieces.append(text[at:start])
        pieces.append(body)
        at = end
    pieces.append(text[at:])
    return "".join(pieces), chosen


def themed_effects(source):
    """``{mod path: bytes}`` for every effect in ``EFFECTS`` read from ``source``."""
    files = {}
    for stem in EFFECTS:
        text = (Path(source) / f"{stem}.pkfx").read_bytes().decode("ascii")
        files[mod_path(stem)] = recolour(text)[0].encode("ascii")
    return files


def swatches(text):
    """For each colour curve, its keys' RGB before and after: ``[(before, after), ...]``."""
    out, _ = recolour(text)
    old, new = (dict((local, text_[start:end]) for _, local, start, end in objects(text_)) for text_ in (text, out))
    return [([key[:3] for key in keys(old[local], channels)], [key[:3] for key in keys(new[local], channels)])
            for local, channels in colour_curves(text).items()]
