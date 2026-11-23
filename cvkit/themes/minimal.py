"""The designed page: minimal, one column, with links. Ported from noah-42.github.io."""
from __future__ import annotations

from ..autolink import AutoLinker
from ..text import anchor, link_or_text, split_location
from .icons import BUILTIN

SECTIONS = {
    "summary": "Summary",
    "projects": "Projects",
    "experience": "Experience",
    "education": "Education",
    "skills": "Skills &amp; Tools",
    "languages": "Languages",
    "contact": "Contact",
}


def _nav(site: dict) -> str:
    out = []
    for item in site.get("nav", []):
        icon = item["icon"]
        inner = BUILTIN[icon] if icon in BUILTIN else f'<img class="nav-icon" src="{icon}" alt="{item["label"]}" />'
        out.append(f'            <a target="_blank" rel="noopener" href="{item["url"]}" '
                   f'aria-label="{item["label"]}">{inner}</a>')
    return "\n".join(out)


def _contact(data: dict, site: dict) -> str:
    urls = site.get("contact", {}).get("urls", {})
    icons = site.get("contact", {}).get("icons", {})

    def item(label: str, shown: str) -> str:
        href = urls.get(shown, shown)
        icon = icons.get(label)
        if icon in BUILTIN:
            return f'<a href="{href}" aria-label="{label}" style="margin-right:14px">' + BUILTIN[icon] + '</a>'
        if icon:
            return (f'<a href="{href}" aria-label="{label}" style="margin-right:14px">'
                    f'<img src="{icon}" alt="{label}" '
                    f'style="width:16px;height:16px;vertical-align:-2px" /></a>')
        return f'<a href="{href}">{shown}</a>'

    pairs = [line.split(": ", 1) for line in data["contact"]["lines"]]
    return '          <div class="contact-row">' + "".join(item(l, u) for l, u in pairs) + "</div>"


def render(data: dict) -> str:
    site = data.get("site", {})
    sections = {**SECTIONS, **site.get("sections", {})}
    links = AutoLinker(site.get("autolink"))
    name = site["name"]

    summary = "\n".join(f"          <li>{links.summary_line(b)}</li>" for b in data["summary"])

    projects = []
    for p in data.get("projects", []):
        if p.get("hidden"):
            continue
        desc = p["desc"]
        for word, url in (p.get("desc_links") or {}).items():
            desc = desc.replace(word, anchor(word, url), 1)
        projects.append(f'          <li><span class="project-name">{link_or_text(p["name"], p.get("url"))}</span>\n'
                        f'            <span class="project-desc">{desc}</span>\n'
                        f'          </li>')

    experience = []
    for e in data["experience"]:
        parts = e["heading_parts"]
        if len(parts) >= 2:
            company = ", ".join(link_or_text(p["text"], p.get("url")) for p in parts[1:])
            heading = f'{parts[0]["text"]}, {company}'
        else:
            heading = parts[0]["text"]
        city, dates = split_location(e["location"])
        loc = f"{city} ({dates})" if dates else city
        bullets = ""
        if e["bullets"]:
            items = "\n".join(f"          <li>{links.bullet(b)}</li>" for b in e["bullets"])
            bullets = f"        <ul>\n{items}\n        </ul>\n"
        experience.append(f"        <h3>{heading}</h3>\n"
                          f'        <p class="location">{loc}</p>\n'
                          f"{bullets}")

    education = []
    for e in data["education"]:
        heading = ", ".join(link_or_text(p["text"], p.get("url")) for p in e["heading_parts"])
        city, dates = split_location(e["location"])
        loc = f"{city} ({dates})" if dates else city
        education.append(f"        <h3>{heading}</h3>\n"
                         f'        <p class="location">{loc}</p>')

    skills = []
    for s in data["skills"]:
        items = ", ".join(links.skill(i) for i in s["items"])
        skills.append(f'          <li><span class="skill-name">{s["label"]}</span>\n'
                      f'            <span class="skill-desc">{items}</span>\n'
                      f'          </li>')

    head = "\n".join(f"    {tag}" for tag in site.get("head", []))
    projects_html = "\n".join(projects)
    experience_html = "\n".join(experience)
    education_html = "\n".join(education)
    skills_html = "\n".join(skills)

    return f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <title>{name}</title>

    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="{site.get("description", name)}" />
    <meta name="author" content="{name}" />
{head}
  </head>
  <body>
    <div class="wrapper">
      <div class="navbar container">
        <span class="name-row">
          <a id="author-name" href="./">{name}</a>
          <span class="name-icons">
{_nav(site)}
          </span>
        </span>
        <p id="headline">{data["headline"]}</p>
      </div>
      <hr />

      <div class="container content">
        <h2 id="summary">{sections["summary"]}</h2>

        <ul>
{summary}
        </ul>

        <h2 id="projects">{sections["projects"]}</h2>

        <ul class="projects-table">
{projects_html}
        </ul>

        <h2 id="experience">{sections["experience"]}</h2>

{experience_html}
        <h2 id="education">{sections["education"]}</h2>

{education_html}
        <h2 id="skills-tools">{sections["skills"]}</h2>

        <ul class="skills-table">
{skills_html}
        </ul>

        <h2 id="languages">{sections["languages"]}</h2>

        <p>{data["languages"]}</p>

        <h2 id="contact">{sections["contact"]}</h2>

        <div class="contact-list">
{_contact(data, site)}
        </div>

        <div class="bottom-space"></div>
      </div>
    </div>
  </body>
</html>
'''
