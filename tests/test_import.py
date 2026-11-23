"""Import tests use an invented old CV (tests/fixtures/old_cv.txt) and a stand-in model; never a real CV.
The live test runs only with CVKIT_LIVE=1 and a local Ollama."""
import json
import os
from pathlib import Path

import pytest

from cvkit import cli
from cvkit.importer import Checker, check_and_assemble, extract, to_cv
from cvkit.llm import ModelError, Ollama
from cvkit.themes import ats

SOURCE = (Path(__file__).parent / "fixtures" / "old_cv.txt").read_text()

GOOD = {
    "name": "BEN SAMPLE", "headline": "Product designer", "city": "Rotterdam",
    "summary": ["Product designer with eight years of work on booking and payment apps."],
    "experience": [
        {"title": "Senior Product Designer", "employer": "Harbour Travel B.V.", "city": "Rotterdam",
         "start": "March 2021", "end": "present",
         "bullets": ["Redesigned the checkout, which raised completed bookings by 12%.",
                     "Set up a weekly test day with five real customers."]},
        {"title": "Product Designer", "employer": "Example Pay", "city": "Utrecht", "start": "Jan 2017",
         "end": "Feb 2021", "bullets": ["Designed the first version of the Example Pay mobile app."]},
    ],
    "education": [{"qualification": "BA Interaction Design", "institution": "Sample Academy of Arts",
                   "city": "Breda", "start": "2013", "end": "2016"}],
    "projects": [],
    "skills": [{"group": "Design", "items": ["Figma", "prototyping", "user testing"]},
               {"group": "Code", "items": ["HTML", "CSS"]}],
    "languages": [{"language": "Dutch", "fluency": "native"}, {"language": "English", "fluency": "fluent"}],
    "links": [{"label": "LinkedIn", "url": "linkedin.com/in/ben-sample-example"}],
}


def invented():
    """The same answer with three facts the CV never states."""
    d = json.loads(json.dumps(GOOD))
    d["experience"][0]["bullets"].append("Led a team of 40 designers across Europe.")
    d["experience"][1]["employer"] = "Example Payments Group"
    d["education"][0]["end"] = "2018"
    return d


class FakeModel:
    def __init__(self, answer):
        self.answer, self.model, self.host = answer, "fake", "http://localhost:11434"

    def json(self, system, user, schema):
        assert "Here is the CV" in user and "exactly" in system
        return self.answer


def test_checker():
    c = Checker(SOURCE)
    assert c.exact("Harbour Travel B.V.") and c.exact("sample academy of arts") and not c.exact("Harbour Air")
    assert c.prose("Redesigned the checkout which raised completed bookings by 12%")
    assert not c.prose("Led a team of 40 designers across Europe")
    assert c.date("March 2021") and c.date("present") and not c.date("2018")
    assert c.url("https://www.linkedin.com/in/ben-sample-example/")


def test_clean_answer_keeps_everything():
    resume, flags, checked = check_and_assemble(GOOD, SOURCE)
    assert flags == [] and checked > 15
    assert resume["work"][0]["startDate"] == "2021-03" and "endDate" not in resume["work"][0]
    assert resume["work"][1]["endDate"] == "2021-02"


def test_invented_facts_are_flagged_and_left_out():
    resume, flags, _ = check_and_assemble(invented(), SOURCE)
    assert {f.path for f in flags} == {"experience[0].bullets[2]", "experience[1].employer", "education[0].end"}
    assert "Led a team of 40 designers across Europe." not in resume["work"][0]["highlights"]
    assert "name" not in resume["work"][1]
    assert "endDate" not in resume["education"][0]


def test_accepted_flags_are_kept():
    resume, _, _ = check_and_assemble(invented(), SOURCE, frozenset({"experience[1].employer"}))
    assert resume["work"][1]["name"] == "Example Payments Group"


def test_result_builds(tmp_path):
    resume, _, _ = check_and_assemble(GOOD, SOURCE)
    cv = to_cv(resume)
    page = ats.context(cv)
    assert page["experience"][0]["heading"] == "Senior Product Designer, Harbour Travel B.V. | Mar 2021-present"
    assert cv["summary"] == GOOD["summary"]


def test_cli_import_writes_cv_and_flag_file(tmp_path, monkeypatch, capsys):
    src = tmp_path / "old.txt"
    src.write_text(SOURCE)
    monkeypatch.setattr("cvkit.llm.Ollama", lambda *a, **k: FakeModel(invented()))
    assert cli.main(["import", str(src), "--root", str(tmp_path), "--no-ask"]) == 0
    cv = json.loads((tmp_path / "cv.json").read_text())
    assert cv["site"]["name"] == "BEN SAMPLE"
    flagged = json.loads((tmp_path / "cv.flagged.json").read_text())
    assert len(flagged) == 3
    assert "3 left out" in capsys.readouterr().out
    assert cli.main(["import", str(src), "--root", str(tmp_path), "--no-ask"]) == 0  # cv.json exists now
    assert (tmp_path / "cv.imported.json").exists()


def test_remote_host_refused():
    with pytest.raises(ModelError):
        Ollama(host="http://example.com:11434")
    assert Ollama(host="http://example.com:11434", allow_remote=True).host == "http://example.com:11434"


@pytest.mark.skipif(os.environ.get("CVKIT_LIVE") != "1", reason="set CVKIT_LIVE=1 to run against a local Ollama")
def test_live_model_on_invented_cv():
    model = Ollama()
    resume, flags, checked = check_and_assemble(extract(model, SOURCE), SOURCE)
    print(f"\n{model.model}: {checked} facts checked, {len(flags)} flagged: {[f.path for f in flags]}")
    titles = [w["position"] for w in resume["work"]]
    assert "Senior Product Designer" in titles and "Product Designer" in titles
    assert len(flags) <= 3


def test_model_retries_once_when_answer_is_not_json(monkeypatch):
    replies = iter([{"message": {"content": "* Built a weekly report."}},
                    {"message": {"content": "```json\n{\"bullets\": [\"Built a weekly report.\"]}\n```"}}])
    sent = []
    m = Ollama()
    monkeypatch.setattr(m, "_post", lambda path, body: sent.append(body) or next(replies))
    assert m.json("sys", "user", {"type": "object"}) == {"bullets": ["Built a weekly report."]}
    assert "Reply with JSON only" in sent[1]["messages"][0]["content"]
    replies2 = iter([{"message": {"content": "nope"}}, {"message": {"content": ""}}])
    monkeypatch.setattr(m, "_post", lambda path, body: next(replies2))
    with pytest.raises(ModelError):
        m.json("sys", "user", {"type": "object"})
