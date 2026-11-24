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
    from .build import published_tailored
    jobs = [(out, None)]
    if not a.private:  # published tailored versions get their PDF next to their pages
        jobs += [(out.parent / "cv" / slug / "cv.pdf", d) for slug, d in published_tailored(root)]
    for target, data in jobs:
        r = make_pdf(root, target, private=a.private, overrides=overrides, data=data)
        print(f"wrote {r.path}: {r.pages} pages, {r.pt:g}pt, {r.font} font")
        for note in r.notes:
            print(f"note   {note}")
    return 0


def _init(a) -> int:
    from .init import init
    for path in init(Path(a.root), a.theme):
        print(f"wrote {path}")
    print("\nNext: edit cv.json, then run `cvkit serve` to look at it.")
    return 0


def _theme(a) -> int:
    from .init import set_theme
    print(f"wrote {set_theme(Path(a.root), a.name)} (old file kept as style.css.bak)")
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


def _import(a) -> int:
    from .importer import check_and_assemble, extract, read_source, to_cv
    root = Path(a.root)
    src = Path(a.source)
    out = Path(a.out) if a.out else (root / "cv.imported.json" if (root / "cv.json").exists() else root / "cv.json")
    if out.exists():
        raise FileExistsError(f"{out} already exists; pass another --out")
    text = read_source(src)
    if not text.strip():
        raise RuntimeError(f"no text found in {src} (a scanned PDF needs OCR first)")
    model = _model(a)
    print(f"reading {src} with {model.model} on {model.host} (this can take a few minutes)...")
    extracted = extract(model, text)
    resume, flags, checked = check_and_assemble(extracted, text)
    accepted = set()
    if flags and sys.stdin.isatty() and not a.no_ask:
        print(f"\n{len(flags)} items were not found word for word in {src.name}. Keep each one?")
        for f in flags:
            if input(f"  {f.path}: {f.value!r}  keep? [y/N] ").strip().lower() == "y":
                accepted.add(f.path)
        resume, _, _ = check_and_assemble(extracted, text, frozenset(accepted))
    left_out = [f for f in flags if f.path not in accepted]
    out.write_text(json.dumps(to_cv(resume), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {out}: {checked} facts checked, {checked - len(flags)} found in the source, "
          f"{len(accepted)} kept by you, {len(left_out)} left out")
    if left_out:
        flagged = out.with_name(out.stem + ".flagged.json")
        flagged.write_text(json.dumps([f.__dict__ for f in left_out], indent=2, ensure_ascii=False) + "\n")
        print(f"left out (not in the source): {flagged}")
    print("next: cvkit check, then cvkit serve")
    return 0


def _model(a):
    from .llm import Ollama
    return Ollama(a.model, a.host, allow_remote=a.allow_remote)


def _polish(a) -> int:
    from .edit import apply, load_raw, polish, save_raw
    path, data = load_raw(Path(a.root))
    model = _model(a)
    print(f"asking {model.model} for suggestions on {path.name} (about half a minute per job)...")
    changes, dropped = polish(model, data, a.job)
    for p, text, why in dropped:
        print(f"dropped  {p}: {why}")
    if not changes:
        print("no suggestions")
        return 0
    if not sys.stdin.isatty():
        out = path.with_name(path.stem + ".polish.json")
        out.write_text(json.dumps([c.__dict__ for c in changes], indent=2, ensure_ascii=False) + "\n")
        print(f"{len(changes)} suggestions written to {out}; {path.name} is unchanged (run in a terminal to accept)")
        return 0
    accepted = []
    for c in changes:
        print(f"\n{c.path}\n  before: {c.before}\n  after:  {c.after}")
        if input("  use the new one? [y/N] ").strip().lower() == "y":
            accepted.append(c)
    if accepted:
        backup = save_raw(path, apply(data, accepted))
        print(f"\n{len(accepted)} of {len(changes)} accepted; {path.name} updated (old file: {backup.name})")
    else:
        print("\nnothing accepted; no change")
    return 0


def _interview(a) -> int:
    from .edit import apply, find_gaps, interview, load_raw, save_raw
    path, data = load_raw(Path(a.root))
    gaps = find_gaps(data)
    if not gaps:
        print("no gaps found: every job has dates and bullets, and there is a headline")
        return 0
    if not sys.stdin.isatty():
        raise RuntimeError(f"{len(gaps)} gaps found; interview asks questions, so run it in a terminal")
    print(f"{len(gaps)} gaps. Press Enter to skip a question.\n")
    accepted = interview(_model(a), data, input, print)
    if accepted:
        backup = save_raw(path, apply(data, accepted))
        print(f"\n{len(accepted)} answers added; {path.name} updated (old file: {backup.name})")
    else:
        print("\nnothing added; no change")
    return 0


def _tailor(a) -> int:
    from .build import write_site
    from .check import keyword_overlap
    from .tailor import slugify, tailor
    root = Path(a.root)
    data = load(root)
    job = Path(a.job).read_text()
    slug = slugify(a.slug or Path(a.job).stem)
    model = _model(a)
    print(f"ranking the CV's items for {Path(a.job).name} with {model.model}...")
    t = tailor(model, data, job)
    before, _ = keyword_overlap(data, job)
    after, missing = keyword_overlap(t, job)
    n_b = sum(len(e.get("bullets", [])) for e in data["experience"])
    n_t = sum(len(e.get("bullets", [])) for e in t["experience"])
    if a.publish:
        src = root / "tailored" / f"{slug}.json"
        src.parent.mkdir(exist_ok=True)
        src.write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
        pages = write_site(root, t, root / "cv" / slug)
        print(f"wrote {src} (published at /cv/{slug}/, noindex; it is public in your repository)")
    else:
        folder = root / "private" / "tailored" / slug
        (folder / "cv.json").parent.mkdir(parents=True, exist_ok=True)
        (folder / "cv.json").write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
        pages = write_site(root, t, folder)
        print(f"wrote {folder}/ (private: not committed, not published)")
    for p in pages:
        print(f"  {p}")
    print(f"bullets: {n_t} of {n_b} kept; summary lines: {len(t['summary'])} of {len(data['summary'])}")
    print(f"job ad keywords in the CV: {len(before)} before, {len(after)} after")
    if missing:
        print("  missing (only you can add these, if they are true): " + ", ".join(missing))
    if not a.no_pdf:
        from .pdf import make_pdf
        target = pages[0].parent / "cv.pdf"
        try:
            r = make_pdf(root, target, data=t)
            print(f"wrote {r.path}: {r.pages} pages, {r.pt:g}pt")
        except RuntimeError as e:
            print(f"no PDF: {e}")
    return 0


def _export(a) -> int:
    from .jsonresume import to_jsonresume
    json.dump(to_jsonresume(load(Path(a.root))), sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cvkit", description="A CV site and an ATS version from one data file.")
    sub = parser.add_subparsers(dest="command", required=True)

    def cmd(name, fn, help, root_positional=True):
        p = sub.add_parser(name, help=help)
        if root_positional:
            p.add_argument("root", nargs="?", default=".", help="site folder (default: current folder)")
        else:
            p.add_argument("--root", default=".", help="site folder (default: current folder)")
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
    ini = cmd("init", _init, "create a new site folder from the starter files")
    ini.add_argument("--theme", default="minimal", choices=["minimal", "paper"], help="look of the designed page")
    th = cmd("theme", _theme, "switch the designed page to a built-in theme (minimal or paper)", root_positional=False)
    th.add_argument("name", choices=["minimal", "paper"])

    s = cmd("serve", _serve, "build into a temporary folder and show it on localhost")
    s.add_argument("--port", type=int, default=8000)
    cmd("export-jsonresume", _export, "print the data as JSON Resume")
    im = cmd("import", _import, "turn an old CV (PDF, .txt, .md) into cv.json with a local model",
             root_positional=False)
    im.add_argument("source", help="the old CV")
    im.add_argument("--out", help="default: cv.json, or cv.imported.json when cv.json exists")
    pol = cmd("polish", _polish, "suggest stronger bullets with a local model; you accept or reject each")
    pol.add_argument("--job", type=int, help="only this job (0 is the first in experience)")
    itv = cmd("interview", _interview, "ask about gaps (dates, empty jobs, headline) and add your answers")
    tl = cmd("tailor", _tailor, "a version of the CV for one job ad (choose and reorder only; private by default)",
             root_positional=False)
    tl.add_argument("job", help="the job ad as a text file")
    tl.add_argument("--slug", help="name for this version (default: the job file's name)")
    tl.add_argument("--publish", action="store_true", help="publish it at /cv/<slug>/ (noindex) instead of private/")
    tl.add_argument("--no-pdf", action="store_true", help="skip the PDF")
    for p in (im, pol, itv, tl):
        p.add_argument("--model", help="Ollama model (default: $CVKIT_MODEL or gemma4)")
        p.add_argument("--host", help="Ollama address (default: $OLLAMA_HOST or http://localhost:11434)")
        p.add_argument("--allow-remote", action="store_true", help="allow a model host that is not this computer")
    im.add_argument("--no-ask", action="store_true", help="leave flagged items out without asking")

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except (FileNotFoundError, FileExistsError, RuntimeError, ValueError) as e:  # ModelError is a RuntimeError
        print(f"cvkit: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
