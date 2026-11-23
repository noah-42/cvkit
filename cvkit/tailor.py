"""`cvkit tailor job.txt`: a version of the CV for one job ad.

The model only ranks the CV's own items by how much they matter for the job: it returns item ids, never text, so a
tailored version cannot contain anything that is not already in cv.json. Code then applies the ranking:

- summary lines, bullets and projects: the chosen ones, most relevant first; the rest are left out
  (if nothing in a section is chosen, it stays as it was);
- every job stays, in its original (date) order, and keeps at least one bullet;
- skills: groups and items reordered, nothing removed (they are the ATS keywords).

Where you apply is personal, so a tailored version is private by default: it goes to private/tailored/<slug>/
(git-ignored). With --publish it goes to tailored/<slug>.json, and `cvkit build` publishes it at /cv/<slug>/,
marked noindex.
"""
from __future__ import annotations

import copy
import re

from .text import plain

SCHEMA = {
    "type": "object",
    "properties": {k: {"type": "array", "items": {"type": "string"}} for k in ("summary", "bullets", "projects", "skills")},
    "required": ["summary", "bullets", "projects", "skills"],
}
SYSTEM = """You help tailor a CV to one job ad. You get the job ad and the CV's items, each with an id in square
brackets. For each section, list the ids of the items that matter for this job, most relevant first. Leave out
items that do not help for this job. Return ids only, exactly as given, never text."""


def items(data: dict) -> dict[str, str]:
    """Every rankable item as {id: plain text}: s<i> summary, e<j>b<k> bullet, p<i> project, k<g>i<n> skill."""
    out = {f"s{i}": plain(s) for i, s in enumerate(data.get("summary", []))}
    for j, e in enumerate(data["experience"]):
        for k, b in enumerate(e.get("bullets", [])):
            out[f"e{j}b{k}"] = plain(b)
    for i, p in enumerate(data.get("projects", [])):
        if not p.get("hidden"):
            out[f"p{i}"] = f'{plain(p["name"])}: {plain(p["desc"])}'
    for g, s in enumerate(data.get("skills", [])):
        for n, item in enumerate(s["items"]):
            out[f"k{g}i{n}"] = f'{plain(s["label"])}: {plain(item)}'
    return out


def prompt(data: dict, job: str) -> str:
    it = items(data)
    lines = ["JOB AD:", job.strip(), "", "CV ITEMS:", "Summary:"]
    lines += [f"[{i}] {t}" for i, t in it.items() if i.startswith("s")]
    for j, e in enumerate(data["experience"]):
        heading = ", ".join(plain(p["text"]) for p in e["heading_parts"])
        lines.append(f"Job {j}: {heading}")
        lines += [f"[{i}] {t}" for i, t in it.items() if i.startswith(f"e{j}b")]
    lines.append("Projects:")
    lines += [f"[{i}] {t}" for i, t in it.items() if i.startswith("p")]
    lines.append("Skills:")
    lines += [f"[{i}] {t}" for i, t in it.items() if i.startswith("k")]
    return "\n".join(lines)


def _ids(ranked: list, pattern: str) -> list[tuple[int, ...]]:
    out, seen = [], set()
    for r in ranked:
        m = re.fullmatch(pattern, str(r).strip().strip("[]"))
        if m:
            key = tuple(int(x) for x in m.groups())
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def apply_ranking(data: dict, ranked: dict) -> dict:
    """A tailored copy of `data`. Unknown ids are ignored; nothing is ever added."""
    t = copy.deepcopy(data)

    chosen = [i for (i,) in _ids(ranked.get("summary", []), r"s(\d+)") if i < len(data.get("summary", []))]
    if chosen:
        t["summary"] = [data["summary"][i] for i in chosen]

    by_job: dict[int, list[int]] = {}
    for j, k in _ids(ranked.get("bullets", []), r"e(\d+)b(\d+)"):
        if j < len(data["experience"]) and k < len(data["experience"][j].get("bullets", [])):
            by_job.setdefault(j, []).append(k)
    for j, e in enumerate(t["experience"]):
        original = data["experience"][j].get("bullets", [])
        if j in by_job:
            e["bullets"] = [original[k] for k in by_job[j]]
        elif original:
            e["bullets"] = original[:1]  # not relevant: keep the first bullet so the job is not empty

    visible = [i for i, p in enumerate(data.get("projects", [])) if not p.get("hidden")]
    chosen = [i for (i,) in _ids(ranked.get("projects", []), r"p(\d+)") if i in visible]
    if chosen:
        t["projects"] = [data["projects"][i] for i in chosen]

    order: dict[int, list[int]] = {}
    for g, n in _ids(ranked.get("skills", []), r"k(\d+)i(\d+)"):
        if g < len(data.get("skills", [])) and n < len(data["skills"][g]["items"]):
            order.setdefault(g, []).append(n)
    groups = list(order) + [g for g in range(len(data.get("skills", []))) if g not in order]
    t["skills"] = []
    for g in groups:
        src = data["skills"][g]
        first = order.get(g, [])
        rest = [n for n in range(len(src["items"])) if n not in first]
        t["skills"].append({**src, "items": [src["items"][n] for n in first + rest]})

    t.setdefault("site", {})["noindex"] = True
    return t


def tailor(model, data: dict, job: str) -> dict:
    return apply_ranking(data, model.json(SYSTEM, prompt(data, job), SCHEMA))


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "job"
