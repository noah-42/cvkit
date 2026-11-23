"""Content for the ATS page (templates/ats.html.j2): one column, plain text, standard headings, no links."""
from __future__ import annotations

from ..text import plain, split_location

TEMPLATE = "ats.html.j2"
SECTIONS = {
    "summary": "Summary",
    "projects": "Projects",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills &amp; Tools",
    "languages": "Languages",
    "contact": "Contact",
}


def context(data: dict, private: dict | None = None) -> dict:
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
