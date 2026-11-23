# cvkit plan

Status: phase 2 done, Mon, 23-Nov-2026.

## Goal

An open-source CV builder that people run themselves. One data file, `cv.json`, builds three outputs and hosts them
free on GitHub Pages at `<user>.github.io`. A local model (Gemma 4 through Ollama by default) helps write and tailor
the CV on the user's own computer; no CV text leaves the machine.

It starts from how [noah-42.github.io](https://github.com/noah-42/noah-42.github.io) already works: `build.py` turns
one `cv_data.json` into a designed page (`index.html`) and a plain ATS page (`ats/index.html`).

## What the user gets

- **Designed page:** minimal, styled like noah-42.github.io, with links.
- **ATS page:** single column, plain text, standard headings ("Experience", "Education", "Skills"), no tables or
  icons.
- **PDF:** made from a print stylesheet from the same data.
- **schema.org `Person` block** (JSON-LD) on the designed page, so search engines and AI agents can read the CV
  directly.

## How it fits together

- **The model writes, the code decides.** Gemma only proposes text. Building pages, checking data and ATS checks are
  ordinary code, so results are repeatable.
- **Data format: [JSON Resume](https://jsonresume.org)**, plus a few extra fields (company links, projects,
  languages). Existing LinkedIn exporters and themes keep working with it.
- **A Python command-line tool**, installed with `uvx cvkit` or `pip`. Templates in Jinja2; themes are plain CSS.
- **Model adapter** for Ollama's local API (`localhost:11434`); the same adapter covers LM Studio and llama.cpp.
  Ollama's JSON-schema output mode makes the model return valid `cv.json` pieces, not free text.
- **GitHub template repo:** "Use this template", name the repo `<user>.github.io`. A GitHub Action checks and builds
  on every push. The model never runs in GitHub, only on the user's computer.

## Commands

| Command | What it does | Uses the model |
|---|---|---|
| `cvkit init` | Creates `cv.json` and the site folder | no |
| `cvkit import old_cv.pdf` | Old CV, pasted text or LinkedIn export into `cv.json` | yes |
| `cvkit interview` | Asks questions to fill gaps (dates, results, skills) | yes |
| `cvkit polish` | Suggests stronger bullets (action and result); user accepts or rejects each | yes |
| `cvkit tailor job.txt` | A version for one job ad: chooses and reorders facts, never adds new ones | yes |
| `cvkit check` | Checks format, dates, missing contact, ATS problems; keyword overlap with a job ad | keyword score only |
| `cvkit build` / `serve` | Builds the three outputs; local preview | no |
| `cvkit publish` | Commits and pushes to the Pages repo | no |

## Keeping the model honest

A small model can invent facts, so:

1. Every change the model suggests is shown as a diff and lands in `cv.json` only when the user accepts it.
2. `import` and `interview` record where each fact came from. Facts with no source are flagged, never added quietly.
3. `tailor` may only choose, reorder and reword existing facts. A test fails if a tailored version holds a fact that
   is not in `cv.json`.

## Privacy

- Phone, home address and date of birth go in `private.json`, which is never committed. Used only for the PDF; never
  on the public pages.
- No tracking data is sent. The model runs only on the user's machine.

## Phases

1. **Pull out the engine.** Turn `build.py` into a general renderer and move noah-42.github.io onto it as the first
   user. Done when the site's pages match today's output.
2. **Data format and outputs.** JSON Resume plus the extra fields, the designed and ATS themes, JSON-LD, the
   print/PDF stylesheet, `check`, the template repo and the GitHub Action. No model yet, already useful.
3. **Local model.** The Ollama adapter, `import`, `interview` and `polish` with diffs to approve; Gemma 4 as default,
   with a recommended model size for 8 GB and 16 GB machines.
4. **Tailoring.** `tailor` and the job-ad keyword check. Tailored versions go to `/cv/<slug>/`, marked `noindex`.
5. **Release.** MIT licence, docs, example CVs of invented people, a second theme, a launch post.

## Tests

- Golden-file tests per theme: the same `cv.json` always produces the same HTML.
- A set of test CVs of invented people (never real ones) to measure import accuracy and the "no invented facts" rule
  per model.
- The ATS page is run through one or two open-source CV parsers to confirm names, dates and job titles come out right.

## Change log

- Mon, 23-Nov-2026: plan written; repo created.
- Mon, 23-Nov-2026: phase 1 done. The engine (`cvkit build`) renders noah-42.github.io byte-for-byte the same as
  its old `build.py`; all its hard-coded links and page settings moved into `cv_data.json` under `site`. Themes are
  plain Python f-strings for now; moving them to Jinja2 is part of phase 2.
- Mon, 23-Nov-2026: phase 2 done (v0.2.0). Jinja2 templates (a site's `templates/` folder overrides them); JSON Resume
  import (a JSON Resume file works as `cv.json`) and `export-jsonresume`; schema.org JSON-LD on the designed page
  (`site.jsonld: false` turns it off); print CSS and `cvkit pdf` through a local Chrome/Chromium (no Playwright
  dependency: GitHub's runners already have Chrome); `private.json` lines reach only the local `--private` PDF;
  `cvkit check` with `--job` keyword overlap; `cvkit init` and `serve`; the Pages workflow and the public template
  repo `noah-42/cvkit-template`.
- Mon, 23-Nov-2026: v0.2.1. The Pages workflow pins `astral-sh/setup-uv@v10.4.0`; that action publishes no `v10` tag,
  so the first template run failed at setup.
- Mon, 23-Nov-2026: v0.2.2. `site.pdf: true` links `cv.pdf` from the ATS page (on screen only; never in a `--private`
  PDF). On in the starter `cv.json`.
