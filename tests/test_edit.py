"""polish and interview tests: the invented starter CV, stand-in models and scripted answers; never a real CV.
The live test runs only with CVKIT_LIVE=1 and a local Ollama."""
import json
import os
from pathlib import Path

import pytest

from cvkit import cli
from cvkit.edit import Change, apply, find_gaps, guard, interview, load_raw, polish, save_raw
from cvkit.init import init

STARTER = Path(__file__).parent.parent / "cvkit" / "scaffold" / "cv.json"


def data():
    return json.loads(STARTER.read_text())


class Fake:
    def __init__(self, *answers):
        self.answers, self.calls, self.model, self.host = list(answers), [], "fake", "http://localhost:11434"

    def json(self, system, user, schema):
        self.calls.append(user)
        return self.answers.pop(0)


def test_guard():
    before = "Moved 40 nightly jobs at Example Logistics to one scheduler, cutting failures by half."
    assert guard("Consolidated 40 nightly jobs at Example Logistics into one scheduler, halving failures.", before) is None
    assert "numbers" in guard("Moved 40 nightly jobs to one scheduler, cutting failures by 50%.", before)
    assert "names" in guard("Moved 40 nightly jobs at Example Logistics to Airflow, halving failures.", before)
    assert guard("Moved <b>40</b> jobs at Example Logistics.", before) == "adds HTML"


def test_polish_keeps_good_and_drops_invented():
    model = Fake({"bullets": [
        "Consolidated 40 nightly jobs at Example Logistics into one scheduler, halving failures.",
        "Built the shipment tracking feed used by 300 S&atilde;o Paulo &amp; Lisbon staff.",
    ]})
    changes, dropped = polish(model, data(), only=0)
    assert [c.path for c in changes] == ["experience[0].bullets[0]"]
    assert dropped[0][0] == "experience[0].bullets[1]" and "300" in dropped[0][2]
    assert model.calls[0].startswith("Current job.")


def test_polish_skips_unchanged_and_jobs_without_bullets():
    d = data()
    model = Fake({"bullets": d["experience"][0]["bullets"]})
    changes, dropped = polish(model, d)
    assert changes == [] and dropped == [] and len(model.calls) == 1  # job 1 has no bullets: no call


def test_find_gaps():
    d = data()
    d["headline"] = ""
    d["experience"][1]["location"] = "Porto"
    gaps = {(g.path, g.kind) for g in find_gaps(d)}
    assert gaps == {("headline", "headline"), ("experience[1].location", "dates"), ("experience[1].bullets", "bullets")}


def test_interview_uses_only_the_answer():
    d = data()
    d["experience"][1]["location"] = "Porto"
    model = Fake({"bullets": ["Built weekly sales reports for 12 regional managers.",
                              "Saved the team 2 days a month with Tableau dashboards."]})
    answers = iter(["Jan 2018 - Feb 2021", "y",
                    "I built weekly sales reports for 12 regional managers and saved 2 days a month.", "y"])
    said = []
    changes = interview(model, d, lambda q: next(answers), said.append)
    assert changes[0] == Change("experience[1].location", "Porto", "Porto (Jan 2018&ndash;Feb 2021)")
    assert changes[1].after == ["Built weekly sales reports for 12 regional managers."]
    assert any("tableau" in s for s in said)  # the invented tool was dropped


def test_interview_bad_dates_and_skips():
    d = data()
    d["experience"][1]["location"] = "Porto"
    answers = iter(["sometime in the past", ""])
    said = []
    assert interview(Fake(), d, lambda q: next(answers), said.append) == []
    assert "dates not understood" in said[0]


def test_save_keeps_backup_and_format(tmp_path):
    init(tmp_path)
    path, d = load_raw(tmp_path)
    backup = save_raw(path, apply(d, [Change("experience[0].bullets[0]", "", "New bullet.")]))
    assert json.loads(path.read_text())["experience"][0]["bullets"][0] == "New bullet."
    assert json.loads(backup.read_text())["experience"][0]["bullets"][0] != "New bullet."


def test_cli_polish_without_terminal_writes_suggestions(tmp_path, monkeypatch, capsys):
    init(tmp_path)
    before = (tmp_path / "cv.json").read_text()
    monkeypatch.setattr("cvkit.llm.Ollama", lambda *a, **k: Fake(
        {"bullets": ["Consolidated 40 nightly jobs at Example Logistics into one scheduler, halving failures.",
                     "Built the shipment tracking feed used by S&atilde;o Paulo &amp; Lisbon teams."]}))
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert cli.main(["polish", str(tmp_path)]) == 0
    assert (tmp_path / "cv.json").read_text() == before
    assert len(json.loads((tmp_path / "cv.polish.json").read_text())) == 1


@pytest.mark.skipif(os.environ.get("CVKIT_LIVE") != "1", reason="set CVKIT_LIVE=1 to run against a local Ollama")
def test_live_polish_on_invented_cv():
    from cvkit.llm import Ollama
    model = Ollama()
    changes, dropped = polish(model, data())
    print(f"\n{model.model}: {len(changes)} suggestions kept, {len(dropped)} dropped by the guard")
    for c in changes:
        print(f"  before: {c.before}\n  after:  {c.after}")
    for p, t, why in dropped:
        print(f"  dropped {p}: {why}")
    for c in changes:
        assert guard(c.after, c.before) is None
