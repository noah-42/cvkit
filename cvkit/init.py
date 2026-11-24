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


THEMES = ("minimal", "paper")


def init(target: Path, theme: str = "minimal") -> list[Path]:
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r}; choose from {', '.join(THEMES)}")
    starter = list(_walk(files("cvkit") / "scaffold")) + [("css/style.css", files("cvkit") / "css_themes" / f"{theme}.css")]
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


def set_theme(target: Path, theme: str) -> Path:
    """Replace css/style.css with a built-in theme; the old file is kept as css/style.css.bak."""
    if theme not in THEMES:
        raise ValueError(f"unknown theme {theme!r}; choose from {', '.join(THEMES)}")
    css = target / "css" / "style.css"
    css.parent.mkdir(parents=True, exist_ok=True)
    if css.exists():
        css.with_name("style.css.bak").write_bytes(css.read_bytes())
    css.write_bytes((files("cvkit") / "css_themes" / f"{theme}.css").read_bytes())
    return css
