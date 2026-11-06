import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


FNV_OFFSET = 0x811C9DC5
FNV_PRIME = 0x01000193
_MASK = 0xFFFFFFFF


def _sign_extend(byte):
    """Trove reads the hash tail through a signed C char."""
    return (byte - 0x100 if byte & 0x80 else byte) & _MASK


def calculate_hash(data):
    """Trove's FNV-1a variant: whole 4-byte words little-endian, the 1-3 byte tail
    big-endian and sign-extended, every step truncated to 32 bits."""
    h = FNV_OFFSET
    for at in range(0, len(data) - len(data) % 4, 4):
        word = int.from_bytes(data[at:at + 4], "little")
        h = FNV_PRIME * (h ^ word) & _MASK
    tail = data[len(data) - len(data) % 4:]
    if tail:
        value = _sign_extend(tail[0])
        for byte in tail[1:]:
            value = (value << 8 & _MASK) | _sign_extend(byte)
        h = FNV_PRIME * (h ^ value) & _MASK
    return h


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, size):
        end = self.pos + size
        if end > len(self.data):
            raise ValueError("Unexpected end of TMOD data")
        result = self.data[self.pos:end]
        self.pos = end
        return result

    def u8(self):
        return self.read(1)[0]

    def u16(self):
        return struct.unpack("<H", self.read(2))[0]

    def u64(self):
        return struct.unpack("<Q", self.read(8))[0]

    def uleb(self):
        value = 0
        shift = 0
        while True:
            byte = self.u8()
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value
            shift += 7

    def string(self):
        return self.read(self.uleb()).decode("utf-8")


@dataclass
class ModEntry:
    path: str
    index: int
    offset: int
    size: int
    checksum: int


def _read_header(raw):
    reader = Reader(raw)
    header_size = reader.u64()
    version = reader.u16()
    property_count = reader.u16()
    properties = {reader.string(): reader.string() for _ in range(property_count)}
    entries = []
    while reader.pos < header_size:
        path_length = reader.u8()
        internal_path = reader.read(path_length).decode("utf-8")
        index, offset, size, checksum = reader.uleb(), reader.uleb(), reader.uleb(), reader.uleb()
        entries.append(ModEntry(internal_path, index, offset, size, checksum))
    if reader.pos != header_size:
        raise ValueError("Invalid TMOD header")
    return version, properties, entries


def _raw(source):
    return source if isinstance(source, bytes) else Path(source).read_bytes()


def header_size_of(raw):
    return struct.unpack_from("<Q", raw, 0)[0]


def decompress_body(raw):
    return zlib.decompressobj().decompress(raw[header_size_of(raw):])


def read_entries(path):
    """The header's file table, keyed by internal path in the order it was written."""
    return {entry.path: entry for entry in _read_header(_raw(path))[2]}


def read_tmod(path):
    raw = _raw(path)
    _, properties, entries = _read_header(raw)
    body = decompress_body(raw)
    files = {}
    for entry in entries:
        data = body[entry.offset:entry.offset + entry.size]
        if len(data) != entry.size:
            raise ValueError("Truncated TMOD file data")
        files[entry.path] = data
    return properties, files


def uleb_bytes(value):
    out = bytearray()
    while value >= 0x80:
        out.append(value & 0x7F | 0x80)
        value >>= 7
    out.append(value & 0x7F)
    return bytes(out)


def padded_len(size):
    return -(-size // 4) * 4


def compress_stored(body):
    """A zlib stream of stored blocks: what Trove's own writer and BTT both emit, and
    what the game's forward-only inflater is built for."""
    out = bytearray(b"\x78\x01")
    for at in range(0, len(body), 32768):
        chunk = body[at:at + 32768]
        out.append(0)
        out.extend(struct.pack("<HH", len(chunk), len(chunk) ^ 0xFFFF))
        out.extend(chunk)
    out.extend(b"\x00\x00\x00\xff\xff")
    return bytes(out)


def pack_tmod(properties, files):
    items = list(properties.items())
    if len(items) > 0xFFFF:
        raise ValueError("'H' format requires 0 <= number <= 65535")
    header = bytearray(struct.pack("<QHH", 0, 1, len(items)))
    for name, value in items:
        for text in (name, value):
            encoded = text.encode("utf-8")
            header.extend(uleb_bytes(len(encoded)))
            header.extend(encoded)

    body = bytearray()
    offset = 0
    for internal_path, data in files.items():
        encoded = internal_path.encode("utf-8")
        if len(encoded) > 255:
            raise ValueError(f"Mod internal path is too long for the .tmod format (>255 bytes): {internal_path}")
        header.append(len(encoded))
        header.extend(encoded)
        header.extend(uleb_bytes(0))
        header.extend(uleb_bytes(0 if not data else offset))
        header.extend(uleb_bytes(len(data)))
        header.extend(uleb_bytes(calculate_hash(data)))
        body.extend(data)
        body.extend(b"\0" * (padded_len(len(data)) - len(data)))
        offset += padded_len(len(data))

    header[:8] = struct.pack("<Q", len(header))
    return bytes(header) + compress_stored(body)


def write_tmod(path, properties, files):
    Path(path).write_bytes(pack_tmod(properties, files))


def extract_tmod(mod_path, destination):
    _, files = read_tmod(mod_path)
    root = Path(destination).resolve()
    extracted = []
    for internal_path, data in files.items():
        normalized = internal_path.replace("\\", "/")
        target = (root / normalized).resolve()
        if not target.is_relative_to(root):
            raise ValueError("Unsafe TMOD path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        extracted.append(Path(normalized))
    return extracted
