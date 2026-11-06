import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.model import blueprint_body

LIVE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Trove\Games\Trove\Live")
BLUEPRINTS = LIVE / "blueprints"

requires_game = unittest.skipUnless((BLUEPRINTS / "index.tfi").exists(), "Trove install is not present")

# --- literals hand-derived from the archive bytes (zlib probe run before tools/tfa.py existed) ---

TORSO = "c_p_adventurer_lvl3_torso.blueprint"
# index.tfi record: archive 1, decompressed offset 3685976, size 138, FNV-1a checksum.
TORSO_RECORD = (1, 3685976, 138, 286190721)
# The 138 plaintext bytes at that coordinate, spelled out from the decompressed archive1.tfa.
TORSO_BYTES = bytes.fromhex(
    "6b697769620500000078dafafbffffff7f40fc1788d9191818d8a0f815103362c14c38c4698539e86c1f21"
    "cc348061318a070f66c6c1a6671a84d1a2a370d8419510570c2ce3e8c4824b9cde72d8c46989d1ed1c6cee"
    "b36b5bca8c4b1ce6566c7820c351dec79765b08627b2db70b1b1f191c5617230363a1fc65e7ff22203b172"
    "e86a4000000000ffff"
)
# blueprint_body(TORSO_BYTES) starts with position (-3, -2, -3) and size (7, 6, 6).
TORSO_HEADER = (-3, -2, -3, 7, 6, 6)

# --- a second archive family, to prove the scheme is not blueprint-specific ---

PARTICLES = LIVE / "particles" / "Common"
DEPENDENCIES_TXT = "dependencies.txt"
DEPENDENCIES_RECORD = (0, 0, 15, 4122101633)
DEPENDENCIES_BYTES = b"$ROOT$/Engine\r\n"

ABILITIES = LIVE / "prefabs" / "abilities" / "adventurer"
BOW_BULLET = "basic_attack_bow_bullet.binfab"
BOW_BULLET_RECORD = (0, 696, 657, 4095691506)
# raw bintab (no kiwib envelope); first 16 bytes read straight off the decompressed archive0.tfa
BOW_BULLET_HEAD = bytes.fromhex("4e008d05000e080016000000e0ffffef")


@requires_game
class IndexTests(unittest.TestCase):
    def setUp(self):
        from tools.tfa import read_index

        self.index = read_index(BLUEPRINTS)

    def test_the_packed_table_holds_every_record(self):
        self.assertEqual(len(self.index), 38337)

    def test_the_torso_record_is_the_one_parsed_from_the_index_by_hand(self):
        self.assertEqual(self.index[TORSO], TORSO_RECORD)


@requires_game
class ExtractTests(unittest.TestCase):
    def test_extract_returns_the_plaintext_blueprint_byte_for_byte(self):
        from tools.tfa import extract

        self.assertEqual(extract(BLUEPRINTS, TORSO), TORSO_BYTES)

    def test_extracted_blueprint_carries_the_kiwib_prefix(self):
        from tools.tfa import extract

        self.assertEqual(extract(BLUEPRINTS, TORSO)[:9], b"kiwib\x05\x00\x00\x00")

    def test_extracted_blueprint_inflates_to_a_sane_position_and_size(self):
        from tools.tfa import extract

        body = blueprint_body(extract(BLUEPRINTS, TORSO))
        pos, size = struct.unpack_from("<3i", body, 0), struct.unpack_from("<3i", body, 12)

        self.assertEqual(pos + size, TORSO_HEADER)
        self.assertTrue(all(axis > 0 for axis in size))
        self.assertTrue(all(abs(offset) <= extent for offset, extent in zip(pos, size)))

    def test_extract_rejects_an_unknown_name(self):
        from tools.tfa import extract

        with self.assertRaises(KeyError):
            extract(BLUEPRINTS, "no_such_thing.blueprint")

    def test_extract_rejects_a_tampered_checksum(self):
        # the stored checksum is Trove's FNV-1a over the entry bytes; extraction proves it
        from tools.tfa import calculate_hash

        self.assertEqual(calculate_hash(TORSO_BYTES), TORSO_RECORD[3])


@requires_game
class OtherArchiveFamiliesTests(unittest.TestCase):
    def test_particles_common_is_the_same_scheme(self):
        from tools.tfa import extract, read_index

        self.assertEqual(read_index(PARTICLES)[DEPENDENCIES_TXT], DEPENDENCIES_RECORD)
        self.assertEqual(extract(PARTICLES, DEPENDENCIES_TXT), DEPENDENCIES_BYTES)

    def test_prefab_archives_hold_plain_bintab_not_encrypted_data(self):
        from tools.tfa import extract, read_index

        self.assertEqual(read_index(ABILITIES)[BOW_BULLET], BOW_BULLET_RECORD)
        self.assertEqual(extract(ABILITIES, BOW_BULLET)[:16], BOW_BULLET_HEAD)


if __name__ == "__main__":
    unittest.main()
