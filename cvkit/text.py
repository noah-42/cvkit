"""Small text helpers shared by the themes."""
from __future__ import annotations

import html
import re
import unicodedata

_ENTITY = re.compile(r"&[A-Za-z]+;|&#\d+;")


def plain(text: str) -> str:
    """HTML text to plain ASCII-friendly text for the ATS page.

    `&amp;` becomes `&`, `&ndash;` becomes `-`, and accented letters lose their accent
    (`S&atilde;o` becomes `Sao`), because some ATS parsers stumble on them.
    """
    text = text.replace("&amp;", "&").replace("&ndash;", "-")

    def _one(m: re.Match) -> str:
        char = html.unescape(m.group(0))
        return unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode() or char

    return _ENTITY.sub(_one, text)


def split_location(location: str) -> tuple[str, str]:
    """Split 'City (dates)' into ('City', 'dates')."""
    location = location.strip()
    if location.endswith(")") and " (" in location:
        city, dates = location.rsplit(" (", 1)
        return city, dates.rstrip(")")
    return location, ""


def anchor(text: str, url: str) -> str:
    return f'<a class="plain-link" href="{url}" target="_blank" rel="noopener">{text}</a>'


def link_or_text(text: str, url: str | None) -> str:
    return anchor(text, url) if url else text
