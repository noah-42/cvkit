"""Tests use the invented person in the starter cv.json only, never a real CV."""
import json
import shutil
from pathlib import Path

import pytest

from cvkit.build import build, render_pages
from cvkit.check import check, keyword_overlap
from cvkit.init import init
from cvkit.jsonresume import from_jsonresume, jsonld, parse_range, to_jsonresume
from cvkit.text import plain, split_location

STARTER = Path(__file__).parent.parent / "cvkit" / "scaffold"
GOLDEN = Path(__file__).parent / "golden"


def data():
    return json.loads((STARTER / "cv.json").read_text())


def pages(tmp_path, d=None, private=None):
    return render_pages(tmp_path, d or data(), private)


def test_plain():
    assert plain("S&atilde;o Paulo &amp; Lisbon (2021&ndash;2024)") == "Sao Paulo & Lisbon (2021-2024)"


def test_split_location():
    assert split_location("Lisbon (Mar 2021&ndash;present)") == ("Lisbon", "Mar 2021&ndash;present")
    assert split_location("Remote") == ("Remote", "")


def test_designed_page_links(tmp_path):
    page = pages(tmp_path)["index.html"]
    assert 'href="https://example.com" target="_blank" rel="noopener">Example Logistics</a>' in page
    assert ">Python</a>, SQL, C" in page
    assert '<a class="plain-link" href="https://kernel.org" target="_blank" rel="noopener">Linux</a> (Debian)' in page


def test_ats_page_is_plain(tmp_path):
    body = pages(tmp_path)["ats/index.html"].split("<body>")[1]
    assert "plain-link" not in body
    assert "Sao Paulo & Lisbon" in body
    assert "<h3>Data Engineer, Example Logistics | Mar 2021-present</h3>" in body


def test_private_lines_only_when_asked(tmp_path):
    private = {"contact_line": ["+00 0000"], "contact_list": ["Phone: +00 0000"]}
    assert "+00 0000" not in pages(tmp_path)["ats/index.html"]
    assert "Phone: +00 0000" in pages(tmp_path, private=private)["ats/index.html"]


def test_jsonld(tmp_path):
    page = pages(tmp_path)["index.html"]
    assert '<script type="application/ld+json">' in page
    person = json.loads(jsonld(data()))
    assert person["@type"] == "Person" and person["name"] == "Ana Example"
    assert person["worksFor"] == [{"@type": "Organization", "name": "Example Logistics", "url": "https://example.com"}]
    assert "Python" in person["knowsAbout"]
    assert person["knowsLanguage"] == ["Portuguese", "English"]


def test_jsonld_can_be_turned_off(tmp_path):
    d = data()
    d["site"]["jsonld"] = False
    assert "ld+json" not in pages(tmp_path, d)["index.html"]


def test_dates():
    assert parse_range("Mar 2021&ndash;present") == ("2021-03", None)
    assert parse_range("Jan 2018&ndash;Feb 2021") == ("2018-01", "2021-02")
    assert parse_range("2019") == ("2019", "2019")


def test_jsonresume_round_trip(tmp_path):
    resume = to_jsonresume(data())
    assert resume["work"][0]["startDate"] == "2021-03" and "endDate" not in resume["work"][0]
    back = from_jsonresume(resume)
    assert back["experience"][0]["location"] == "Lisbon (Mar 2021&ndash;present)"
    assert back["experience"][1]["heading_parts"] == [{"text": "Analyst"}, {"text": "Sample Health"}]
    page = pages(tmp_path, back)["ats/index.html"]
    assert "<h3>Data Engineer, Example Logistics | Mar 2021-present</h3>" in page


def test_build_reads_jsonresume_file(tmp_path):
    (tmp_path / "cv.json").write_text(json.dumps(to_jsonresume(data())))
    build(tmp_path)
    assert "Ana Example" in (tmp_path / "index.html").read_text()


def test_check_clean_starter(tmp_path):
    assert [i for i in check(tmp_path, data()) if i[0] == "error"] == []


def test_check_finds_problems(tmp_path):
    d = data()
    del d["site"]["name"]
    assert ("error", "site.name") in [(l, p) for l, p, _ in check(tmp_path, d)]
    d = data()
    d["experience"][0]["location"] = "Lisbon"
    d["contact"]["lines"].append("no colon here")
    found = {(l, p) for l, p, _ in check(tmp_path, d)}
    assert ("warn", "experience[0].location") in found
    assert ("error", "contact.lines[2]") in found


def test_check_never_quotes_contents(tmp_path):
    d = data()
    d["experience"][0]["bullets"].append("<b>SECRET-VALUE</b>")
    assert not any("SECRET-VALUE" in msg or "SECRET-VALUE" in path for _, path, msg in check(tmp_path, d))


def test_keyword_overlap():
    job = "We need Python and SQL. Python daily. Kubernetes and Kubernetes clusters."
    found, missing = keyword_overlap(data(), job)
    assert "python" in found and "sql" in found and "kubernetes" in missing


def test_init_and_build(tmp_path):
    init(tmp_path)
    assert (tmp_path / ".github" / "workflows" / "pages.yml").exists()
    assert (tmp_path / ".gitignore").exists() and (tmp_path / "css" / "style.css").exists()
    with pytest.raises(FileExistsError):
        init(tmp_path)
    build(tmp_path, out=tmp_path / "_site")
    assert (tmp_path / "_site" / "css" / "style.css").exists()


def test_golden(tmp_path):
    shutil.copy(STARTER / "cv.json", tmp_path / "cv.json")
    build(tmp_path)
    assert (tmp_path / "index.html").read_text() == (GOLDEN / "index.html").read_text()
    assert (tmp_path / "ats" / "index.html").read_text() == (GOLDEN / "ats.html").read_text()
