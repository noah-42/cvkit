"""Content for the designed page (templates/minimal.html.j2): minimal, one column, with links."""
from __future__ import annotations

from ..autolink import AutoLinker
from ..jsonresume import jsonld
from ..text import anchor, link_or_text, split_location
from .icons import BUILTIN

TEMPLATE = "minimal.html.j2"
SECTIONS = {
    "summary": "Summary",
    "projects": "Projects",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills &amp; Tools",
    "languages": "Languages",
    "contact": "Contact",
}


def _contact(data: dict, site: dict) -> list[str]:
    urls = site.get("contact", {}).get("urls", {})
    icons = site.get("contact", {}).get("icons", {})
    out = []
    for line in data["contact"]["lines"]:
        label, shown = line.split(": ", 1)
        href = urls.get(shown, shown)
        icon = icons.get(label)
        if icon in BUILTIN:
            out.append(f'<a href="{href}" aria-label="{label}" style="margin-right:14px">' + BUILTIN[icon] + "</a>")
        elif icon:
            out.append(f'<a href="{href}" aria-label="{label}" style="margin-right:14px">'
                       f'<img src="{icon}" alt="{label}" style="width:16px;height:16px;vertical-align:-2px" /></a>')
        else:
            out.append(f'<a href="{href}">{shown}</a>')
    return out


def _loc(location: str) -> str:
    city, dates = split_location(location)
    return f"{city} ({dates})" if dates else city


def context(data: dict) -> dict:
    site = data.get("site", {})
    links = AutoLinker(site.get("autolink"))

    projects = []
    for p in data.get("projects", []):
        if p.get("hidden"):
            continue
        desc = p["desc"]
        for word, url in (p.get("desc_links") or {}).items():
            desc = desc.replace(word, anchor(word, url), 1)
        projects.append({"name": link_or_text(p["name"], p.get("url")), "desc": desc})

    experience = []
    for e in data["experience"]:
        parts = e["heading_parts"]
        heading = parts[0]["text"]
        if len(parts) >= 2:
            heading += ", " + ", ".join(link_or_text(p["text"], p.get("url")) for p in parts[1:])
        experience.append({"heading": heading, "loc": _loc(e["location"]),
                           "bullets": [links.bullet(b) for b in e["bullets"]]})

    return {
        "name": site["name"],
        "description": site.get("description", site["name"]),
        "head": site.get("head", []),
        "jsonld": jsonld(data) if site.get("jsonld", True) else "",
        "nav": [{"label": n["label"], "url": n["url"],
                 "inner": BUILTIN.get(n["icon"]) or f'<img class="nav-icon" src="{n["icon"]}" alt="{n["label"]}" />'}
                for n in site.get("nav", [])],
        "headline": data["headline"],
        "sections": {**SECTIONS, **site.get("sections", {})},
        "summary": [links.summary_line(s) for s in data["summary"]],
        "projects": projects,
        "experience": experience,
        "education": [{"heading": ", ".join(link_or_text(p["text"], p.get("url")) for p in e["heading_parts"]),
                       "loc": _loc(e["location"])} for e in data["education"]],
        "skills": [{"label": s["label"], "list": ", ".join(links.skill(i) for i in s["items"])} for s in data["skills"]],
        "languages": data["languages"],
        "contact": _contact(data, site),
    }
