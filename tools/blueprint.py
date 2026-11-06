"""Trove's `.blueprint` (kiwib) v5 container, both ways.

The body after the 9-byte header is one zlib stream: three i32 position, three i32 size,
voxel count, first cell index, then the count-1 cell deltas, the 16-bit material types
and the packed colours (`w << 24 | r << 16 | g << 8 | b`). Cells scan x, then z, then y.

Older models (the game's starter sword, the vanilla chickens) are v3/v4 and are only read:
an uleb voxel count, then per voxel zigzag-uleb x, y, z, a u16 type and B, G, R, w bytes,
then the entity section. The raw coordinates are already in the attachment frame: the
vanilla chicken's v3 beak, crest and feet have their minimum corner exactly at the ``pos``
of the undead skin's v5 remake of the same part. So ``pos`` is that minimum corner (not a
centred box, as BTT assumes), and a re-encode writes them as v5 at the same place.
"""

import struct
import zlib
from dataclasses import dataclass

MAGIC = b"kiwib"
VERSION = 5
_HEADER = struct.Struct("<8i")
_EMPTY_BLOB = b"\0\0\0\0"


@dataclass(frozen=True)
class Voxel:
    x: int
    y: int
    z: int
    r: int
    g: int
    b: int
    w: int
    t: int


@dataclass(frozen=True)
class Decoded:
    voxels: list
    pos: tuple
    size: tuple
    entity_blob: bytes

    @property
    def attachment(self):
        """Where the model grips a hand or sits on a head: world zero in its own frame."""
        return tuple(-coordinate for coordinate in self.pos)


def blueprint_body(data):
    if data[:len(MAGIC)] != MAGIC:
        raise ValueError("not a kiwib blueprint")
    version = struct.unpack_from("<I", data, 5)[0]
    if version != VERSION:
        raise ValueError(f"unsupported kiwib blueprint version {version}, only v5 is read here")
    return zlib.decompressobj().decompress(data[len(MAGIC) + 4:])


def wrap_blueprint(body):
    folder = zlib.compressobj(9)
    stream = folder.compress(body) + folder.flush(zlib.Z_SYNC_FLUSH)
    return MAGIC + struct.pack("<I", VERSION) + stream


def bounding_size(voxels):
    if not voxels:
        return (0, 0, 0)
    return (max(v.x for v in voxels) + 1, max(v.y for v in voxels) + 1, max(v.z for v in voxels) + 1)


def encode_blueprint(voxels, pos, entity_blob=_EMPTY_BLOB):
    size = bounding_size(voxels)
    if not voxels:
        return wrap_blueprint(_HEADER.pack(*pos, 0, 0, 0, 0, 0))

    scan_x, scan_z = size[0], size[0] * size[2]
    order = {}
    for voxel in voxels:
        order[voxel.x + voxel.z * scan_x + voxel.y * scan_z] = voxel
    cells = sorted(order)

    payload = bytearray(_HEADER.pack(*pos, *size, len(cells), cells[0]))
    payload += struct.pack(f"<{len(cells) - 1}i", *[b - a for a, b in zip(cells, cells[1:])])
    payload += b"".join(struct.pack("<H", order[cell].t) for cell in cells)
    payload += b"".join(struct.pack("<I", _colour(order[cell])) for cell in cells)
    payload += entity_blob or _EMPTY_BLOB
    return wrap_blueprint(bytes(payload))


def _colour(voxel):
    return voxel.w << 24 | voxel.r << 16 | voxel.g << 8 | voxel.b


def blueprint_version(data):
    if data[:len(MAGIC)] != MAGIC:
        raise ValueError("not a kiwib blueprint")
    return struct.unpack_from("<I", data, 5)[0]


def _uleb(data, at):
    value = shift = 0
    while True:
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, at
        shift += 7


def _decode_legacy(data):
    count, at = _uleb(data, len(MAGIC) + 4)
    raw = []
    for _ in range(count):
        coordinates = []
        for _ in range(3):
            zigzag, at = _uleb(data, at)
            coordinates.append((zigzag >> 1) ^ -(zigzag & 1))
        if at + 6 > len(data):
            raise ValueError("v3/v4 voxel record is truncated")
        t, b, g, r, w = struct.unpack_from("<H4B", data, at)
        raw.append((coordinates, r, g, b, w, t))
        at += 6
    if not raw:
        return Decoded([], (0, 0, 0), (0, 0, 0), data[at:])
    low = [min(coordinates[axis] for coordinates, *_ in raw) for axis in range(3)]
    voxels = [Voxel(c[0] - low[0], c[1] - low[1], c[2] - low[2], r, g, b, w, t) for c, r, g, b, w, t in raw]
    return Decoded(voxels, tuple(low), bounding_size(voxels), data[at:])


def decode_blueprint(data):
    if blueprint_version(data) in (3, 4):
        return _decode_legacy(data)
    body = blueprint_body(data)
    if len(body) < _HEADER.size:
        raise ValueError("blueprint body is shorter than its header")
    pos, size, count, start = _split_header(_HEADER.unpack_from(body, 0))
    if count == 0:
        return Decoded([], pos, size, body[_HEADER.size:])

    scan_x, scan_z = size[0], size[0] * size[2]
    deltas_at, types_at = _HEADER.size, _HEADER.size + 4 * (count - 1)
    colours_at = types_at + 2 * count
    needed = colours_at + 4 * count
    if len(body) < needed:
        raise ValueError(f"blueprint declares {count} voxels but its body holds {len(body)} of {needed} bytes")

    voxels = []
    cell = start
    for index in range(count):
        if index:
            cell += struct.unpack_from("<i", body, deltas_at + 4 * (index - 1))[0]
        colour = struct.unpack_from("<I", body, colours_at + 4 * index)[0]
        within = cell % scan_z
        voxels.append(
            Voxel(
                x=within % scan_x,
                y=cell // scan_z,
                z=within // scan_x,
                r=colour >> 16 & 0xFF,
                g=colour >> 8 & 0xFF,
                b=colour & 0xFF,
                w=colour >> 24,
                t=struct.unpack_from("<H", body, types_at + 2 * index)[0],
            )
        )
    return Decoded(voxels, pos, size, body[needed:])


def _split_header(fields):
    return fields[:3], fields[3:6], fields[6], fields[7]
