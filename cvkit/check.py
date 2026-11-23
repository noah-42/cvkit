"""Check a data file before building. Messages name the field, never its contents."""
from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

from .jsonresume import parse_range
from .text import plain, split_location

_TAG = re.compile(r"<[a-zA-Z/][^>]*>")
_ENTITY = re.compile(r"&[A-Za-z#0-9]+;")
STOP = set("""a an and are as at be by for from has have in is it its of on or our that the this to we will with you
your their they all any can more most other our such than then there these those into about over under not but per
via who what when where which while within without job role team work working experience years year strong ability
including include includes etc using use new across well also must should""".split())


def _ats_text(text: str, path: str, issues: list) -> None:
    flat = plain(text)
    if _TAG.search(flat):
        issues.append(("warn", path, "contains an HTML tag; it will show as text on the ATS page"))
    if _ENTITY.search(flat):
        issues.append(("warn", path, "contains an HTML entity the ATS page cannot turn into plain text"))


def _dates(location: str, path: str, issues: list, required: bool) -> None:
    _, dates = split_location(location)
    if not dates:
        if required:
            issues.append(("warn", path, "no dates; write it as 'City (Mon YYYY&ndash;Mon YYYY)'"))
        return
    start, _ = parse_range(dates)
    if not start:
        issues.append(("warn", path, "dates not understood; use 'Mon YYYY' or 'YYYY', joined by &ndash;"))


def check(root: Path, data: dict) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    site = data.get("site", {})
    if not site.get("name"):
        issues.append(("error", "site.name", "missing; it is the page title and the CV's name"))
    if not data.get("headline"):
        issues.append(("warn", "headline", "empty"))
    if not data.get("summary"):
        issues.append(("warn", "summary", "empty"))
    for key in ("experience", "education", "skills", "contact"):
        if key not in data:
            issues.append(("error", key, "missing"))
    if any(i[0] == "error" for i in issues):
        return issues

    for i, e in enumerate(data["experience"]):
        p = f"experience[{i}]"
        if not e.get("heading_parts") or not e["heading_parts"][0].get("text"):
            issues.append(("error", f"{p}.heading_parts", "needs at least a job title"))
        _dates(e.get("location", ""), f"{p}.location", issues, required=True)
        for j, b in enumerate(e.get("bullets", [])):
            _ats_text(b, f"{p}.bullets[{j}]", issues)
            if len(plain(b)) > 300:
                issues.append(("warn", f"{p}.bullets[{j}]", "over 300 characters; ATS and readers prefer short lines"))
    for i, e in enumerate(data["education"]):
        _dates(e.get("location", ""), f"education[{i}].location", issues, required=False)
    for i, s in enumerate(data.get("summary", [])):
        _ats_text(s, f"summary[{i}]", issues)
    if not data["skills"]:
        issues.append(("warn", "skills", "empty; ATS keyword matching leans on this section"))

    urls = site.get("contact", {}).get("urls", {})
    for i, line in enumerate(data["contact"].get("lines", [])):
        if ": " not in line:
            issues.append(("error", f"contact.lines[{i}]", "write it as 'Label: value'"))
        elif line.split(": ", 1)[1] not in urls and not line.split(": ", 1)[1].startswith("http"):
            issues.append(("warn", f"contact.lines[{i}]", "no link for it in site.contact.urls"))
    if not site.get("ats", {}).get("contact_line"):
        issues.append(("warn", "site.ats.contact_line", "empty; the ATS page shows no contact line under the name"))

    if (root / "private.json").exists():
        ignored = subprocess.run(["git", "check-ignore", "-q", "private.json"], cwd=root).returncode == 0
        if not ignored:
            issues.append(("error", "private.json", "not in .gitignore; it would be published"))
    return issues


def _terms(text: str) -> Counter:
    words = [w for w in re.findall(r"[a-z][a-z0-9+#.\-]*[a-z0-9+#]|[a-z]", text.lower()) if w not in STOP and len(w) > 1]
    return Counter(words) + Counter(f"{a} {b}" for a, b in zip(words, words[1:]))


def keyword_overlap(data: dict, job_text: str, top: int = 25) -> tuple[list[str], list[str]]:
    """The job ad's most frequent terms, split into (found in the CV, missing from the CV)."""
    cv = " ".join(plain(x) for x in [data.get("headline", ""), *data.get("summary", []),
                                     *[b for e in data["experience"] for b in e.get("bullets", [])],
                                     *[p["text"] for e in data["experience"] for p in e["heading_parts"]],
                                     *[i for s in data["skills"] for i in s["items"]]]).lower()
    terms = [t for t, n in _terms(job_text).most_common() if n >= 2 or " " not in t][:top]
    found = [t for t in terms if re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", cv)]
    return found, [t for t in terms if t not in found]
