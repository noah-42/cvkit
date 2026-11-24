"""`cvkit import`: an old CV (PDF, text or Markdown) into cv.json, with help from a local model.

The model only copies facts out of the text. Code then checks every fact against the text: anything it cannot find
there is flagged and is never added quietly. On a terminal you are asked about each flagged item; otherwise they
are written to a separate file for you to look at.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .jsonresume import from_jsonresume, parse_date

S = {"type": "string"}
SCHEMA = {
    "type": "object",
    "properties": {
        "name": S, "headline": S, "city": S,
        "summary": {"type": "array", "items": S},
        "experience": {"type": "array", "items": {"type": "object", "properties": {
            "title": S, "employer": S, "city": S, "start": S, "end": S,
            "bullets": {"type": "array", "items": S}},
            "required": ["title", "employer", "city", "start", "end", "bullets"]}},
        "education": {"type": "array", "items": {"type": "object", "properties": {
            "qualification": S, "institution": S, "city": S, "start": S, "end": S},
            "required": ["qualification", "institution", "city", "start", "end"]}},
        "projects": {"type": "array", "items": {"type": "object", "properties": {
            "name": S, "description": S, "url": S}, "required": ["name", "description", "url"]}},
        "skills": {"type": "array", "items": {"type": "object", "properties": {
            "group": S, "items": {"type": "array", "items": S}}, "required": ["group", "items"]}},
        "languages": {"type": "array", "items": {"type": "object", "properties": {
            "language": S, "fluency": S}, "required": ["language", "fluency"]}},
        "links": {"type": "array", "items": {"type": "object", "properties": {
            "label": S, "url": S}, "required": ["label", "url"]}},
    },
    "required": ["name", "headline", "city", "summary", "experience", "education", "projects", "skills",
                 "languages", "links"],
}

SYSTEM = """You copy facts out of a CV into JSON. Rules:
- Copy words exactly as they are written in the CV. Do not add, guess, improve, translate or summarise anything.
- If the CV does not say something, leave that field as an empty string or an empty list.
- Dates: copy them as written, for example "Mar 2021", "2019" or "present".
- One experience entry per job; its bullets are the lines written under that job, copied word for word.
- Skills: keep the CV's own groups; if it has none, use one group named "Skills".
- Links: only web addresses and profile links that appear in the CV (LinkedIn, GitHub, a website). Never phone
  numbers, street addresses or email addresses."""

STOP = set("a an and the of to in on for with at by from as or is are was were be been our we i my this that it its "
           "into over under per via".split())
MONTH_WORDS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "present",
               "current", "now", "today", "sept"}


def read_source(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    if path.suffix.lower() == ".pdf":
        if shutil.which("pdftotext"):
            r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError(f"could not read {path.name} as a PDF ({r.stderr.strip()[:120] or 'pdftotext failed'})")
            return r.stdout
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("reading a PDF needs pdftotext (poppler) or the pypdf package") from None
        return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    return path.read_text()


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9+#]+", " ", text).split())


@dataclass
class Checker:
    source: str
    _norm: str = field(init=False)
    _tokens: set = field(init=False)

    def __post_init__(self):
        self._norm = f" {norm(self.source)} "
        self._tokens = set(self._norm.split())

    def exact(self, value: str) -> bool:
        v = norm(value)
        return not v or f" {v} " in self._norm

    def url(self, value: str) -> bool:
        return self.exact(re.sub(r"^https?://(www\.)?", "", value).rstrip("/"))

    def prose(self, value: str) -> bool:
        """At least 90% of the meaningful words must appear in the source."""
        words = [w for w in norm(value).split() if w not in STOP and len(w) > 2]
        return not words or sum(w in self._tokens for w in words) / len(words) >= 0.9

    def date(self, value: str) -> bool:
        words = norm(value).split()
        years = [w for w in words if re.fullmatch(r"(19|20)\d\d", w)]
        return all(y in self._tokens for y in years) and all(w in MONTH_WORDS or w[:3] in MONTH_WORDS or w in years for w in words)


@dataclass
class Flag:
    path: str
    value: str
    why: str


def _iso(text: str) -> str | None:
    t = text.strip()
    if not t or t.lower() in {"present", "current", "now", "today"}:
        return None
    return parse_date(t)


def check_and_assemble(extracted: dict, source: str, accept: frozenset = frozenset()) -> tuple[dict, list[Flag], int]:
    """Keep only facts found in `source`, plus the flagged paths the user accepted.
    Returns (JSON Resume dict, flags, number of facts checked)."""
    c = Checker(source)
    flags: list[Flag] = []
    checked = 0

    def ok(path: str, value: str, test) -> bool:
        nonlocal checked
        if not value:
            return False
        checked += 1
        if test(value) or path in accept:
            return True
        flags.append(Flag(path, value, "not found in the source text"))
        return False

    basics = {"name": extracted["name"] if ok("name", extracted["name"], c.exact) else "",
              "label": extracted["headline"] if ok("headline", extracted["headline"], c.prose) else "",
              "profiles": []}
    if ok("city", extracted["city"], c.exact):
        basics["location"] = {"city": extracted["city"]}
    summary = [s for i, s in enumerate(extracted["summary"]) if ok(f"summary[{i}]", s, c.prose)]
    for i, l in enumerate(extracted["links"]):
        if ok(f"links[{i}]", l["url"], c.url):
            url = l["url"] if "://" in l["url"] else "https://" + l["url"]
            basics["profiles"].append({"network": l["label"] or "Web", "url": url})

    work = []
    for i, e in enumerate(extracted["experience"]):
        p = f"experience[{i}]"
        if not ok(f"{p}.title", e["title"], c.exact):
            continue
        item = {"position": e["title"]}
        if ok(f"{p}.employer", e["employer"], c.exact):
            item["name"] = e["employer"]
        if ok(f"{p}.city", e["city"], c.exact):
            item["location"] = e["city"]
        if ok(f"{p}.start", e["start"], c.date) and _iso(e["start"]):
            item["startDate"] = _iso(e["start"])
            if e["end"] and ok(f"{p}.end", e["end"], c.date) and _iso(e["end"]):
                item["endDate"] = _iso(e["end"])
        item["highlights"] = [b for j, b in enumerate(e["bullets"]) if ok(f"{p}.bullets[{j}]", b, c.prose)]
        work.append(item)

    education = []
    for i, e in enumerate(extracted["education"]):
        p = f"education[{i}]"
        if not ok(f"{p}.institution", e["institution"], c.exact):
            continue
        item = {"institution": e["institution"]}
        if ok(f"{p}.qualification", e["qualification"], c.exact):
            item["studyType"] = e["qualification"]
        if ok(f"{p}.start", e["start"], c.date) and _iso(e["start"]):
            item["startDate"] = _iso(e["start"])
            if e["end"] and ok(f"{p}.end", e["end"], c.date) and _iso(e["end"]):
                item["endDate"] = _iso(e["end"])
        education.append(item)

    projects = []
    for i, pr in enumerate(extracted["projects"]):
        if not ok(f"projects[{i}].name", pr["name"], c.exact):
            continue
        item = {"name": pr["name"], "description": pr["description"] if ok(f"projects[{i}].description", pr["description"], c.prose) else ""}
        if pr["url"] and ok(f"projects[{i}].url", pr["url"], c.url):
            item["url"] = pr["url"] if "://" in pr["url"] else "https://" + pr["url"]
        projects.append(item)

    skills = []
    for i, s in enumerate(extracted["skills"]):
        items = [x for j, x in enumerate(s["items"]) if ok(f"skills[{i}].items[{j}]", x, c.exact)]
        if items:
            skills.append({"name": s["group"] or "Skills", "keywords": items})
    languages = [{"language": l["language"], **({"fluency": l["fluency"]} if l["fluency"] and c.exact(l["fluency"]) else {})}
                 for i, l in enumerate(extracted["languages"]) if ok(f"languages[{i}]", l["language"], c.exact)]

    resume = {"basics": basics, "work": work, "education": education, "projects": projects,
              "skills": skills, "languages": languages, "_summary": summary}
    return resume, flags, checked


def to_cv(resume: dict) -> dict:
    summary = resume.pop("_summary", [])
    cv = from_jsonresume(resume)
    cv["summary"] = summary
    return cv


def extract(model, source: str) -> dict:
    return model.json(SYSTEM, "Here is the CV:\n\n" + source, SCHEMA)
