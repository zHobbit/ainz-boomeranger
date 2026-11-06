from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.tmod import calculate_hash, header_size_of, pack_tmod, padded_len, read_entries, read_tmod, write_tmod


class WriteTmodTests(unittest.TestCase):
    def setUp(self):
        self.properties, self.files = read_tmod(ROOT / "sources" / "death-lord" / "Death Lord.tmod")

    def test_reads_back_the_mod_that_was_written(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "Out.tmod"
            write_tmod(target, self.properties, self.files)
            self.assertEqual(read_tmod(target), (self.properties, self.files))

    def test_records_each_file_checksum_index_and_padded_offset(self):
        entries = list(read_entries(pack_tmod(self.properties, self.files)).values())
        offset = 0
        for path, data in self.files.items():
            entry = entries.pop(0)
            self.assertEqual(entry.path, path)
            self.assertEqual((entry.index, entry.offset, entry.size), (0, offset, len(data)))
            self.assertEqual(entry.checksum, calculate_hash(data), path)
            offset += padded_len(len(data))
        self.assertEqual(entries, [])

    def test_lays_the_body_out_as_stored_zlib_blocks(self):
        body = pack_tmod(self.properties, self.files)[header_size_of(pack_tmod(self.properties, self.files)):]
        blocks = sum(padded_len(len(data)) for data in self.files.values())
        self.assertTrue(body.startswith(b"\x78\x01"))
        self.assertTrue(body.endswith(b"\x00\x00\x00\xff\xff"))
        self.assertEqual(len(body), 2 + blocks + 5 * -(-blocks // 32768) + 5)

    def test_an_empty_file_still_gets_an_entry_with_the_empty_hash(self):
        entries = read_entries(pack_tmod({"title": "Empty"}, {"blueprints/empty.blueprint": b""}))
        self.assertEqual([(e.offset, e.size, e.checksum) for e in entries.values()], [(0, 0, calculate_hash(b""))])

    def test_rejects_a_path_too_long_for_the_header(self):
        with self.assertRaisesRegex(ValueError, "255"):
            pack_tmod({"title": "Long"}, {f"blueprints/{'x' * 246}.blueprint": b"kiwib"})

    def test_rejects_a_property_list_the_header_cannot_count(self):
        with self.assertRaisesRegex(ValueError, "65535"):
            pack_tmod({f"p{i}": "" for i in range(65536)}, {"a": b""})


if __name__ == "__main__":
    unittest.main()
