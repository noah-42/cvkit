# Getting started

cvkit turns one data file, `cv.json`, into a designed CV page, a plain ATS page and a PDF, and publishes them on
GitHub Pages. A model on your own computer can help you write it; nothing you type is sent anywhere else.

## 1. Make your site (no installs)

1. Open [cvkit-template](https://github.com/noah-42/cvkit-template) and click **Use this template**.
2. Name the new repository `<your-username>.github.io`. (Any other name works too; the site is then at
   `<your-username>.github.io/<name>/`.)
3. In the new repository: **Settings → Pages → Source: GitHub Actions**.
4. Edit `cv.json` on GitHub and commit. After a minute or two your CV is live at `https://<your-username>.github.io/`,
   with the ATS page at `/ats/` and the PDF at `/cv.pdf`.

If the Action fails, its log names the problem: usually a field in `cv.json` (`cvkit check` explains each one).

## 2. Work on it on your computer

You need [uv](https://docs.astral.sh/uv/) (one command to install). Then, in your site folder:

```bash
uvx --from git+https://github.com/noah-42/cvkit cvkit serve
```

opens a preview at http://127.0.0.1:8000. Other commands:

```bash
uvx --from git+https://github.com/noah-42/cvkit cvkit check
```

```bash
uvx --from git+https://github.com/noah-42/cvkit cvkit pdf
```

`cvkit pdf` needs Google Chrome or Chromium installed.

Starting without the template: `cvkit init my-cv` (or `cvkit init my-cv --theme paper`) creates the same files.

## 3. Let a local model help (optional)

Install [Ollama](https://ollama.com), then get Gemma 4 (about 10 GB; 16 GB of memory is comfortable):

```bash
ollama pull gemma4
```

| Command | What it does |
|---|---|
| `cvkit import old_cv.pdf` | Copies the facts from an old CV into `cv.json` |
| `cvkit interview` | Asks about what is missing and turns your answers into bullets |
| `cvkit polish` | Suggests stronger wording for each bullet |
| `cvkit tailor job.txt --slug acme` | A version of your CV for one job ad |

The model never gets the last word. Every fact `import` copies is checked against your old CV; `polish` and
`interview` may not add a number or a name that you did not write; `tailor` can only choose and reorder what is
already there. You accept each change, and the previous `cv.json` is kept as `cv.json.bak`.

Tailored versions stay in the `private/` folder, which is never committed, unless you pass `--publish`.

## 4. Keep private things private

- Your repository and site are public. Put only what you would print on a CV in `cv.json`.
- A phone number or address for your own PDF goes in `private.json` (never committed) and is used only by
  `cvkit pdf --private`, which writes `private/cv.pdf`.
- `cvkit check` stops with an error if `private.json` is not git-ignored.

## 5. Change the look

- `cvkit theme paper` (or `minimal`) swaps `css/style.css`; the old file is kept as `style.css.bak`.
- Or edit `css/style.css` yourself.
- To change the page structure, copy a template from cvkit's `cvkit/templates/` into a `templates/` folder in your
  site; your copy is used instead.

The data file is described in [cv-json.md](cv-json.md).
