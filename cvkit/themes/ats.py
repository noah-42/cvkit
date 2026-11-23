"""Content for the ATS page (templates/ats.html.j2): one column, plain text, standard headings, no links."""
from __future__ import annotations

from ..text import plain, split_location

TEMPLATE = "ats.html.j2"

# Print settings (site.print). The recommended values are only reported against, never enforced.
PRINT_DEFAULTS = {"font": "mono", "start_pt": 10.5, "min_pt": None, "max_pages": None}
RECOMMENDED = {"min_pt": 10, "max_pages": 2}
FONTS = {"mono": "", "sans": '"Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif'}


def print_settings(site: dict) -> dict:
    s = {**PRINT_DEFAULTS, **site.get("print", {})}
    if s["font"] not in FONTS:
        raise ValueError(f'site.print.font must be one of {", ".join(FONTS)}')
    if s["min_pt"] is None:
        s["min_pt"] = s["start_pt"]
    return s


def _n(x: float) -> str:
    return f"{x:g}"


def print_css(site: dict, pt: float | None = None) -> dict:
    s = print_settings(site)
    pt = s["start_pt"] if pt is None else pt
    return {"pt": _n(pt), "h1": _n(pt + 6.5), "h2": _n(pt + 2), "font_family": FONTS[s["font"]]}
SECTIONS = {
    "summary": "Summary",
    "projects": "Projects",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills &amp; Tools",
    "languages": "Languages",
    "contact": "Contact",
}


def context(data: dict, private: dict | None = None, pt: float | None = None) -> dict:
    """`private` (from private.json) adds lines to the contact list; only the local PDF uses it."""
    site = data.get("site", {})
    ats = site.get("ats", {})
    private = private or {}

    experience = []
    for e in data["experience"]:
        city, dates = split_location(e["location"])
        heading = ", ".join(plain(p["text"]) for p in e["heading_parts"])
        experience.append({"heading": f"{heading} | {plain(dates)}" if dates else heading,
                           "city": plain(city), "bullets": [plain(b) for b in e["bullets"]]})

    return {
        "name": site["name"],
        "pdf": bool(site.get("pdf")) and not private,
        "print": print_css(site, pt),
        "headline": plain(data["headline"]),
        "contact_line": private.get("contact_line", []) + ats.get("contact_line", []),
        "sections": {**SECTIONS, **ats.get("sections", {})},
        "summary": [plain(s) for s in data["summary"]],
        "projects": [{"name": plain(p["name"]), "desc": plain(p["desc"])}
                     for p in data.get("projects", []) if not p.get("hidden")],
        "experience": experience,
        "education": [{"heading": ", ".join(plain(p["text"]) for p in e["heading_parts"]),
                       "city": plain(split_location(e["location"])[0])} for e in data["education"]],
        "skills": [{"label": plain(s["label"]), "list": plain(", ".join(s["items"]))} for s in data["skills"]],
        "languages": plain(data["languages"]),
        "contact_list": private.get("contact_list", []) + ats.get("contact_list", []),
    }
