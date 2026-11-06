from pathlib import Path
import struct
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.blueprint import Voxel, blueprint_body, decode_blueprint, encode_blueprint


def deflate(body):
    folder = zlib.compressobj(9)
    return folder.compress(body) + folder.flush(zlib.Z_SYNC_FLUSH)


class V5CodecTests(unittest.TestCase):
    # 2 voxels in a 2x3x2 box at (-1, 0, -1): cell indices x + z * 2 + y * 4, so the
    # scan order is 0 then 11.
    BODY = (
        struct.pack("<8i", -1, 0, -1, 2, 3, 2, 2, 0)
        + struct.pack("<i", 11)
        + struct.pack("<2H", 21, 21)
        + struct.pack("<2I", 0x00C80A1E, 0x00C80A1E)
        + b"\0\0\0\0"
    )
    VOXELS = [Voxel(0, 0, 0, 200, 10, 30, 0, 21), Voxel(1, 2, 1, 200, 10, 30, 0, 21)]

    def test_encodes_the_hand_derived_body(self):
        self.assertEqual(blueprint_body(encode_blueprint(self.VOXELS, (-1, 0, -1))), self.BODY)

    def test_decodes_the_hand_derived_body(self):
        decoded = decode_blueprint(b"kiwib\x05\0\0\0" + deflate(self.BODY))
        self.assertEqual(decoded.voxels, self.VOXELS)
        self.assertEqual((decoded.pos, decoded.size, decoded.entity_blob), ((-1, 0, -1), (2, 3, 2), b"\0\0\0\0"))

    def test_the_attachment_point_is_the_negative_of_the_position(self):
        self.assertEqual(decode_blueprint(b"kiwib\x05\0\0\0" + deflate(self.BODY)).attachment, (1, 0, 1))

    def test_an_empty_blueprint_carries_zero_bounds_and_no_voxels(self):
        decoded = decode_blueprint(Path(ROOT / "work/death-lord/blueprints/c_p_tombraiser_lvl3_chest.blueprint").read_bytes())
        self.assertEqual((decoded.voxels, decoded.pos, decoded.size), ([], (0, 0, 0), (0, 0, 0)))
        self.assertEqual(blueprint_body(encode_blueprint([], (0, 0, 0))), b"\0" * 32)

    def test_round_trips_every_v5_blueprint_in_the_sources(self):
        files = sorted((ROOT / "work").glob("*/blueprints/*.blueprint"))
        self.assertGreaterEqual(len(files), 158)   # the corpus grows as vanilla parts are extracted
        for source in files:
            raw = source.read_bytes()
            if raw[5] != 5:
                continue  # v3/v4 sources are read-only; they ship re-encoded as v5
            with self.subTest(blueprint=str(source.relative_to(ROOT))):
                decoded = decode_blueprint(raw)
                self.assertEqual(blueprint_body(encode_blueprint(decoded.voxels, decoded.pos, decoded.entity_blob)), blueprint_body(raw), source.name)


if __name__ == "__main__":
    unittest.main()
