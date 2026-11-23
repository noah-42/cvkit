"""cvkit command line."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import sys
import tempfile
from pathlib import Path

from .build import build, load


def _build(a) -> int:
    for path in build(Path(a.root), Path(a.data) if a.data else None, Path(a.out) if a.out else None):
        print(f"wrote {path}")
    return 0


def _check(a) -> int:
    from .check import check, keyword_overlap
    root = Path(a.root)
    data = load(root, Path(a.data) if a.data else None)
    issues = check(root, data)
    for level, path, msg in issues:
        print(f"{level:5}  {path}: {msg}")
    errors = sum(1 for i in issues if i[0] == "error")
    print(f"{errors} errors, {len(issues) - errors} warnings")
    if a.job:
        found, missing = keyword_overlap(data, Path(a.job).read_text())
        total = len(found) + len(missing)
        print(f"\njob ad keywords in the CV: {len(found)} of {total}")
        print("  found:   " + ", ".join(found))
        print("  missing: " + ", ".join(missing))
    return 1 if errors else 0


def _pdf(a) -> int:
    from .pdf import make_pdf
    root = Path(a.root)
    out = Path(a.out) if a.out else (root / "private" / "cv.pdf" if a.private else root / "cv.pdf")
    overrides = {k: v for k, v in {"font": a.font, "min_pt": a.min_pt, "max_pages": a.max_pages}.items() if v is not None}
    r = make_pdf(root, out, private=a.private, overrides=overrides)
    print(f"wrote {r.path}: {r.pages} pages, {r.pt:g}pt, {r.font} font")
    for note in r.notes:
        print(f"note   {note}")
    return 0


def _init(a) -> int:
    from .init import init
    for path in init(Path(a.root)):
        print(f"wrote {path}")
    print("\nNext: edit cv.json, then run `cvkit serve` to look at it.")
    return 0


def _serve(a) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        build(Path(a.root), out=Path(tmp))
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
        with http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler) as server:
            print(f"http://127.0.0.1:{a.port}/  (ATS page: /ats/)  Ctrl+C to stop")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    return 0


def _export(a) -> int:
    from .jsonresume import to_jsonresume
    json.dump(to_jsonresume(load(Path(a.root))), sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvkit", description="A CV site and an ATS version from one data file.")
    sub = parser.add_subparsers(dest="command", required=True)

    def cmd(name, fn, help):
        p = sub.add_parser(name, help=help)
        p.add_argument("root", nargs="?", default=".", help="site folder (default: current folder)")
        p.set_defaults(fn=fn)
        return p

    b = cmd("build", _build, "build index.html and ats/index.html")
    b.add_argument("--data", help="data file (default: cv.json or cv_data.json)")
    b.add_argument("--out", help="write the site here instead (static folders are copied along)")
    c = cmd("check", _check, "check the data file; with --job, compare it with a job ad")
    c.add_argument("--data")
    c.add_argument("--job", help="a job ad as a text file")
    p = cmd("pdf", _pdf, "print the ATS page to cv.pdf (needs Chrome or Chromium)")
    p.add_argument("--out")
    p.add_argument("--private", action="store_true", help="add private.json lines; writes private/cv.pdf")
    p.add_argument("--font", choices=["mono", "sans"], help="override site.print.font")
    p.add_argument("--min-pt", type=float, help="override site.print.min_pt (smallest font size allowed)")
    p.add_argument("--max-pages", type=int, help="override site.print.max_pages")
    cmd("init", _init, "create a new site folder from the starter files")
    s = cmd("serve", _serve, "build into a temporary folder and show it on localhost")
    s.add_argument("--port", type=int, default=8000)
    cmd("export-jsonresume", _export, "print the data as JSON Resume")

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as e:
        print(f"cvkit: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
