"""Trove voxel models: a base grid plus its three material maps, compiled by the devtool.

The devtool reads and writes Qubicle binaries, so every edit goes through ``.qb`` and
comes back as a ``.blueprint``. One wrinkle: when a model's attachment marker sits below
the model's floor, the devtool compiles the blueprint's y position as if the marker were
on the floor, leaving the part floating on its bone. ``maps_to_blueprint`` puts that
offset back.
"""

import struct
import subprocess
import zlib
from pathlib import Path

from tools.qb import read_qb, write_qb

DEVTOOL = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Trove\Games\Trove\Live\devtool.bat")
MAGENTA = (255, 0, 255)
MAP_SUFFIXES = {"base": "", "alpha": "_a", "specular": "_s", "style": "_t"}
_HEADER = struct.Struct("<3i")


def blueprint_body(data):
    """The uncompressed payload of a ``.blueprint``."""
    if data[:5] != b"kiwib":
        raise ValueError("not a kiwib blueprint")
    return zlib.decompressobj().decompress(data[9:])


def _wrap(body):
    return b"kiwib\x05\x00\x00\x00" + _deflate(body)


def _deflate(body):
    folder = zlib.compressobj(9)
    return folder.compress(body) + folder.flush(zlib.Z_SYNC_FLUSH)


def shift_blueprint_y(data, delta_y):
    """Move a compiled model along y by ``delta_y`` blueprint voxels."""
    body = blueprint_body(data)
    if len(body) < _HEADER.size:
        return data
    position = list(_HEADER.unpack_from(body, 0))
    position[1] += delta_y
    return _wrap(_HEADER.pack(*position) + body[_HEADER.size :])


def read_maps(directory, stem):
    maps = {name: read_qb((directory / f"{stem}{suffix}.qb").read_bytes())[0] for name, suffix in MAP_SUFFIXES.items()}
    model = maps["base"]
    for name, matrix in maps.items():
        if (matrix.size, matrix.pos) != (model.size, model.pos):
            raise ValueError(f"the {name} map is {matrix.size} at {matrix.pos}, the model is {model.size} at {model.pos}")
    return maps


def _run_devtool(*arguments):
    """`devtool.bat` ends on the exit status of its empty-argument test, so the artefact
    it was asked to write is the only usable proof it worked. The batch file is run
    directly: ``cmd /c`` strips the outer quotes once several arguments carry spaces."""
    subprocess.run([str(DEVTOOL), *arguments], cwd=DEVTOOL.parent, capture_output=True)


def blueprint_to_maps(blueprint_path, directory, stem):
    _run_devtool("copyblueprint", "-generatemaps", "1", str(blueprint_path), str(directory / f"{stem}.qb"))
    return read_maps(directory, stem)


def maps_to_blueprint(directory, stem, maps):
    for name, matrix in maps.items():
        (directory / f"{stem}{MAP_SUFFIXES[name]}.qb").write_bytes(write_qb(matrix))
    target = directory / f"{stem}.blueprint"
    target.unlink(missing_ok=True)
    _run_devtool(
        "copyblueprint",
        "-applystylemap",
        "1",
        "-applytypemap",
        "1",
        "-applyalphamap",
        "1",
        str(directory / f"{stem}.qb"),
        str(target),
    )
    if not target.exists():
        raise RuntimeError(f"the devtool compiled no blueprint for {stem}.qb")
    return shift_blueprint_y(target.read_bytes(), maps["base"].pos[1])
