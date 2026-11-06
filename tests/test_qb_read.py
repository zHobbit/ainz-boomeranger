import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.qb import read_qb

BOOMERANG_QB = ROOT / "reference" / "elise-boomerang.qb"


class ReadQbTests(unittest.TestCase):
    def test_reads_the_matrix_the_devtool_header_declares(self):
        matrices = read_qb(BOOMERANG_QB.read_bytes())

        self.assertEqual(len(matrices), 1)
        self.assertEqual(matrices[0].name, "kiwi")
        self.assertEqual(matrices[0].size, (43, 1, 43))
        self.assertEqual(matrices[0].pos, (-21, 0, -21))

    def test_reads_every_occupied_voxel_with_its_colour(self):
        matrix = read_qb(BOOMERANG_QB.read_bytes())[0]

        self.assertEqual(len(matrix.cells), 338)
        self.assertEqual(matrix.cells[(21, 0, 21)], (255, 0, 255))
        self.assertEqual(matrix.cells[(8, 0, 3)], (202, 202, 202))
        self.assertEqual(matrix.cells[(25, 0, 22)], (171, 171, 171))
        self.assertEqual(matrix.cells[(24, 0, 42)], (202, 202, 202))

    def test_skips_voxels_that_are_fully_transparent(self):
        matrix = read_qb(BOOMERANG_QB.read_bytes())[0]

        self.assertNotIn((0, 0, 0), matrix.cells)
        self.assertNotIn((42, 0, 0), matrix.cells)


if __name__ == "__main__":
    unittest.main()
