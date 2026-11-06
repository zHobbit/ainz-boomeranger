"""Trove ``index.tfi`` + ``archiveN.tfa`` asset archives, decrypted.

There is no per-file cipher. The whole of each ``archiveN.tfa`` is a single zlib-deflate
stream (the game ships it ending on a sync flush with no final block or adler32, so we
inflate with ``zlib.decompressobj().decompress()``, which stops at end-of-input). An index
record's ``(archive, offset, size)`` address plaintext bytes inside that one decompressed
blob, and ``checksum`` is Trove's FNV-1a variant of the entry's plaintext, so extraction
self-verifies. The apparent per-file "keystreams" were just deflate output at raw file
offsets. Scheme and checksum semantics follow Better Trove Tools' prior art,
``core/src/game/archive.rs`` and ``core/src/game/hash.rs`` (AallynReed/BetterTroveTools).

CLI, from the repo root (the game install is read-only; ``-o`` points at a work dir)::

    py -m tools.tfa "C:/Program Files (x86)/Steam/steamapps/common/Trove/Games/Trove/Live/blueprints" list --match boomerang
    py -m tools.tfa ".../Live/prefabs/abilities/adventurer" extract boomerang.binfab -o work/game-assets
"""

import argparse
import sys
import zlib
from pathlib import Path

_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619
_MASK32 = 0xFFFFFFFF
_CONTENT_CACHE = {}


def _read_uleb(data, at):
    result = shift = 0
    while True:
        byte = data[at]
        at += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result & _MASK32, at
        shift += 7


def _sign_extend(byte):
    """A signed C ``char`` widened to uint32 (hash.rs::sign_extend)."""
    return (byte - 256 if byte >= 128 else byte) & _MASK32


def calculate_hash(data):
    """Trove's FNV-1a variant: 4-byte words little-endian, then a 1-3 byte tail
    big-endian with each byte sign-extended to 32 bits (hash.rs::calculate_hash)."""
    h = _FNV_OFFSET
    full = len(data) & ~3
    for i in range(0, full, 4):
        word = int.from_bytes(data[i : i + 4], "little")
        h = _FNV_PRIME * (h ^ word) & _MASK32
    tail = data[full:]
    if tail:
        value = _sign_extend(tail[0])
        for byte in tail[1:]:
            value = (value << 8) | _sign_extend(byte)
        h = _FNV_PRIME * (h ^ (value & _MASK32)) & _MASK32
    return h


def read_index(archive_dir):
    """``name -> (archive_index, offset, size, checksum)`` for every record in
    ``archive_dir/index.tfi``."""
    data = (Path(archive_dir) / "index.tfi").read_bytes()
    at = 0
    index = {}
    while at < len(data):
        length, at = _read_uleb(data, at)
        name = data[at : at + length].decode("utf-8", "replace")
        at += length
        archive_index, at = _read_uleb(data, at)
        offset, at = _read_uleb(data, at)
        size, at = _read_uleb(data, at)
        checksum, at = _read_uleb(data, at)
        index[name] = (archive_index, offset, size, checksum)
    return index


def _inflate(raw):
    """Everything a truncated zlib stream yields, tolerating the missing final block."""
    try:
        return zlib.decompressobj().decompress(raw)
    except zlib.error:
        return zlib.decompressobj(-15).decompress(raw[2:])


def archive_content(archive_dir, archive_index):
    """The decompressed bytes of ``archive_dir/archiveN.tfa``, cached per process."""
    path = Path(archive_dir) / f"archive{archive_index}.tfa"
    meta = path.stat()
    key = (str(path), meta.st_mtime_ns, meta.st_size)
    if key not in _CONTENT_CACHE:
        _CONTENT_CACHE[key] = _inflate(path.read_bytes())
    return _CONTENT_CACHE[key]


def extract(archive_dir, name):
    """The plaintext bytes of one archived file, checksum-verified."""
    archive_index, offset, size, checksum = read_index(archive_dir)[name]
    content = archive_content(archive_dir, archive_index)
    data = content[offset : offset + size]
    if len(data) != size:
        raise ValueError(f"{name}: archive{archive_index}.tfa holds only {len(content) - offset} of {size} bytes")
    found = calculate_hash(data)
    if found != checksum:
        raise ValueError(f"{name}: FNV-1a {found} does not match the index checksum {checksum}")
    return data


def _main(argv=None):
    parser = argparse.ArgumentParser(description="read Trove .tfa asset archives")
    parser.add_argument("archive_dir", type=Path, help="folder with index.tfi and archiveN.tfa")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--match", help="only names containing this text, case-insensitive")
    getting = commands.add_parser("extract")
    getting.add_argument("names", nargs="+")
    getting.add_argument("-o", type=Path, default=Path("work/game-assets"), help="output directory")
    args = parser.parse_args(argv)

    index = read_index(args.archive_dir)
    if args.command == "list":
        for name, record in sorted(index.items()):
            if not args.match or args.match.lower() in name.lower():
                print(*record, sep="\t", end="\t")
                print(name)
        return 0
    for name in args.names:
        if name not in index:
            print(f"not in {args.archive_dir}: {name}", file=sys.stderr)
            return 1
        target = args.o / Path(name).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(extract(args.archive_dir, name))
        print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
