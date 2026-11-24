# cvkit

One data file, `cv.json`, becomes a minimal designed CV page, a plain ATS page and a PDF, published free on GitHub
Pages. A later phase adds a model that runs on your own computer (Gemma 4 through Ollama) to help write and tailor
the CV. Status: v0.5.0, all five phases of the [plan](docs/PLAN.md) done. MIT licence.

**New here?** Read [Getting started](docs/getting-started.md). The data file is described in [cv.json](docs/cv-json.md). See [docs/PLAN.md](docs/PLAN.md).

## Start a CV site

Easiest: open [cvkit-template](https://github.com/noah-42/cvkit-template), click **Use this template**, name the
repository `<your-username>.github.io`, set Settings → Pages → Source to **GitHub Actions**, edit `cv.json`, push.

Or locally:

```bash
uvx --from git+https://github.com/noah-42/cvkit cvkit init my-cv
```

## Commands

| Command | What it does |
|---|---|
| `cvkit init [dir] [--theme paper]` | Starter files: example `cv.json`, theme CSS, `.gitignore`, the GitHub Pages workflow |
| `cvkit theme minimal\|paper` | Switches the designed page's theme (old CSS kept as `style.css.bak`) |
| `cvkit check [--job ad.txt]` | Checks the data (names fields, never quotes them); with `--job`, which of the ad's keywords the CV has |
| `cvkit build [--out dir]` | Writes `index.html` (designed, with schema.org JSON-LD) and `ats/index.html` |
| `cvkit pdf [--private]` | Prints the ATS page (set `site.pdf: true` to link it from the ATS page) to `cv.pdf` with Chrome/Chromium; `--private` adds `private.json` lines into `private/cv.pdf` |
| `cvkit serve` | Builds into a temporary folder and serves it on `127.0.0.1:8000` |
| `cvkit export-jsonresume` | Prints the data as [JSON Resume](https://jsonresume.org) |
| `cvkit import old.pdf` | Turns an old CV (PDF, .txt, .md) into `cv.json` with a model on your own computer |
| `cvkit polish [--job N]` | The local model suggests stronger bullets; you accept or reject each one |
| `cvkit interview` | Asks about gaps (missing dates, jobs without bullets, no headline) and adds your answers |
| `cvkit tailor job.txt [--publish]` | A version for one job ad: your own items chosen and reordered, nothing added |

### Import with a local model

`cvkit import` sends the old CV's text to [Ollama](https://ollama.com) on this computer only (default model
`gemma4`; `--model gemma4:12b` for the larger one) and refuses any other host unless you pass `--allow-remote`. The
model only copies facts; cvkit then checks every fact against the old CV's text. Anything it cannot find there is
left out: in a terminal you are asked about each one, otherwise they are listed in `cv.flagged.json`. If `cv.json`
already exists, the result goes to `cv.imported.json`.

`cvkit polish` and `cvkit interview` use the same local model. A suggestion may never contain a number or a name
that is not in the text it came from (the old bullet, or your own answer); suggestions that break this are dropped
and named. Nothing changes in `cv.json` until you accept, and the previous file is kept as `cv.json.bak`. Outside a
terminal, `polish` writes its suggestions to `cv.polish.json` and changes nothing.

### Tailoring to a job ad

`cvkit tailor job.txt --slug acme` asks the local model to rank your CV's items for that ad. The model returns item
ids only, never text, so a tailored version cannot contain anything that is not in `cv.json`. Code then keeps the
chosen summary lines, bullets and projects (most relevant first), keeps every job with at least one bullet, and
reorders skills without removing any. It reports how many of the ad's keywords the CV has before and after, and
which are missing (add them only if they are true).

Where you apply is personal, so a tailored version is private by default: pages, PDF and data go to
`private/tailored/<slug>/`, which is git-ignored. With `--publish` it is saved as `tailored/<slug>.json` and
published at `/cv/<slug>/`, marked `noindex` and without JSON-LD; remember the repository itself is public.

### PDF length and font size

`site.print` in `cv.json` controls the PDF: `font` (`mono` or `sans`), `start_pt` (10.5), `min_pt` (the smallest font
size allowed) and `max_pages`. `cvkit pdf` starts at `start_pt` and goes down 0.5pt at a time until the CV fits in
`max_pages`, never below `min_pt`; if it still does not fit, it says so and keeps `min_pt`. It always reports the page
count and font size, with a note when they pass the recommended values (at least 10pt, at most 2 pages). The starter
`cv.json` uses those values; `--font`, `--min-pt` and `--max-pages` override them for one run.

A [JSON Resume](https://jsonresume.org) file also works as `cv.json` directly. Layout lives in Jinja2 templates
(`cvkit/templates/`); put a file of the same name in your site's `templates/` folder to override it.

First user: [noah-42.github.io](https://github.com/noah-42/noah-42.github.io).

## Tests

```bash
uv run --no-project --with pytest --with jinja2 --with-editable . python -m pytest -q tests
```

## Licence

MIT. See [LICENSE](LICENSE).
