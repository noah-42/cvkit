"""Build the designed page and the ATS page from one data file."""
from __future__ import annotations

import json
from pathlib import Path

from .themes import ats, minimal

DATA_NAMES = ("cv.json", "cv_data.json")


def find_data(root: Path) -> Path:
    for name in DATA_NAMES:
        if (root / name).exists():
            return root / name
    raise FileNotFoundError(f"no {' or '.join(DATA_NAMES)} in {root}")


def build(root: Path, data_path: Path | None = None) -> list[Path]:
    data = json.loads((data_path or find_data(root)).read_text())
    outputs = {root / "index.html": minimal.render(data), root / "ats" / "index.html": ats.render(data)}
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return list(outputs)
