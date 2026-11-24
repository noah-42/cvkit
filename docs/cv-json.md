# cv.json

One file holds the whole CV. The starter file (from the template or `cvkit init`) is a complete example of an
invented person; change it rather than starting empty. A [JSON Resume](https://jsonresume.org) file also works as
`cv.json` (cvkit converts it when building), and `cvkit export-jsonresume` writes one out.

Text fields may use HTML entities such as `&amp;` and `&ndash;`; the ATS page turns them into plain text.

## Content

| Field | Example | Notes |
|---|---|---|
| `headline` | `"Data engineer who builds calm, reliable pipelines"` | One line under your name |
| `summary` | `["Seven years building data pipelines.", "..."]` | A short list |
| `projects` | `[{"name": "Tidewatch", "desc": "...", "url": "https://...", "desc_links": {"Python": "https://..."}}]` | `"hidden": true` leaves one out |
| `experience` | see below | Newest first |
| `education` | `[{"heading_parts": [{"text": "BA Design"}, {"text": "Sample Academy", "url": "https://..."}], "location": "Breda (2013&ndash;2016)"}]` | |
| `skills` | `[{"label": "Tools", "items": ["git", "Linux (Debian)"]}]` | Groups of items |
| `languages` | `"Portuguese (native), English (fluent)"` | One line |
| `contact.lines` | `["GitHub: github.com/ana-example", "Web: ana.example.com"]` | `Label: shown text` |

An experience entry:

```json
{
  "heading_parts": [{"text": "Data Engineer"}, {"text": "Example Logistics", "url": "https://example.com"}],
  "location": "Lisbon (Mar 2021&ndash;present)",
  "bullets": ["Moved 40 nightly jobs to one scheduler, cutting failures by half."]
}
```

The first heading part is the job title, the rest the employer. `location` is `City (start&ndash;end)`, with dates
written as `Mon YYYY` or `YYYY`, and `present` for a current job.

## Page settings: `site`

| Field | What it does |
|---|---|
| `name` | Your name: page title and heading (required) |
| `description` | The page's meta description |
| `url` | Your site's address, used in the JSON-LD |
| `head` | Extra tags for the page head, e.g. the stylesheet link |
| `nav` | Icons next to your name: `[{"label": "GitHub", "url": "...", "icon": "github"}]`; `icon` is `github` or an image address |
| `sections` | Rename headings on the designed page, e.g. `{"projects": "Side projects"}` |
| `autolink` | Links added on the designed page only: `bullet_links` and `skill_links` (`{"text": "url"}`), `skill_links_partial`, `summary` and `bullet_replacements` (`[{"find": "...", "replace": "<a ...>...</a>"}]`) |
| `contact.urls` | Where each contact line's shown text links to: `{"ana.example.com": "https://ana.example.com"}` |
| `contact.icons` | Show a contact line as an icon: `{"GitHub": "github"}` |
| `ats.contact_line` | The line under your name on the ATS page and PDF: `["Lisbon", "github.com/ana-example"]` |
| `ats.contact_list` | The ATS page's contact section |
| `ats.sections` | Rename headings on the ATS page |
| `jsonld` | `false` leaves out the schema.org block (on by default) |
| `pdf` | `true` links `cv.pdf` from the ATS page |
| `print` | PDF settings: `{"font": "mono" or "sans", "start_pt": 10.5, "min_pt": 10, "max_pages": 2}`. `cvkit pdf` shrinks the type 0.5pt at a time to fit `max_pages`, never below `min_pt` |

## Files next to cv.json

| File | Committed | What it is |
|---|---|---|
| `css/style.css` | yes | The designed page's look |
| `templates/*.html.j2` | yes | Your own page layout (optional) |
| `tailored/<slug>.json` | yes | A tailored version you chose to publish (`cvkit tailor --publish`) |
| `private.json` | never | Phone, address for your own PDF: `{"contact_line": [...], "contact_list": [...]}` |
| `private/` | never | Private PDF and private tailored versions |
| `cv.json.bak` | never | The previous file, after `polish` or `interview` |
