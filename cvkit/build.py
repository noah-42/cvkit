"""Build the designed page and the ATS page from one data file."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader

from .themes import ats, minimal

DATA_NAMES = ("cv.json", "cv_data.json")
STATIC = ("css", "assets")


def find_data(root: Path) -> Path:
    for name in DATA_NAMES:
        if (root / name).exists():
            return root / name
    raise FileNotFoundError(f"no {' or '.join(DATA_NAMES)} in {root}")


def load(root: Path, data_path: Path | None = None) -> dict:
    data = json.loads((data_path or find_data(root)).read_text())
    if "basics" in data and "experience" not in data:  # a JSON Resume file
        from .jsonresume import from_jsonresume
        data = from_jsonresume(data)
    return data


def environment(root: Path) -> Environment:
    """A site's own templates/ folder wins over the built-in templates of the same name."""
    return Environment(
        loader=ChoiceLoader([FileSystemLoader(str(root / "templates")), PackageLoader("cvkit", "templates")]),
        autoescape=False, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )


def render_pages(root: Path, data: dict, private: dict | None = None) -> dict[str, str]:
    env = environment(root)
    return {
        "index.html": env.get_template(minimal.TEMPLATE).render(minimal.context(data)),
        "ats/index.html": env.get_template(ats.TEMPLATE).render(ats.context(data, private)),
    }


def build(root: Path, data_path: Path | None = None, out: Path | None = None) -> list[Path]:
    out = out or root
    written = []
    for rel, text in render_pages(root, load(root, data_path)).items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        written.append(path)
    if out.resolve() != root.resolve():  # building into another folder (e.g. _site): bring the static files along
        for name in STATIC:
            if (root / name).is_dir():
                shutil.copytree(root / name, out / name, dirs_exist_ok=True)
    return written
