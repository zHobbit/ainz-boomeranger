import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.qb import Matrix, read_qb, write_qb

BOOMERANG_QB = ROOT / "reference" / "elise-boomerang.qb"

_HEADER = (
    b"\x01\x01\x00\x00"  # version 257
    b"\x00\x00\x00\x00"  # colour_format 0: bytes are already RGB
    b"\x01\x00\x00\x00"  # z_orientation 1: no vertical flip
    b"\x00\x00\x00\x00"  # compression 0: raw 4-byte cells
    b"\x00\x00\x00\x00"
    b"\x01\x00\x00\x00"  # one matrix
)
_MATRIX_HEAD = (
    b"\x04kiwi"  # name length, then the name
    + b"\x02\x00\x00\x00"  # size x
    + b"\x01\x00\x00\x00"  # size y
    + b"\x02\x00\x00\x00"  # size z
    + b"\x00\x00\x00\x00" * 3  # pos
)


class WriteQbTests(unittest.TestCase):
    def test_writes_cells_in_z_then_y_then_x_scan_order(self):
        matrix = Matrix(
            name="kiwi",
            size=(2, 1, 2),
            pos=(0, 0, 0),
            cells={(0, 0, 0): (1, 2, 3), (1, 0, 0): (4, 5, 6), (0, 0, 1): (7, 8, 9)},
        )

        self.assertEqual(
            write_qb(matrix),
            _HEADER
            + _MATRIX_HEAD
            + b"\x01\x02\x03\xff"
            + b"\x04\x05\x06\xff"
            + b"\x07\x08\x09\xff"
            + b"\x00\x00\x00\x00",
        )

    def test_writes_a_file_that_reads_back_identically(self):
        original = read_qb(BOOMERANG_QB.read_bytes())[0]

        rewritten = read_qb(write_qb(original))[0]

        self.assertEqual(rewritten.name, original.name)
        self.assertEqual(rewritten.size, original.size)
        self.assertEqual(rewritten.pos, original.pos)
        self.assertEqual(rewritten.cells, original.cells)

    def test_rejects_a_matrix_wider_than_a_byte_can_name(self):
        with self.assertRaises(ValueError):
            write_qb(Matrix(name="k" * 256, size=(1, 1, 1), pos=(0, 0, 0), cells={(0, 0, 0): (1, 2, 3)}))


if __name__ == "__main__":
    unittest.main()
