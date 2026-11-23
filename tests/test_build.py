"""Tests use the invented person in example/cv.json only, never a real CV."""
import json
import shutil
from pathlib import Path

from cvkit.build import build
from cvkit.text import plain, split_location
from cvkit.themes import ats, minimal

EXAMPLE = Path(__file__).parent.parent / "example"
GOLDEN = Path(__file__).parent / "golden"


def data():
    return json.loads((EXAMPLE / "cv.json").read_text())


def test_plain():
    assert plain("S&atilde;o Paulo &amp; Lisbon (2021&ndash;2024)") == "Sao Paulo & Lisbon (2021-2024)"


def test_split_location():
    assert split_location("Lisbon (Mar 2021&ndash;present)") == ("Lisbon", "Mar 2021&ndash;present")
    assert split_location("Remote") == ("Remote", "")


def test_designed_page_links():
    page = minimal.render(data())
    assert 'href="https://example.com" target="_blank" rel="noopener">Example Logistics</a>' in page
    assert '>Python</a>, SQL, C' in page
    assert '<a class="plain-link" href="https://kernel.org" target="_blank" rel="noopener">Linux</a> (Debian)' in page


def test_ats_page_is_plain():
    page = ats.render(data())
    body = page.split("<body>")[1]
    assert "plain-link" not in body
    assert "Sao Paulo & Lisbon" in body
    assert "<h3>Data Engineer, Example Logistics | Mar 2021-present</h3>" in body


def test_golden(tmp_path):
    shutil.copy(EXAMPLE / "cv.json", tmp_path / "cv.json")
    build(tmp_path)
    assert (tmp_path / "index.html").read_text() == (GOLDEN / "index.html").read_text()
    assert (tmp_path / "ats" / "index.html").read_text() == (GOLDEN / "ats.html").read_text()
