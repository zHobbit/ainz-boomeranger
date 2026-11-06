"""Qubicle binaries as the official Trove devtool writes them."""

import struct
from dataclasses import dataclass

CELL = 4

_HEADER = struct.Struct("<6I")
_MATRIX = struct.Struct("<3I3i")


@dataclass
class Matrix:
    name: str
    size: tuple[int, int, int]
    pos: tuple[int, int, int]
    cells: dict[tuple[int, int, int], tuple[int, int, int]]


def read_qb(data):
    version, colour_format, z_orientation, compression, _, count = _HEADER.unpack_from(data, 0)
    for field, value, expected in (
        ("version", version, 257),
        ("colour_format", colour_format, 0),
        ("z_orientation", z_orientation, 1),
        ("compression", compression, 0),
    ):
        if value != expected:
            raise ValueError(f"Unsupported .qb {field} {value}, the devtool writes {expected}")

    offset = _HEADER.size
    matrices = []
    for _ in range(count):
        name_length = data[offset]
        name_end = offset + 1 + name_length
        matrix_end = name_end + _MATRIX.size
        if matrix_end > len(data):
            raise ValueError("Truncated .qb matrix header")
        name = data[name_end - name_length:name_end].decode("utf-8")
        size_x, size_y, size_z, pos_x, pos_y, pos_z = _MATRIX.unpack_from(data, name_end)
        cells_end = matrix_end + CELL * size_x * size_y * size_z
        if cells_end > len(data):
            raise ValueError("Truncated .qb voxel data")

        plane = size_x * size_y
        cells = {}
        for index in range(size_x * size_y * size_z):
            at = matrix_end + CELL * index
            if data[at + 3]:
                cells[(index % size_x, (index // size_x) % size_y, index // plane)] = (
                    data[at],
                    data[at + 1],
                    data[at + 2],
                )
        offset = cells_end
        matrices.append(Matrix(name, (size_x, size_y, size_z), (pos_x, pos_y, pos_z), cells))
    return matrices


def write_qb(matrix):
    name = matrix.name.encode("utf-8")
    if len(name) > 255:
        raise ValueError(f".qb matrix name is {len(name)} bytes, the header stores its length in one")
    size_x, size_y, size_z = matrix.size
    plane = size_x * size_y
    body = bytearray(CELL * plane * size_z)
    for (x, y, z), colour in matrix.cells.items():
        if not (0 <= x < size_x and 0 <= y < size_y and 0 <= z < size_z):
            raise ValueError(f"voxel {(x, y, z)} lies outside the {matrix.size} matrix")
        at = CELL * (z * plane + y * size_x + x)
        body[at : at + CELL] = bytes(colour) + b"\xff"
    return b"".join(
        (
            _HEADER.pack(257, 0, 1, 0, 0, 1),
            bytes((len(name),)) + name,
            _MATRIX.pack(size_x, size_y, size_z, *matrix.pos),
            bytes(body),
        )
    )
