"""Create a new CV site folder from the starter files."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def _walk(node, rel=""):
    for child in node.iterdir():
        path = f"{rel}{child.name}"
        if child.is_dir():
            yield from _walk(child, path + "/")
        elif child.name != "__pycache__":
            yield path, child


def init(target: Path) -> list[Path]:
    starter = list(_walk(files("cvkit") / "scaffold"))
    clashes = [rel for rel, _ in starter if (target / rel).exists()]
    if clashes:
        raise FileExistsError("already there, not overwritten: " + ", ".join(clashes))
    written = []
    for rel, src in starter:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        written.append(dest)
    return written
