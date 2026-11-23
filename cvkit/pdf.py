"""Print the ATS page to a PDF with a local Chrome or Chromium (no extra Python packages).

Fitting (site.print): start at `start_pt`; while the PDF has more than `max_pages` pages, go down 0.5pt at a time,
never below `min_pt`. If it still does not fit at `min_pt`, the PDF is kept at `min_pt` and the result says so.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .build import load, render_pages
from .themes.ats import RECOMMENDED, print_settings

CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
STEP = 0.5


@dataclass
class PdfResult:
    path: Path
    pages: int
    pt: float
    font: str
    fits: bool  # within max_pages (True when no max_pages is set)
    notes: list[str]


def find_browser() -> str:
    for c in [os.environ.get("CVKIT_CHROME", "")] + CANDIDATES:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("no Chrome or Chromium found; install one or set CVKIT_CHROME to its path")


def count_pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pdf))


def _print(browser: str, page: str, out: Path) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "cv.html"
        html.write_text(page)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([browser, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                        "--virtual-time-budget=10000", f"--print-to-pdf={out.resolve()}", html.as_uri()],
                       check=True, capture_output=True, timeout=120)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("the browser did not write a PDF")
    return count_pages(out.read_bytes())


def make_pdf(root: Path, out: Path, private: bool = False, overrides: dict | None = None) -> PdfResult:
    """Public PDF by default. With private=True, lines from private.json (phone, address) are added;
    keep that file out of git (`cvkit check` errors when it is not ignored). `overrides` replaces site.print keys."""
    data = load(root)
    if overrides:
        data.setdefault("site", {})["print"] = {**data["site"].get("print", {}), **overrides}
    s = print_settings(data.get("site", {}))
    extra = json.loads((root / "private.json").read_text()) if private else None
    browser = find_browser()

    pt = float(s["start_pt"])
    while True:
        pages = _print(browser, render_pages(root, data, extra, pt)["ats/index.html"], out)
        if not s["max_pages"] or pages <= s["max_pages"] or pt - STEP < s["min_pt"] - 1e-9:
            break
        pt -= STEP

    fits = not s["max_pages"] or pages <= s["max_pages"]
    notes = []
    if not fits:
        notes.append(f"does not fit in {s['max_pages']} pages at the minimum font size ({s['min_pt']:g}pt); "
                     "shorten the content or allow more pages")
    if pt < RECOMMENDED["min_pt"]:
        notes.append(f"font size {pt:g}pt is below the recommended minimum of {RECOMMENDED['min_pt']}pt")
    if pages > RECOMMENDED["max_pages"]:
        notes.append(f"{pages} pages is more than the recommended maximum of {RECOMMENDED['max_pages']}")
    return PdfResult(out, pages, pt, s["font"], fits, notes)
