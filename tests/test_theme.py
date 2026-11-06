from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.blueprint import Voxel, decode_blueprint
from tools.theme import (
    BONE,
    BONE_SHADOW,
    GLOWING_TYPES,
    ROBE_BRIGHT,
    ROBE_DARK,
    ROBE_LIGHT,
    ROBE_MID,
    SPECTRAL,
    SPECTRAL_DEEP,
    TRIM,
    VOID,
    recolor,
    target_for,
)

PALETTE = {VOID, ROBE_DARK, ROBE_MID, ROBE_LIGHT, ROBE_BRIGHT, TRIM, BONE, BONE_SHADOW, SPECTRAL, SPECTRAL_DEEP}

# The models the port rebuilds from: Elise's Boomeranger skeleton and skill props, plus
# everything Death Lord itself ships. Not its spider pet, hair or UGC weapons.
ELISE = [Path("work/elise/blueprints/c_p_adventurer_lvl3_%s.blueprint" % bone) for bone in
         ("torso", "hips", "pack", "hand_l", "hand_r", "shoulder_l", "shoulder_r",
          "thigh_l", "thigh_r", "shin_l", "shin_r", "foot_l", "foot_r", "ui")]
ELISE += [Path("work/elise/blueprints/c_p_adventurer_basic_%s.blueprint" % skill) for skill in
          ("boomerang", "bomb", "bawkbomb", "urn")]
DEATH_LORD = sorted(path for path in (ROOT / "work/death-lord/blueprints").glob("*.blueprint")
                    if not path.stem.endswith(("_a", "_s", "_t")))


class PaletteTests(unittest.TestCase):
    def test_the_painted_robe_ladder_is_purple(self):
        self.assertEqual(target_for((0, 0, 0), 21), VOID)
        self.assertEqual(target_for((12, 0, 0), 21), ROBE_DARK)
        self.assertEqual(target_for((30, 30, 30), 21), ROBE_DARK)
        self.assertEqual(target_for((43, 0, 0), 21), ROBE_MID)
        self.assertEqual(target_for((62, 0, 0), 21), ROBE_MID)
        self.assertEqual(target_for((85, 0, 8), 21), ROBE_LIGHT)
        self.assertEqual(target_for((120, 0, 0), 21), ROBE_LIGHT)
        self.assertEqual(target_for((181, 41, 233), 21), ROBE_BRIGHT)

    def test_greys_and_skins_read_as_bone(self):
        for colour in ((75, 75, 75), (129, 129, 129), (162, 106, 73), (223, 155, 116)):
            self.assertEqual(target_for(colour, 21), BONE_SHADOW, colour)
        for colour in ((171, 171, 171), (202, 202, 202), (210, 210, 210), (225, 173, 131), (255, 198, 156)):
            self.assertEqual(target_for(colour, 21), BONE, colour)

    def test_the_yellow_is_trim_not_glow(self):
        self.assertEqual(target_for((255, 249, 13), 21), TRIM)
        self.assertEqual(target_for((181, 145, 0), 21), TRIM)

    def test_the_same_red_is_green_when_it_emits(self):
        """Death Lord's dominant red only ever appears in glowing voxels, so that is the
        accent that carries the spectral green."""
        self.assertEqual(target_for((181, 0, 0), 55), SPECTRAL)
        self.assertEqual(target_for((181, 0, 0), 56), SPECTRAL)
        self.assertEqual(target_for((108, 0, 0), 55), SPECTRAL)
        self.assertEqual(target_for((85, 0, 8), 55), SPECTRAL_DEEP)
        self.assertEqual(target_for((31, 0, 0), 55), SPECTRAL_DEEP)

    def test_a_colour_outside_the_vocabulary_falls_back_on_brightness(self):
        self.assertEqual(target_for((9, 9, 9), 21), VOID)
        self.assertEqual(target_for((200, 40, 40), 21), ROBE_BRIGHT)
        self.assertEqual(target_for((250, 250, 250), 21), BONE)
        self.assertEqual(target_for((20, 20, 20), 56), SPECTRAL_DEEP)
        self.assertEqual(target_for((240, 240, 240), 56), SPECTRAL)

    def test_recolor_keeps_every_voxel_place_and_material(self):
        voxels = [Voxel(1, 2, 3, 181, 0, 0, 3, 56), Voxel(1, 2, 4, 30, 30, 30, 0, 21)]
        recolored, unmapped = recolor(voxels)
        self.assertEqual([(v.x, v.y, v.z, v.w, v.t) for v in recolored], [(1, 2, 3, 3, 56), (1, 2, 4, 0, 21)])
        self.assertEqual([v.r for v in recolored], [SPECTRAL[0], ROBE_DARK[0]])
        self.assertEqual(unmapped, [])


class CoverageTests(unittest.TestCase):
    def test_every_voxel_of_every_donor_model_has_a_reviewed_colour(self):
        """A fallback that fires here is a colour nobody looked at, so it fails the build."""
        files = ELISE + DEATH_LORD
        self.assertEqual(len(files), 47)
        for relative in files:
            with self.subTest(model=relative.name):
                _, unmapped = recolor(decode_blueprint((ROOT / relative).read_bytes()).voxels)
                self.assertEqual(unmapped, [], relative)

    def test_the_recoloured_helm_is_robe_bone_and_spectral_green(self):
        helm = (ROOT / "work/death-lord/blueprints/equipment_helm_darkhood.blueprint").read_bytes()
        recolored, unmapped = recolor(decode_blueprint(helm).voxels)
        colours = {(v.r, v.g, v.b) for v in recolored}
        self.assertEqual(len(recolored), 2296)
        self.assertEqual(unmapped, [])
        self.assertEqual(colours - PALETTE, set())
        self.assertIn(SPECTRAL, colours)
        self.assertIn(BONE, colours)
        self.assertTrue(any(voxel.t in GLOWING_TYPES for voxel in recolored))


if __name__ == "__main__":
    unittest.main()
