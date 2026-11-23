# cvkit

One data file, `cv.json`, becomes a minimal designed CV page, a plain ATS page and a PDF, published free on GitHub
Pages. A later phase adds a model that runs on your own computer (Gemma 4 through Ollama) to help write and tailor
the CV. Status: phase 2 done. See [docs/PLAN.md](docs/PLAN.md).

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
| `cvkit init [dir]` | Starter files: example `cv.json`, theme CSS, `.gitignore`, the GitHub Pages workflow |
| `cvkit check [--job ad.txt]` | Checks the data (names fields, never quotes them); with `--job`, which of the ad's keywords the CV has |
| `cvkit build [--out dir]` | Writes `index.html` (designed, with schema.org JSON-LD) and `ats/index.html` |
| `cvkit pdf [--private]` | Prints the ATS page to `cv.pdf` with Chrome/Chromium; `--private` adds `private.json` lines into `private/cv.pdf` |
| `cvkit serve` | Builds into a temporary folder and serves it on `127.0.0.1:8000` |
| `cvkit export-jsonresume` | Prints the data as [JSON Resume](https://jsonresume.org) |

A [JSON Resume](https://jsonresume.org) file also works as `cv.json` directly. Layout lives in Jinja2 templates
(`cvkit/templates/`); put a file of the same name in your site's `templates/` folder to override it.

First user: [noah-42.github.io](https://github.com/noah-42/noah-42.github.io).

## Tests

```bash
uv run --no-project --with pytest --with jinja2 --with-editable . python -m pytest -q tests
```
