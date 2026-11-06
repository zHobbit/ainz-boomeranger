from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.vfx import (
    EFFECTS,
    GREEN,
    LUMA,
    brightness_gain,
    VIOLET,
    colour_curves,
    format_float,
    keys,
    mod_path,
    objects,
    recolour,
    themed_effects,
    tone,
)

SOURCE = ROOT / "work/game-assets/particles"
PROJECTILE = (SOURCE / "character_pc_adventurer_ability_boomerang_projectile_01.pkfx").read_bytes().decode("ascii")
FUSE = (SOURCE / "character_pc_adventurer_ability_bomb_fuse_01.pkfx").read_bytes().decode("ascii")


def bodies(text):
    return {local: text[start:end] for _, local, start, end in objects(text)}


class FormatTests(unittest.TestCase):
    def test_numbers_are_spelled_the_way_the_editor_writes_them(self):
        for spelled in ("3.6297047e-001", "1.1760454e+001", "-2.5988981e-001", "0.0000000e+000"):
            self.assertEqual(format_float(float(spelled)), spelled)

    def test_negative_zero_is_written_as_zero(self):
        self.assertEqual(format_float(-0.0), "0.0000000e+000")


class CurveDiscoveryTests(unittest.TestCase):
    def test_finds_the_colour_field_curves_and_not_the_size_or_rotation_ones(self):
        curves = colour_curves(PROJECTILE)
        self.assertEqual(curves, {"$LOCAL$/CParticleSamplerCurve_F965E42C": 4,
                                  **{local: 4 for local in curves if local != "$LOCAL$/CParticleSamplerCurve_F965E42C"}})
        self.assertEqual(len(curves), 3)
        self.assertNotIn("$LOCAL$/CParticleSamplerCurve_40C9073A", curves)  # Size
        self.assertNotIn("$LOCAL$/CParticleSamplerCurve_456F970D", curves)  # rotation speed

    def test_finds_named_colour_samplers_the_scripts_sample(self):
        curves = colour_curves(FUSE)
        self.assertEqual(list(curves.values()), [3])
        self.assertIn('SamplerName = "ColorCurveGlobal"', bodies(FUSE)[next(iter(curves))])

    def test_every_shipped_effect_has_colour_to_change(self):
        for stem in EFFECTS:
            with self.subTest(stem):
                self.assertTrue(colour_curves((SOURCE / f"{stem}.pkfx").read_bytes().decode("ascii")))


class ToneTests(unittest.TestCase):
    def test_fire_turns_violet_and_cool_glows_turn_green(self):
        self.assertEqual(tone((1.0, 0.5, 0.1)), VIOLET)
        self.assertEqual(tone((0.9, 0.1, 0.1)), VIOLET)
        self.assertEqual(tone((0.2, 0.9, 0.3)), GREEN)
        self.assertEqual(tone((0.3, 0.6, 1.0)), GREEN)
        self.assertEqual(tone((0.36, 0.145, 0.68)), VIOLET)  # the boomerang's own purple arcs

    def test_greys_go_by_brightness(self):
        self.assertEqual(tone((0.95, 0.95, 0.95)), GREEN)
        self.assertEqual(tone((0.1, 0.1, 0.1)), VIOLET)


class RecolourTests(unittest.TestCase):
    def test_only_numbers_inside_colour_curves_change(self):
        out, _ = recolour(PROJECTILE)
        before, after = PROJECTILE.splitlines(keepends=True), out.splitlines(keepends=True)
        self.assertEqual(len(before), len(after))
        curves = colour_curves(PROJECTILE)
        allowed = "".join(body for local, body in bodies(PROJECTILE).items() if local in curves)
        for old, new in zip(before, after):
            if old != new:
                self.assertRegex(new, r"^\t\t-?\d\.\d{7}e[-+]\d{3},\r\n$")
                self.assertIn(old, allowed)
        self.assertEqual({local: body for local, body in bodies(out).items() if local not in curves},
                         {local: body for local, body in bodies(PROJECTILE).items() if local not in curves})

    def test_alpha_is_kept_and_rgb_becomes_luminance_times_the_tint(self):
        out, chosen = recolour(PROJECTILE)
        for local, channels in colour_curves(PROJECTILE).items():
            (colour,) = chosen[local]
            old_keys = keys(bodies(PROJECTILE)[local], channels)
            new_keys = keys(bodies(out)[local], channels)
            gain = brightness_gain([key[:3] for key in old_keys])
            for old, new in zip(old_keys, new_keys):
                luma = sum(w * c for w, c in zip(LUMA, old[:3]))
                for got, want in zip(new[:3], (gain * luma * c for c in colour)):
                    self.assertAlmostEqual(got, want, places=6)
                self.assertEqual(new[3:], old[3:])

    def test_a_curve_keeps_its_brightest_channel(self):
        out, _ = recolour(PROJECTILE)
        for local, channels in colour_curves(PROJECTILE).items():
            peak = lambda text: max(max(key[:3]) for key in keys(bodies(text)[local], channels))
            self.assertAlmostEqual(peak(out), peak(PROJECTILE), places=6)

    def test_hermite_slopes_get_the_same_linear_map_as_the_keys(self):
        local = "$LOCAL$/CParticleSamplerCurve_F965E42C"
        out, chosen = recolour(PROJECTILE)
        (colour,) = chosen[local]
        gain = brightness_gain([key[:3] for key in keys(bodies(PROJECTILE)[local], 4)])
        slopes = lambda body: [float(n) for n in re.findall(r"^\t\t(\S+),",
                               body.split("FloatTangents")[1].split("};")[0], re.M)]
        old, new = slopes(bodies(PROJECTILE)[local]), slopes(bodies(out)[local])
        self.assertEqual(len(old), 40)
        for at in range(0, 40, 4):
            luma = sum(w * c for w, c in zip(LUMA, old[at:at + 3]))
            for got, want in zip(new[at:at + 3], (gain * luma * c for c in colour)):
                self.assertAlmostEqual(got, want, places=6)
            self.assertEqual(new[at + 3], old[at + 3])

    def test_a_linear_ramp_from_orange_to_green_becomes_violet_to_green(self):
        _, chosen = recolour(FUSE)
        self.assertEqual(list(chosen.values()), [{VIOLET, GREEN}])

    def test_recolouring_twice_is_stable_in_hue(self):
        once, chosen = recolour(PROJECTILE)
        _, again = recolour(once)
        self.assertEqual(chosen, again)


class ShippingTests(unittest.TestCase):
    def test_effects_ship_where_mods_override_game_particles(self):
        self.assertEqual(mod_path("abc"), "particles/vfx/particles/abc.pkfx")

    def test_every_effect_is_shipped_as_ascii_with_crlf_kept(self):
        files = themed_effects(SOURCE)
        self.assertEqual(sorted(files), sorted(mod_path(stem) for stem in EFFECTS))
        self.assertEqual(len(files), 21)
        for path, data in files.items():
            with self.subTest(path):
                data.decode("ascii")
                self.assertNotIn(b"\r\r", data)
                self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))


if __name__ == "__main__":
    unittest.main()
