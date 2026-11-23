# cvkit

Build a minimal CV site and an ATS-friendly version from one data file, and host it free on GitHub Pages. Later
phases add a PDF and a model that runs on your own computer (Gemma 4 through Ollama) to help write and tailor the CV.

Status: phase 1 done (the engine). See [docs/PLAN.md](docs/PLAN.md).

## Use

```bash
uvx --from git+https://github.com/noah-42/cvkit cvkit build path/to/site
```

The site folder holds `cv.json` (or `cv_data.json`). The command writes `index.html` (the designed page) and
`ats/index.html` (the ATS page). [example/cv.json](example/cv.json) is a full example of an invented person; the
`site` block holds the page head, navigation icons, automatic links, contact links and section titles.

First user: [noah-42.github.io](https://github.com/noah-42/noah-42.github.io).

## Tests

```bash
uv run --no-project --with pytest python -m pytest -q tests
```
