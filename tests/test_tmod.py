import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.tmod import extract_tmod, read_tmod


class TmodTests(unittest.TestCase):
    def test_reads_death_lord_assets_without_corruption(self):
        properties, files = read_tmod(ROOT / "sources" / "death-lord" / "Death Lord.tmod")

        self.assertEqual(properties["title"], "Death Lord")
        self.assertEqual(len(files), 117)
        digest = hashlib.sha256(files["blueprints/c_p_tombraiser_lvl3_chest.blueprint"]).hexdigest()
        self.assertEqual(digest, "b3a1fc95309b5df2ad1bc990e13e7fba8ca8265e24609c640d4a02a37392972c")

    def test_reads_unicode_tmod_and_boomerang_without_corruption(self):
        properties, files = read_tmod(ROOT / "sources" / "elise" / "Elise.tmod")

        self.assertEqual(properties["title"], "Elise, Queen of Spiders [Mod from China]")
        self.assertEqual(len(files), 38)
        digest = hashlib.sha256(files["blueprints/c_p_adventurer_basic_boomerang.blueprint"]).hexdigest()
        self.assertEqual(digest, "6646ba87f18c7f478bd61cd0d76b9d850e57f9880133870eeb701848e1f8ad38")

    def test_extracts_all_internal_paths_under_destination(self):
        source = ROOT / "sources" / "death-lord" / "Death Lord.tmod"
        chest_sample = ROOT / "reference" / "deathlord-chest-api.blueprint"
        preview_sample = ROOT / "reference" / "deathlord-api.png"

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)
            extracted = extract_tmod(source, destination)

            self.assertEqual(len(extracted), 117)
            chest = destination / "blueprints/c_p_tombraiser_lvl3_chest.blueprint"
            preview = destination / "ui/deathlord.png"
            self.assertEqual(chest.read_bytes(), chest_sample.read_bytes())
            self.assertEqual(preview.read_bytes(), preview_sample.read_bytes())


if __name__ == "__main__":
    unittest.main()
