"""tailor tests: the invented starter CV and an invented job ad; stand-in models; never a real CV or application.
The live test runs only with CVKIT_LIVE=1 and a local Ollama."""
import json
import os
from pathlib import Path

import pytest

from cvkit import cli
from cvkit.build import build, render_pages
from cvkit.init import init
from cvkit.tailor import apply_ranking, items, prompt, slugify, tailor

STARTER = Path(__file__).parent.parent / "cvkit" / "scaffold" / "cv.json"
JOB = (Path(__file__).parent / "fixtures" / "job_ad.txt").read_text()


def data():
    d = json.loads(STARTER.read_text())
    d["experience"][0]["bullets"].append("Ran the office book club.")
    d["skills"][1]["items"].append("Airflow")
    return d


RANKED = {"summary": ["s0"], "bullets": ["e0b1", "e0b0", "e9b9", "made up"],
          "projects": [], "skills": ["k1i2", "k0i0", "k0i1"]}


class Fake:
    model, host = "fake", "http://localhost:11434"

    def __init__(self, answer=RANKED):
        self.answer = answer

    def json(self, system, user, schema):
        assert "JOB AD:" in user and "[e0b0]" in user and "ids only" in system
        return self.answer


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def test_items_and_prompt():
    it = items(data())
    assert it["e0b2"] == "Ran the office book club." and it["k1i2"] == "Tools: Airflow"
    assert "Job 1: Analyst, Sample Health" in prompt(data(), JOB)


def test_ranking_applied():
    t = apply_ranking(data(), RANKED)
    assert t["summary"] == [data()["summary"][0]]
    assert t["experience"][0]["bullets"] == [data()["experience"][0]["bullets"][1], data()["experience"][0]["bullets"][0]]
    assert len(t["experience"]) == 2  # every job stays
    assert t["projects"] == data()["projects"]  # nothing chosen: unchanged
    assert t["skills"][0]["label"] == "Tools" and t["skills"][0]["items"][0] == "Airflow"
    assert sorted(t["skills"][0]["items"]) == sorted(data()["skills"][1]["items"])  # nothing removed
    assert t["site"]["noindex"] is True


def test_unchosen_job_keeps_one_bullet():
    d = data()
    d["experience"][1]["bullets"] = ["Built reports.", "Ran workshops."]
    t = apply_ranking(d, {"summary": [], "bullets": ["e0b0"], "projects": [], "skills": []})
    assert t["experience"][1]["bullets"] == ["Built reports."]


def test_tailored_never_contains_new_text():
    original = set(strings(data()))
    for ranked in (RANKED, {"summary": ["s9", "x"], "bullets": ["e0b0e0b1", "[e0b1]"], "projects": ["p0", "p0"],
                            "skills": ["k9i9"]}):
        t = apply_ranking(data(), ranked)
        t["site"].pop("noindex")
        assert set(strings(t)) <= original


def test_tailored_pages_are_noindex_without_jsonld(tmp_path):
    p = render_pages(tmp_path, apply_ranking(data(), RANKED))
    assert '<meta name="robots" content="noindex, nofollow" />' in p["index.html"]
    assert "ld+json" not in p["index.html"]
    assert "noindex" in p["ats/index.html"]
    assert "noindex" not in render_pages(tmp_path, data())["index.html"]


def test_slugify():
    assert slugify("Data Engineer @ Freight Co. (Berlin)") == "data-engineer-freight-co-berlin"


def test_cli_tailor_private_by_default(tmp_path, monkeypatch, capsys):
    init(tmp_path)
    (tmp_path / "ad.txt").write_text(JOB)
    monkeypatch.setattr("cvkit.llm.Ollama", lambda *a, **k: Fake())
    assert cli.main(["tailor", str(tmp_path / "ad.txt"), "--root", str(tmp_path), "--slug", "freight", "--no-pdf"]) == 0
    folder = tmp_path / "private" / "tailored" / "freight"
    assert (folder / "index.html").exists() and (folder / "ats" / "index.html").exists() and (folder / "css").is_dir()
    assert not (tmp_path / "tailored").exists() and not (tmp_path / "cv").exists()
    out = capsys.readouterr().out
    assert "private" in out and "job ad keywords" in out


def test_cli_tailor_publish_and_build(tmp_path, monkeypatch):
    init(tmp_path)
    (tmp_path / "ad.txt").write_text(JOB)
    monkeypatch.setattr("cvkit.llm.Ollama", lambda *a, **k: Fake())
    assert cli.main(["tailor", str(tmp_path / "ad.txt"), "--root", str(tmp_path), "--publish", "--no-pdf"]) == 0
    assert (tmp_path / "tailored" / "ad.json").exists()
    build(tmp_path, out=tmp_path / "_site")
    assert "noindex" in (tmp_path / "_site" / "cv" / "ad" / "index.html").read_text()
    assert (tmp_path / "_site" / "cv" / "ad" / "css" / "style.css").exists()


@pytest.mark.skipif(os.environ.get("CVKIT_LIVE") != "1", reason="set CVKIT_LIVE=1 to run against a local Ollama")
def test_live_tailor_on_invented_cv():
    from cvkit.check import keyword_overlap
    from cvkit.llm import Ollama
    d = data()
    t = tailor(Ollama(), d, JOB)
    kept = [b for e in t["experience"] for b in e["bullets"]]
    print(f"\nbullets kept: {kept}\nskills order: {[s['items'] for s in t['skills']]}")
    print(f"keywords before {len(keyword_overlap(d, JOB)[0])}, after {len(keyword_overlap(t, JOB)[0])}")
    assert "Ran the office book club." not in kept
    t["site"].pop("noindex")
    assert set(strings(t)) <= set(strings(d))
