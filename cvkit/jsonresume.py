"""Convert between cvkit's data file and JSON Resume (https://jsonresume.org), and make schema.org JSON-LD."""
from __future__ import annotations

import json
import re

from .text import plain, split_location

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_DATE = re.compile(r"^(?:([A-Za-z]{3})[a-z]*\.? )?(\d{4})$")


def parse_date(text: str) -> str | None:
    """'Mar 2021' -> '2021-03', '2021' -> '2021', 'present' -> None."""
    m = _DATE.match(text.strip())
    if not m:
        return None
    month, year = m.groups()
    if month and month.title() in MONTHS:
        return f"{year}-{MONTHS.index(month.title()) + 1:02d}"
    return year


def parse_range(dates: str) -> tuple[str | None, str | None]:
    """'Mar 2021&ndash;present' -> ('2021-03', None)."""
    parts = [p.strip() for p in plain(dates).split("-", 1)]
    start = parse_date(parts[0]) if parts and parts[0] else None
    end = parse_date(parts[1]) if len(parts) > 1 else start
    return start, end


def format_date(iso: str | None) -> str:
    if not iso:
        return "present"
    year, _, month = iso.partition("-")
    return f"{MONTHS[int(month[:2]) - 1]} {year}" if month else year


def _languages(text: str) -> list[dict]:
    out = []
    for part in plain(text).split(","):
        m = re.match(r"\s*([^()]+?)\s*(?:\(([^)]*)\))?\s*$", part)
        if m and m.group(1):
            out.append({"language": m.group(1), **({"fluency": m.group(2)} if m.group(2) else {})})
    return out


def to_jsonresume(data: dict) -> dict:
    site = data.get("site", {})
    work = []
    for e in data["experience"]:
        parts = e["heading_parts"]
        city, dates = split_location(e["location"])
        start, end = parse_range(dates) if dates else (None, None)
        item = {"position": plain(parts[0]["text"])}
        if len(parts) > 1:
            item["name"] = ", ".join(plain(p["text"]) for p in parts[1:])
            if parts[1].get("url"):
                item["url"] = parts[1]["url"]
        item.update({k: v for k, v in {"location": plain(city), "startDate": start, "endDate": end}.items() if v})
        if e["bullets"]:
            item["highlights"] = [plain(b) for b in e["bullets"]]
        work.append(item)
    education = []
    for e in data["education"]:
        parts = e["heading_parts"]
        city, dates = split_location(e["location"])
        start, end = parse_range(dates) if dates else (None, None)
        item = {"institution": plain(parts[-1]["text"])}
        if parts[-1].get("url"):
            item["url"] = parts[-1]["url"]
        if len(parts) > 1:
            item["studyType"] = ", ".join(plain(p["text"]) for p in parts[:-1])
        item.update({k: v for k, v in {"startDate": start, "endDate": end}.items() if v})
        education.append(item)
    return {
        "basics": {
            "name": site.get("name", ""),
            "label": plain(data.get("headline", "")),
            "summary": " ".join(plain(s) for s in data.get("summary", [])),
            **({"url": site["url"]} if site.get("url") else {}),
            "profiles": [{"network": n["label"], "url": n["url"]} for n in site.get("nav", [])],
        },
        "work": work,
        "education": education,
        "projects": [{"name": plain(p["name"]), "description": plain(p["desc"]), **({"url": p["url"]} if p.get("url") else {})}
                     for p in data.get("projects", []) if not p.get("hidden")],
        "skills": [{"name": plain(s["label"]), "keywords": [plain(i) for i in s["items"]]} for s in data.get("skills", [])],
        "languages": _languages(data.get("languages", "")),
    }


def _span(start: str | None, end: str | None) -> str:
    if not start:
        return ""
    return f" ({format_date(start)}&ndash;{format_date(end)})"


def _strip_scheme(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def from_jsonresume(resume: dict) -> dict:
    basics = resume.get("basics", {})
    profiles = basics.get("profiles", [])
    city = (basics.get("location") or {}).get("city", "")
    links = [p.get("url") for p in profiles if p.get("url")] + ([basics["url"]] if basics.get("url") else [])
    contact_lines = [f'{p.get("network", "Web")}: {_strip_scheme(p["url"])}' for p in profiles if p.get("url")]
    if basics.get("url"):
        contact_lines.append(f'Web: {_strip_scheme(basics["url"])}')
    return {
        "headline": basics.get("label", ""),
        "summary": [s.strip() for s in re.split(r"(?<=[.!?])\s+", basics.get("summary", "")) if s.strip()],
        "projects": [{"name": p.get("name", ""), "desc": p.get("description", ""), **({"url": p["url"]} if p.get("url") else {})}
                     for p in resume.get("projects", [])],
        "experience": [{
            "heading_parts": [{"text": w.get("position", "")}] + ([{"text": w["name"], **({"url": w["url"]} if w.get("url") else {})}] if w.get("name") else []),
            "location": f'{w.get("location", "")}{_span(w.get("startDate"), w.get("endDate"))}'.strip(),
            "bullets": w.get("highlights", []),
        } for w in resume.get("work", [])],
        "education": [{
            "heading_parts": ([{"text": e["studyType"]}] if e.get("studyType") else [])
                             + [{"text": e.get("institution", ""), **({"url": e["url"]} if e.get("url") else {})}],
            "location": _span(e.get("startDate"), e.get("endDate")).strip(),
        } for e in resume.get("education", [])],
        "skills": [{"label": s.get("name", ""), "items": s.get("keywords", [])} for s in resume.get("skills", [])],
        "languages": ", ".join(f'{l["language"]} ({l["fluency"]})' if l.get("fluency") else l.get("language", "")
                               for l in resume.get("languages", [])),
        "contact": {"lines": contact_lines, "links": []},
        "site": {
            "name": basics.get("name", ""),
            "description": f'CV of {basics.get("name", "")}',
            "head": ['<link rel="stylesheet" href="./css/style.css" />'],
            "nav": [{"label": p.get("network", "Web"), "url": p["url"],
                     "icon": "github" if p.get("network", "").lower() == "github" else f'{p["url"].split("/", 3)[0]}//{p["url"].split("/", 3)[2]}/favicon.ico'}
                    for p in profiles if p.get("url")],
            "contact": {"urls": {_strip_scheme(u): u for u in links}, "icons": {"GitHub": "github"}},
            "ats": {"contact_line": ([city] if city else []) + [_strip_scheme(u) for u in links],
                    "contact_list": contact_lines},
        },
    }


def jsonld(data: dict) -> str:
    """schema.org Person for the designed page, safe to put inside a <script> tag."""
    r = to_jsonresume(data)
    b = r["basics"]
    person = {"@context": "https://schema.org", "@type": "Person", "name": b["name"]}
    if b["label"]:
        person["jobTitle"] = b["label"]
    if b.get("url"):
        person["url"] = b["url"]
    if b["profiles"]:
        person["sameAs"] = [p["url"] for p in b["profiles"]]
    current = [{"@type": "Organization", "name": w["name"], **({"url": w["url"]} if w.get("url") else {})}
               for w in r["work"] if w.get("name") and w.get("startDate") and not w.get("endDate")]
    if current:
        person["worksFor"] = current
    schools = [{"@type": "EducationalOrganization", "name": e["institution"], **({"url": e["url"]} if e.get("url") else {})}
               for e in r["education"]]
    if schools:
        person["alumniOf"] = schools
    skills = [k for s in r["skills"] for k in s["keywords"]]
    if skills:
        person["knowsAbout"] = skills
    if r["languages"]:
        person["knowsLanguage"] = [l["language"] for l in r["languages"]]
    return json.dumps(person, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
