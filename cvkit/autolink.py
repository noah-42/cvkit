"""Automatic links on the designed page, driven by `site.autolink` in cv.json.

The ATS page never gets these links. Keys (all optional):

- `summary`: list of {find, replace, when_startswith?}: replace the first `find` in a summary
  line with the HTML in `replace`.
- `bullet_replacements`: list of {find, replace}: same, for experience bullets, applied first.
- `bullet_links`: {name: url}: link the first mention of each name in a bullet (longest names first).
- `skill_links`: {skill: url}: link a skill when it matches exactly.
- `skill_links_partial`: {word: url}: link a word inside a skill.
"""
from __future__ import annotations

from .text import anchor


class AutoLinker:
    def __init__(self, rules: dict | None):
        rules = rules or {}
        self.summary = rules.get("summary", [])
        self.bullet_replacements = rules.get("bullet_replacements", [])
        self.bullet_links = rules.get("bullet_links", {})
        self.skill_links = rules.get("skill_links", {})
        self.skill_links_partial = rules.get("skill_links_partial", {})

    def summary_line(self, text: str) -> str:
        for rule in self.summary:
            prefix = rule.get("when_startswith")
            if prefix is None or text.startswith(prefix):
                text = text.replace(rule["find"], rule["replace"], 1)
        return text

    def bullet(self, text: str) -> str:
        for rule in self.bullet_replacements:
            text = text.replace(rule["find"], rule["replace"], 1)
        for name in sorted(self.bullet_links, key=len, reverse=True):
            text = text.replace(name, anchor(name, self.bullet_links[name]), 1)
        return text

    def skill(self, item: str) -> str:
        url = self.skill_links.get(item)
        if url:
            return anchor(item, url)
        for key, url in self.skill_links_partial.items():
            if key in item:
                return item.replace(key, anchor(key, url), 1)
        return item
