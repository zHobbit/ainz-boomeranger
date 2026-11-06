"""Assemble the Ainz Boomeranger mod: Death Lord's robe and helm, on the Boomeranger.

Every shipped file is listed in `MANIFEST` with the model it was rebuilt from and, when
the donor came from the Tomb Raiser skeleton, the Boomeranger bone it is re-anchored to.
`BUILT` holds the models made from scratch in `tools.ainz_parts` (the long robe and cape,
the staff over the starter sword, the skeleton chickens). The skills' particle scripts
ride along, recoloured by `tools.vfx`.
"""

import dataclasses
import io
from pathlib import Path

from tools import ainz_parts
from tools.blueprint import bounding_size, decode_blueprint, encode_blueprint
from tools.render import portrait, sheet
from tools.theme import recolor
from tools.vfx import EFFECTS, mod_path, swatches, themed_effects

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "death-lord": ROOT / "work/death-lord/blueprints",
    "elise": ROOT / "work/elise/blueprints",
    "vanilla": ROOT / "work/game-assets/blueprints",
}
PARTICLES = ROOT / "work/game-assets/particles"

BONES = ("torso", "hips", "pack", "hand_l", "hand_r", "shoulder_l", "shoulder_r",
          "thigh_l", "thigh_r", "shin_l", "shin_r", "foot_l", "foot_r", "ui")

# The game's own Boomeranger part for each bone: the frame a donor model is aligned to.
RECIPIENTS = {bone: decode_blueprint((MODELS["vanilla"] / f"c_p_adventurer_lvl3_{bone}.blueprint").read_bytes())
              for bone in BONES}

SKILLS = ("boomerang", "bomb", "bawkbomb", "urn")


def anchor(donor, bone):
    """Where a donor model goes so it sits on `bone` the way the Boomeranger's own part does.

    Both centres are bone-relative, so the offset is their difference; halving at the end
    is floor division, which is what reproduces the original author's placements.
    """
    if bone is None:
        return donor.pos
    recipient = RECIPIENTS[bone]
    return tuple((2 * at + size - donor_size) // 2
                 for at, size, donor_size in zip(recipient.pos, recipient.size, donor.size))


@dataclasses.dataclass(frozen=True)
class Part:
    target: str
    donor: Path
    bone: str = None

    def recolor(self):
        return recolor(decode_blueprint(self.donor.read_bytes()).voxels)

    def blueprint(self):
        decoded = decode_blueprint(self.donor.read_bytes())
        voxels, unmapped = recolor(decoded.voxels)
        if unmapped:
            raise ValueError(f"{self.donor.name} uses colours the palette has not reviewed: {unmapped}")
        return encode_blueprint(voxels, anchor(decoded, self.bone), decoded.entity_blob)


def _death_lord(stem, target, bone=None):
    return Part(target, MODELS["death-lord"] / f"{stem}.blueprint", bone)


def _elise(stem, target):
    return Part(target, MODELS["elise"] / f"{stem}.blueprint")


MANIFEST = [
    _death_lord("c_p_tombraiser_lvl3_core", "blueprints/c_p_adventurer_lvl3_torso.blueprint", "torso"),
    _death_lord("c_p_tombraiser_lvl3_hand_l", "blueprints/c_p_adventurer_lvl3_hand_l.blueprint", "hand_l"),
    _death_lord("c_p_tombraiser_lvl3_hand_r", "blueprints/c_p_adventurer_lvl3_hand_r.blueprint", "hand_r"),
] + [
    _elise(f"c_p_adventurer_lvl3_{bone}", f"blueprints/c_p_adventurer_lvl3_{bone}.blueprint")
    for bone in ("shoulder_l", "shoulder_r", "thigh_l", "thigh_r", "shin_l", "shin_r",
                 "foot_l", "foot_r", "ui")
] + [
    _elise(f"c_p_adventurer_basic_{skill}", f"blueprints/c_p_adventurer_basic_{skill}.blueprint")
    for skill in SKILLS
] + [
    _death_lord("equipment_helm_darkhood", "blueprints/equipment_helm_darkhood.blueprint"),
    _death_lord("equipment_face_mask_halfskull[destral]", "blueprints/equipment_face_mask_halfskull[destral].blueprint"),
]

# Built here: (voxels, pos) per target. The robe hangs off the hips to the feet and the
# cape off the pack bone (the leg bones are two voxels wide, so cloth on them reads as
# wings); the staff replaces the starter sword "Espada Lascada" that every class can
# hold; the chicken parts serve every Boomeranger chicken, the big one included.
BUILT = {
    "blueprints/c_p_adventurer_lvl3_hips.blueprint": ainz_parts.robe,
    "blueprints/c_p_adventurer_lvl3_pack.blueprint": ainz_parts.cape,
    "blueprints/equipment_weapon_1h_sword_001.blueprint": lambda: ainz_parts.staff(MODELS["death-lord"]),
    **{f"blueprints/c_c_quchik_{part}.blueprint":
       (lambda part=part: ainz_parts.skeleton_chicken(part, MODELS["vanilla"]))
       for part in ainz_parts.CHICKEN_PARTS},
}

PROPERTIES = {
    "author": "Xlabausaum",
    "title": "Ainz Boomeranger",
    "tags": "Costume,Boomeranger",
    "notes": "Death Lord (NeodymiumP) re-themed as Ainz Ooal Gown and ported to the "
             "Boomeranger, with violet and spectral green skill effects. Looks only: no damage "
             "or gameplay changes.",
    "previewPath": "ui/ainz.png",
}


def shipped_paths():
    return {part.target for part in MANIFEST} | set(BUILT)


def effect_paths():
    return {mod_path(stem) for stem in EFFECTS}


# Hair and equipment are both authored against the game's generic head bone, so the head
# figure can place the hood by the positions its author gave it. Nothing here is shipped.
HAIR = decode_blueprint((MODELS["elise"] / "c_p_hair_short_unispike[spritzo].blueprint").read_bytes())


def body_parts(files):
    """The robe as the Boomeranger wears it, all in one bone frame."""
    return [(label, voxels, origin) for label, voxels, origin in _placed(files)
            if label.startswith("lvl3_") and label != "lvl3_ui"]


def head_parts(files):
    """The hood and mask, next to the game's own hair for reference."""
    parts = [("hair", HAIR.voxels, HAIR.pos)]
    parts.extend((label, voxels, origin) for label, voxels, origin in _placed(files)
                 if label.startswith("equipment_") and "weapon" not in label)
    return parts


def preview(files):
    """The in-game preview texture: the Boomeranger wearing the robe."""
    return _png(body_parts(files), scale=6)


def contact_sheet(files):
    """Every shipped model on its own, front and side, for reviewing the parts."""
    placed = _placed(files)
    models = [(label, voxels, bounding_size(voxels)) for label, voxels, _ in placed]
    buffer = io.BytesIO()
    sheet(models, buffer, scale=6, columns=4, label_height=13)
    return buffer.getvalue()


def _png(parts, scale):
    buffer = io.BytesIO()
    portrait(parts, buffer, scale=scale)
    return buffer.getvalue()


def _placed(files):
    placed = []
    for path, data in files.items():
        if not path.endswith(".blueprint"):
            continue
        decoded = decode_blueprint(data)
        label = path.rsplit("/", 1)[-1].replace(".blueprint", "").replace("c_p_adventurer_", "")
        placed.append((label, decoded.voxels, decoded.pos))
    return placed


def build_mod():
    files = {part.target: part.blueprint() for part in MANIFEST}
    files.update({target: encode_blueprint(*build()) for target, build in BUILT.items()})
    files[PROPERTIES["previewPath"]] = preview(files)
    files.update(themed_effects(PARTICLES))
    return PROPERTIES, files


def effect_sheet(scale=4):
    """Each skill effect's colour curves, vanilla on the left and themed on the right."""
    from PIL import Image, ImageDraw

    rows = [(stem, swatches((PARTICLES / f"{stem}.pkfx").read_bytes().decode("ascii"))) for stem in EFFECTS]
    strip, gap, label = 24 * scale, 2 * scale, 92 * scale
    widest = max(len(curves) for _, curves in rows)
    height = 8 * scale
    image = Image.new("RGB", (label + 2 * widest * (strip + gap) + 4 * gap, len(rows) * (height + gap)), (18, 16, 24))
    draw = ImageDraw.Draw(image)
    for row, (stem, curves) in enumerate(rows):
        top = row * (height + gap)
        draw.text((gap, top), stem.replace("character_pc_adventurer_", ""), fill=(200, 200, 200))
        for side, pick in enumerate((0, 1)):
            for index, curve in enumerate(curves):
                left = label + side * (widest * (strip + gap) + 4 * gap) + index * (strip + gap)
                colours = curve[pick]
                for x in range(strip):
                    at = x / (strip - 1) * (len(colours) - 1)
                    low = min(int(at), len(colours) - 2) if len(colours) > 1 else 0
                    high = min(low + 1, len(colours) - 1)
                    mix = at - low
                    rgb = [a + (b - a) * mix for a, b in zip(colours[low], colours[high])]
                    draw.line([(left + x, top), (left + x, top + height - 1)],
                              fill=tuple(max(0, min(255, round(c * 255))) for c in rgb))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def main(destination=None):
    from tools.tmod import write_tmod

    root = Path(destination) if destination else ROOT / "dist"
    properties, files = build_mod()
    target = root / f"{properties['title']}.tmod"
    target.parent.mkdir(parents=True, exist_ok=True)
    write_tmod(target, properties, files)
    (root / "preview.png").write_bytes(files[properties["previewPath"]])
    (root / "hood.png").write_bytes(_png(head_parts(files), scale=6))
    (root / "parts.png").write_bytes(contact_sheet(files))
    (root / "vfx.png").write_bytes(effect_sheet())
    print(f"wrote {target} ({len(files)} files, {target.stat().st_size} bytes)")
    print(f"wrote preview.png, hood.png, parts.png and vfx.png in {root}")
    return target


if __name__ == "__main__":
    main()
