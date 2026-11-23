"""cvkit command line."""
from __future__ import annotations

import argparse
from pathlib import Path

from .build import build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvkit", description="Build a CV site from one data file.")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build", help="build index.html and ats/index.html")
    b.add_argument("root", nargs="?", default=".", help="site folder (default: current folder)")
    b.add_argument("--data", help="data file (default: cv.json or cv_data.json in the site folder)")
    args = parser.parse_args(argv)

    if args.command == "build":
        root = Path(args.root)
        for path in build(root, Path(args.data) if args.data else None):
            print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
