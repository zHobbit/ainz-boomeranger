import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.model import blueprint_body, blueprint_to_maps, maps_to_blueprint, read_maps
from tools.qb import Matrix, write_qb

DEVTOOL = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Trove\Games\Trove\Live\devtool.bat")
REFERENCE_QBS = ROOT / "reference"
ELISE_BOOMERANG = ROOT / "work" / "elise" / "blueprints" / "c_p_adventurer_basic_boomerang.blueprint"
# This helm's attachment marker sits 12 voxels under the model's floor. The devtool drops
# that offset when it compiles, so the maps have to put it back.
HELM_DARKHOOD = ROOT / "work" / "death-lord" / "blueprints" / "equipment_helm_darkhood.blueprint"

requires_devtool = unittest.skipUnless(DEVTOOL.exists(), "Trove devtool is not installed")


class ReadMapsTests(unittest.TestCase):
    def test_reads_the_four_material_maps_that_share_one_grid(self):
        maps = read_maps(REFERENCE_QBS, "elise-boomerang")

        self.assertEqual([maps[key].size for key in ("base", "alpha", "specular", "style")], [(43, 1, 43)] * 4)
        self.assertEqual([maps[key].pos for key in ("base", "alpha", "specular", "style")], [(-21, 0, -21)] * 4)
        self.assertEqual([len(maps[key].cells) for key in ("base", "alpha", "specular", "style")], [338] * 4)
        self.assertEqual(maps["base"].cells[(21, 0, 21)], (255, 0, 255))

    def test_rejects_a_material_map_whose_grid_is_not_the_model_grid(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for suffix in ("", "_a", "_s"):
                shutil.copy(REFERENCE_QBS / f"elise-boomerang{suffix}.qb", directory / f"model{suffix}.qb")
            write = Matrix(name="kiwi", size=(9, 9, 9), pos=(0, 0, 0), cells={(0, 0, 0): (1, 1, 1)})
            (directory / "model_t.qb").write_bytes(write_qb(write))

            with self.assertRaisesRegex(ValueError, "style"):
                read_maps(directory, "model")


class DevtoolCompileTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, True)

    @requires_devtool
    def test_maps_written_here_compile_back_to_the_original_model(self):
        for source in (ELISE_BOOMERANG, HELM_DARKHOOD):
            with self.subTest(source.stem):
                maps = blueprint_to_maps(source, self.temp, source.stem)
                rebuilt = maps_to_blueprint(self.temp, source.stem, maps)

                self.assertEqual(blueprint_body(rebuilt), blueprint_body(source.read_bytes()))


if __name__ == "__main__":
    unittest.main()
