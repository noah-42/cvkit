"""`cvkit polish` and `cvkit interview`: the local model suggests wording, you decide.

polish: the model rewrites each experience bullet (strong verb first, result stated) without adding facts.
interview: cvkit finds gaps in cv.json (missing dates, jobs without bullets, no headline) and asks you about them;
the model only turns your own answers into bullets.

Both use the same guard: a suggestion may not contain a number or a name that is not in the text it came from
(the old bullet, or your answer). Suggestions that fail the guard are dropped, never shown as if they were fine.
Nothing is written to the data file until you accept it; the old file is kept as <name>.bak.
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .build import find_data
from .importer import norm
from .jsonresume import format_date, parse_date
from .text import plain, split_location

S = {"type": "string"}
POLISH_SCHEMA = {"type": "object", "properties": {"bullets": {"type": "array", "items": S}}, "required": ["bullets"]}
POLISH_SYSTEM = """You improve CV bullet points. For each bullet you get, return one improved bullet, in the same order.
Rules:
- Start with a strong past-tense verb (or present tense for a current job). State the result if the bullet has one.
- Keep every fact exactly as it is: the same numbers, names, products and places. Never add a number, a name, a
  result, a team size or a tool that is not in that bullet.
- Keep it to one line. Keep HTML entities such as &amp; and &ndash; as they are.
- If a bullet is already good, return it unchanged."""
DRAFT_SCHEMA = POLISH_SCHEMA
DRAFT_SYSTEM = """You write CV bullet points from a person's own answer about one job. Rules:
- Use only facts in the answer. Never add a number, a name, a result, a team size or a tool the answer does not give.
- Keep every number and result the answer gives; the result is the most important part of a bullet.
- One to three bullets, each one line, starting with a strong verb and ending with the result. Past tense for past
  jobs."""

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NAME = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-Z][A-Za-z0-9&+.-]*")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(plain(text))}


def _names(text: str) -> set[str]:
    """Capitalised words that are not the first word of a sentence, e.g. product, company and place names."""
    return {norm(m) for m in _NAME.findall(plain(text)) if norm(m)}


def guard(suggestion: str, allowed: str) -> str | None:
    """None when `suggestion` adds nothing to `allowed`; otherwise the reason it was dropped."""
    extra_numbers = _numbers(suggestion) - _numbers(allowed)
    if extra_numbers:
        return f"adds numbers not in the original: {', '.join(sorted(extra_numbers))}"
    known = set(norm(plain(allowed)).split())
    extra_names = {n for n in _names(suggestion) if not set(n.split()) <= known}
    if extra_names:
        return f"adds names not in the original: {', '.join(sorted(extra_names))}"
    if _TAG.search(suggestion) and not _TAG.search(allowed):
        return "adds HTML"
    if len(suggestion) > max(2 * len(allowed), len(allowed) + 120):
        return "much longer than the original"
    return None


_TAG = re.compile(r"<[a-zA-Z/][^>]*>")


@dataclass
class Change:
    path: str          # e.g. experience[2].bullets[0]
    before: str
    after: str


# ---------- data file ----------

def load_raw(root: Path, data_path: Path | None = None) -> tuple[Path, dict]:
    path = data_path or find_data(root)
    data = json.loads(path.read_text())
    if "basics" in data and "experience" not in data:
        raise RuntimeError("this works on cvkit's own format; a JSON Resume file can be built but not edited here "
                           "(run `cvkit export-jsonresume` the other way round first)")
    return path, data


def save_raw(path: Path, data: dict) -> Path:
    raw = path.read_text()
    backup = path.with_name(path.name + ".bak")
    shutil.copyfile(path, backup)
    ascii_only = all(ord(c) < 128 for c in raw)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=ascii_only) + "\n")
    return backup


def _set(data: dict, path: str, value) -> None:
    keys = re.findall(r"[a-z_]+|\[\d+\]", path)
    node = data
    for k in keys[:-1]:
        node = node[int(k[1:-1])] if k.startswith("[") else node[k]
    last = keys[-1]
    if last.startswith("["):
        node[int(last[1:-1])] = value
    else:
        node[last] = value


def apply(data: dict, changes: list[Change]) -> dict:
    for c in changes:
        _set(data, c.path, c.after)
    return data


# ---------- polish ----------

def polish(model, data: dict, only: int | None = None) -> tuple[list[Change], list[tuple[str, str, str]]]:
    """Suggestions for every bullet (or one job with `only`). Returns (changes, dropped as (path, text, reason))."""
    changes: list[Change] = []
    dropped: list[tuple[str, str, str]] = []
    for i, e in enumerate(data["experience"]):
        if only is not None and i != only:
            continue
        bullets = e.get("bullets", [])
        editable = [(j, b) for j, b in enumerate(bullets) if not _TAG.search(b)]
        if not editable:
            continue
        current = "present" in split_location(e["location"])[1].lower()
        answer = model.json(POLISH_SYSTEM, ("Current job. " if current else "Past job. ") + "Bullets:\n"
                            + "\n".join(f"{n + 1}. {b}" for n, (_, b) in enumerate(editable)), POLISH_SCHEMA)
        for (j, before), after in zip(editable, answer.get("bullets", [])):
            after = after.strip().lstrip("-•* ").strip()
            if not after or after == before:
                continue
            path = f"experience[{i}].bullets[{j}]"
            reason = guard(after, before)
            if reason:
                dropped.append((path, after, reason))
            else:
                changes.append(Change(path, before, after))
    return changes, dropped


# ---------- interview ----------

@dataclass
class Gap:
    path: str
    question: str
    kind: str  # "dates" | "bullets" | "headline"


def find_gaps(data: dict) -> list[Gap]:
    gaps = []
    if not data.get("headline"):
        gaps.append(Gap("headline", "In one line, what do you do? (for example: Data engineer who builds reliable "
                        "pipelines)", "headline"))
    for i, e in enumerate(data["experience"]):
        parts = e["heading_parts"]
        job = plain(parts[0]["text"]) + (f" at {plain(parts[1]['text'])}" if len(parts) > 1 else "")
        city, dates = split_location(e.get("location", ""))
        if not dates:
            gaps.append(Gap(f"experience[{i}].location", f"{job}: when did it start and end? "
                            "(for example: Mar 2021 - present)", "dates"))
        if not e.get("bullets"):
            gaps.append(Gap(f"experience[{i}].bullets", f"{job}: what did you do there, and what came of it? "
                            "Numbers help (users, money, time saved).", "bullets"))
    return gaps


def _dates_answer(answer: str) -> str | None:
    parts = re.split(r"\s*(?:-|–|—|to|until)\s*", answer.strip(), maxsplit=1)
    start = parse_date(parts[0])
    if not start:
        return None
    end_text = parts[1] if len(parts) > 1 else ""
    end = None if not end_text or end_text.lower() in {"present", "now", "today", "current"} else parse_date(end_text)
    if end_text and end is None and end_text.lower() not in {"present", "now", "today", "current"}:
        return None
    return f"{format_date(start)}&ndash;{format_date(end)}"


def interview(model, data: dict, ask: Callable[[str], str], say: Callable[[str], None]) -> list[Change]:
    """Asks about each gap. Empty answers skip. Returns the changes the person accepted."""
    accepted: list[Change] = []
    for gap in find_gaps(data):
        answer = ask(gap.question + "\n> ").strip()
        if not answer:
            continue
        if gap.kind == "headline":
            change = Change("headline", "", answer)
        elif gap.kind == "dates":
            span = _dates_answer(answer)
            if not span:
                say("  dates not understood; skipped (write them like 'Mar 2021 - present')")
                continue
            i = int(re.search(r"\[(\d+)\]", gap.path).group(1))
            city, _ = split_location(data["experience"][i].get("location", ""))
            change = Change(gap.path, data["experience"][i].get("location", ""),
                            f"{city} ({span})" if city else f"({span})")
        else:
            draft = model.json(DRAFT_SYSTEM, f"The job: {gap.question.split(':')[0]}\nTheir answer: {answer}",
                               DRAFT_SCHEMA).get("bullets", [])
            kept = []
            for b in draft:
                b = b.strip().lstrip("-•* ").strip()
                reason = guard(b, answer) if b else "empty"
                if reason:
                    say(f"  dropped a draft bullet: {reason}")
                else:
                    kept.append(b)
            if not kept:
                say("  no usable bullets from that answer; skipped")
                continue
            change = Change(gap.path, "", kept)  # type: ignore[arg-type]
        shown = "\n    ".join(change.after) if isinstance(change.after, list) else change.after
        if ask(f"  new: {shown}\n  keep? [y/N] ").strip().lower() == "y":
            accepted.append(change)
    return accepted
