from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.blueprint import bounding_size, decode_blueprint
from tools.build import MANIFEST, MODELS, anchor, body_parts, build_mod, effect_paths, head_parts, shipped_paths
from tools.tmod import read_tmod
from tools.theme import PALETTE
from tools.ainz_parts import GEMS, GOLD_DARK


class AnchorTests(unittest.TestCase):
    def test_the_donor_lands_where_the_recipient_bone_puts_it(self):
        """Death Lord put its robe on the Tomb Raiser's core bone at (-9, -4, -6). Re-anchoring
        that same robe to the Boomeranger's torso bone reproduces the author's own numbers,
        which is the only ground truth available without running the game."""
        donor = MODELS["death-lord"] / "c_p_tombraiser_lvl3_core.blueprint"
        self.assertEqual(anchor(decode_blueprint(donor.read_bytes()), "torso"), (-9, -4, -6))

    def test_a_part_that_stays_on_its_own_bone_keeps_its_position(self):
        donor = MODELS["elise"] / "c_p_adventurer_lvl3_hips.blueprint"
        self.assertEqual(anchor(decode_blueprint(donor.read_bytes()), None), (-4, -7, -3))


class ManifestTests(unittest.TestCase):
    def test_the_manifest_ships_every_bone_the_boomeranger_wears(self):
        bones = {"torso", "hips", "pack", "hand_l", "hand_r", "shoulder_l", "shoulder_r",
                 "thigh_l", "thigh_r", "shin_l", "shin_r", "foot_l", "foot_r", "ui"}
        self.assertEqual(shipped_paths(), {
            f"blueprints/c_p_adventurer_lvl3_{bone}.blueprint" for bone in bones
        } | {
            f"blueprints/c_p_adventurer_basic_{skill}.blueprint" for skill in ("boomerang", "bomb", "bawkbomb", "urn")
        } | {
            "blueprints/equipment_helm_darkhood.blueprint",
            "blueprints/equipment_face_mask_halfskull[destral].blueprint",
            "blueprints/equipment_weapon_1h_sword_001.blueprint",
        } | {
            f"blueprints/c_c_quchik_{part}.blueprint" for part in
            ("head", "beak", "crest", "l_eye", "r_eye", "l_wing", "r_wing", "l_foot", "r_foot")
        })

    def test_no_donor_needs_a_colour_nobody_reviewed(self):
        for part in MANIFEST:
            with self.subTest(model=part.donor.name):
                _, unmapped = part.recolor()
                self.assertEqual(unmapped, [], part.donor.name)


class FigureTests(unittest.TestCase):
    def test_the_body_figure_draws_the_worn_robe_only(self):
        _, files = build_mod()
        labels = [label for label, _, _ in body_parts(files)]
        self.assertEqual(set(labels), {"lvl3_" + bone for bone in
                                      ("torso", "hips", "pack", "hand_l", "hand_r", "shoulder_l", "shoulder_r",
                                       "thigh_l", "thigh_r", "shin_l", "shin_r", "foot_l", "foot_r")})

    def test_the_head_figure_hangs_the_hood_on_the_games_own_head_frame(self):
        """Equipment and hair are both authored against the generic head bone, so the
        preview can place them by the positions their authors gave them."""
        _, files = build_mod()
        origins = {label: origin for label, _, origin in head_parts(files)}
        self.assertEqual(set(origins), {"hair", "equipment_helm_darkhood",
                                        "equipment_face_mask_halfskull[destral]"})
        self.assertEqual(origins["equipment_helm_darkhood"], (-25, -8, -13))
        self.assertEqual(origins["hair"], (-5, -6, -6))

    def test_the_hood_covers_where_the_hair_is(self):
        _, files = build_mod()
        parts = {label: (voxels, origin) for label, voxels, origin in head_parts(files)}
        helm_voxels, helm_origin = parts["equipment_helm_darkhood"]
        hair_voxels, hair_origin = parts["hair"]
        hair_floor, hair_top = hair_origin[1], hair_origin[1] + bounding_size(hair_voxels)[1] - 1
        helm_floor, helm_ceiling = helm_origin[1], helm_origin[1] + bounding_size(helm_voxels)[1] - 1
        self.assertLessEqual(helm_floor, hair_floor)
        self.assertGreaterEqual(helm_ceiling, hair_top)


class BuildTests(unittest.TestCase):
    def test_the_mod_reads_back_with_every_model_intact(self):
        properties, files = build_mod()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Ainz Boomeranger.tmod"
            from tools.tmod import write_tmod
            write_tmod(target, properties, files)
            self.assertEqual(read_tmod(target), (properties, files))
        self.assertEqual(set(files), shipped_paths() | effect_paths() | {"ui/ainz.png"})
        self.assertEqual(properties["title"], "Ainz Boomeranger")
        self.assertEqual(len(MANIFEST), 18)
        self.assertEqual(len(effect_paths()), 21)
        self.assertEqual(len(files), 30 + 21 + 1)

    def test_every_shipped_model_is_only_palette_colours(self):
        _, files = build_mod()
        for path, data in files.items():
            if not path.endswith(".blueprint"):
                continue
            with self.subTest(model=path):
                decoded = decode_blueprint(data)
                colours = {(v.r, v.g, v.b) for v in decoded.voxels}
                if "c_c_quchik_" in path:  # the undead chicken's own bone shades stay
                    colours = {(v.r, v.g, v.b) for v in decoded.voxels if v.t in (55, 56)}
                if "weapon" in path:  # the staff's seven jewels
                    colours -= set(GEMS) | {GOLD_DARK}
                self.assertTrue(colours <= PALETTE or not decoded.voxels, path)


if __name__ == "__main__":
    unittest.main()
