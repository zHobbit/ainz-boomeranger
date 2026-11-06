from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.tmod import calculate_hash, read_entries, read_tmod


class CalculateHashTests(unittest.TestCase):
    def test_matches_trove_known_answers(self):
        cases = {
            b"": 2166136261,
            b"abcd": 3967774508,
            b"abcde\xff": 2254699561,
            b"prefabs/items/test.binfab": 4101874600,
            bytes([0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF]): 2948466838,
        }
        for data, expected in cases.items():
            with self.subTest(len=len(data)):
                self.assertEqual(calculate_hash(data), expected)

    def test_every_file_in_the_source_mods_carries_this_checksum(self):
        for source in (ROOT / "sources" / "death-lord" / "Death Lord.tmod", ROOT / "sources" / "elise" / "Elise.tmod"):
            with self.subTest(mod=source.name):
                _, files = read_tmod(source)
                for name, entry in read_entries(source).items():
                    self.assertEqual(entry.checksum, calculate_hash(files[name]), name)


if __name__ == "__main__":
    unittest.main()
