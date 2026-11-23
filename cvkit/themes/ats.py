"""The ATS page: one column, plain text, standard headings, no links in the body."""
from __future__ import annotations

from ..text import plain, split_location

SECTIONS = {
    "summary": "Summary",
    "projects": "Projects",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills &amp; Tools",
    "languages": "Languages",
    "contact": "Contact",
}

STYLE = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Inconsolata:400,700&display=swap">
    <style>
      body { font-family: "Inconsolata", "Courier New", monospace; font-size: 12pt; color: #24292f; max-width: 100%; margin: 24px auto; padding: 0 16px; line-height: 1.5; background: #fff; }
      h1 { font-size: 20pt; margin-bottom: 4px; color: #0A66C2; }
      h2 { font-size: 15pt; color: #444746; border-bottom: 1px solid #444746; margin-top: 20px; margin-bottom: 8px; }
      h3 { font-size: 12pt; margin: 12px 0 2px; color: #0A66C2; }
      p.headline { margin: 0 0 6px; color: #444746; font-style: italic; }
      p.location { font-style: italic; color: #3d3d3d; margin: 0 0 4px; }
      ul { margin: 4px 0 10px 22px; padding: 0; }
      li { margin-bottom: 2px; color: #24292f; }
      a { color: #0A66C2; }
      .contact { margin-bottom: 8px; }
    </style>"""


def render(data: dict) -> str:
    site = data.get("site", {})
    ats = site.get("ats", {})
    sections = {**SECTIONS, **ats.get("sections", {})}
    name = site["name"]

    summary = "\n".join(f"      <li>{plain(b)}</li>" for b in data["summary"])
    projects = "\n".join(f'      <li>{plain(p["name"])}: {plain(p["desc"])}</li>'
                         for p in data.get("projects", []) if not p.get("hidden"))

    experience = []
    for e in data["experience"]:
        heading = ", ".join(plain(p["text"]) for p in e["heading_parts"])
        city, dates = split_location(e["location"])
        heading = f"{heading} | {plain(dates)}" if dates else heading
        loc = f'    <p class="location">{plain(city)}</p>\n' if city else ""
        bullets = ""
        if e["bullets"]:
            items = "\n".join(f"      <li>{plain(b)}</li>" for b in e["bullets"])
            bullets = f"    <ul>\n{items}\n    </ul>\n"
        experience.append(f"    <h3>{heading}</h3>\n{loc}{bullets}")

    education = []
    for e in data["education"]:
        heading = ", ".join(plain(p["text"]) for p in e["heading_parts"])
        city, _ = split_location(e["location"])
        loc = f'    <p class="location">{plain(city)}</p>\n' if city else ""
        education.append(f"    <h3>{heading}</h3>\n{loc}")

    skills = "\n".join(f'      <li>{plain(s["label"])}: {plain(", ".join(s["items"]))}</li>' for s in data["skills"])
    contact_line = " | ".join(ats.get("contact_line", []) + ['<a href="../">formatted version</a>'])
    contact_list = "\n".join(f"      <li>{line}</li>" for line in ats.get("contact_list", []))
    experience_html = "\n".join(experience)
    education_html = "\n".join(education)

    return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <title>{name} - ATS CV</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="ATS-friendly CV for {name}" />
{STYLE}
  </head>
  <body>
    <h1>{name}</h1>
    <p class="headline">{plain(data["headline"])}</p>
    <p class="contact">{contact_line}</p>

    <h2>{sections["summary"]}</h2>
    <ul>
{summary}
    </ul>

    <h2>{sections["projects"]}</h2>
    <ul>
{projects}
    </ul>

    <h2>{sections["experience"]}</h2>
{experience_html}

    <h2>{sections["education"]}</h2>
{education_html}

    <h2>{sections["skills"]}</h2>
    <ul>
{skills}
    </ul>

    <h2>{sections["languages"]}</h2>
    <p>{plain(data["languages"])}</p>

    <h2>{sections["contact"]}</h2>
    <ul>
{contact_list}
    </ul>
  </body>
</html>
'''
