"""Print the ATS page to a PDF with a local Chrome or Chromium (no extra Python packages)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .build import load, render_pages

CANDIDATES = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def find_browser() -> str:
    for c in [os.environ.get("CVKIT_CHROME", "")] + CANDIDATES:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    raise RuntimeError("no Chrome or Chromium found; install one or set CVKIT_CHROME to its path")


def make_pdf(root: Path, out: Path, private: bool = False) -> Path:
    """Public PDF by default. With private=True, lines from private.json (phone, address) are added;
    keep that file out of git (`cvkit check` warns when it is not ignored)."""
    extra = json.loads((root / "private.json").read_text()) if private else None
    page = render_pages(root, load(root), extra)["ats/index.html"]
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "cv.html"
        html.write_text(page)
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([find_browser(), "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                        "--virtual-time-budget=10000", f"--print-to-pdf={out.resolve()}", html.as_uri()],
                       check=True, capture_output=True, timeout=120)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("the browser did not write a PDF")
    return out
