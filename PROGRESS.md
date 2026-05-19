# NFP Article Formatter — Build Progress

**Project:** Novel Future Publishers — JATS XML Article Formatting Tool  
**Repo:** `/Users/kareem/Github/NovelTOR`  
**Last updated:** 2026-05-18 (end of day)

---

## What This Tool Does

A standalone web application for journal editors at Novel Future Publishers Inc. Editors upload a DOCX manuscript, review and clean extracted metadata, tag article sections, and export a standards-compliant JATS XML file plus a PDF galley.

---

## Session Log

### 2026-05-14 — Initial Build (Complete)

#### Backend — Python Flask (`/backend`)

**`app.py`** — Flask REST API with 5 endpoints:
- `GET /health` — health check
- `POST /parse` — accepts `.docx` file upload, returns structured JSON
- `POST /generate` — accepts article JSON, returns JATS XML string
- `POST /validate` — accepts JATS XML string, returns `{valid, errors[], warnings[]}`
- `POST /autotag` — sends raw article text to Claude API, returns AI-suggested section types

**`parser/docx_parser.py`** — DOCX parsing using python-docx:
- Title: first Heading 1 or large bold text
- Authors: block between title and abstract (with heuristic name/affiliation splitting)
- Abstract: paragraph after "Abstract" heading
- Keywords: line matching `Keywords:` pattern
- Sections: Heading 2 = section break, Heading 3 = subsection
- References: numbered list after "References" heading
- Figures: inline image elements with adjacent caption detection

**`jats/generator.py`** — JATS Publishing DTD v1.3 XML generator:
- Produces valid `<?xml ...><!DOCTYPE ...><article>` output
- Builds `<front>` (journal-meta + article-meta), `<body>`, `<back>`
- Authors as `<contrib contrib-type="author">` with name, affiliation, email, ORCID
- Sections as `<sec>` with `<title>` and `<p>` tags
- References as `<ref-list>` with `<ref id="refN"><mixed-citation>`
- Figures in `<back>` with `<label>`, `<caption>`, `<graphic xlink:href>`

**`jats/validator.py`** — Structural + NFP consistency checker (no network required):
- Validates required JATS elements (article-type, xml:lang, journal-meta, article-meta, body, back)
- Enforces 8 NFP rules (author names, corresponding author, abstract word count, keyword count, DOI format, section headings, figure captions, reference numbering)

---

#### Frontend — React + TailwindCSS (`/frontend`)

Built with Vite. TailwindCSS v4 via `@tailwindcss/vite` plugin.

**Screen 1 — Upload (`UploadScreen.jsx`)**
- Drag-and-drop zone + file input for `.docx` files
- Sends file to `/parse`, shows spinner during parsing
- On success: populates article state and advances to Metadata screen
- Error states with inline red message

**Screen 2 — Metadata (`MetadataScreen.jsx`)**
- Article title, article type dropdown (5 types), DOI with format validation
- Abstract textarea with live word count and 150–300 range indicator
- Tag input for keywords (Enter or comma to add, × to remove)
- Repeatable author blocks: first name, last name, email, ORCID, affiliation, corresponding toggle
- Author reorder (↑↓) and remove (✕)
- Journal info: name, publisher, ISSN print/online, volume, issue, year, location
- Dates: received, accepted, published
- Copyright statement field

**Screen 3 — Sections (`SectionsScreen.jsx`)**
- Drag-and-drop section reorder using `@dnd-kit/core` + `@dnd-kit/sortable`
- Each section: heading input, type dropdown (7 types), body textarea
- Inline subsection editor (add/remove subsections per section)
- Blue dot indicator on AI-suggested section type tags
- **AI Auto-tag button**: POSTs to `/autotag` → Claude `claude-sonnet-4-20250514` suggests section types and flags missing required sections
- Figures panel: label, file/href, caption fields; add/remove figures
- References panel: numbered list editor `[1]…[N]`; add/remove references

**Screen 4 — Export (`ExportScreen.jsx`)**
- Tab switcher: Article Preview | JATS XML
- Article Preview: styled HTML rendering with serif font, formatted abstract, section hierarchy, reference list
- JATS XML viewer: syntax-highlighted with navy tags, amber attributes, green values (dark background)
- Validation panel: combines client-side checks + `/validate` server checks; shows error/warning counts as colored badges with labelled list
- Export buttons: Download XML (triggers browser download), Download PDF (uses `html2pdf.js` via CDN)
- Auto-generates XML on screen mount; "Regenerate XML" and "Validate" buttons

**Shared components:**
- `Header.jsx` — navy header bar with Novel Future "N" logo, 4-step progress stepper, Save Draft button
- `FormField.jsx` — reusable `Input`, `Textarea`, `Select`, `Button` (4 variants), `Card`, `Badge` components
- `store.js` — article state defaults (NFP pre-fills), `saveDraft`/`loadDraft` via localStorage
- `utils/validation.js` — client-side NFP rule checker, `countAbstractWords`, `isDOIValid`
- `utils/xmlHighlight.js` — regex-based XML syntax highlighter returning HTML string

---

#### Infrastructure

| Item | Detail |
|------|--------|
| Backend port | **5001** (macOS reserves 5000 for AirPlay Receiver) |
| Frontend port | 3000 |
| Vite proxy | `/parse`, `/generate`, `/validate`, `/autotag`, `/health` → `:5001` |
| Python venv | `backend/.venv` |
| AI model | `claude-sonnet-4-20250514` (auto-tag only, requires `ANTHROPIC_API_KEY` in `backend/.env`) |
| Draft persistence | `localStorage` key `nfp_draft`, survives page refresh |

**Start commands:**
```bash
# Backend
cd backend && bash start.sh

# Frontend
cd frontend && npm run dev
```

---

## NFP Defaults (pre-filled on every new article)

| Field | Value |
|-------|-------|
| Journal name | Novel Future Proceedings |
| Publisher | Novel Future Publishers Inc. |
| Location | Canada |
| Default article type | Conference Proceeding |
| Copyright | © 2026 Novel Future Publishers Inc. Open Access article under CC BY 4.0 license. |
| ISSN online | *(blank — to be filled per issue)* |

---

## Validation Rules Implemented

| # | Rule | Where enforced |
|---|------|---------------|
| 1 | All authors need first + last name | Client + server |
| 2 | ≥1 corresponding author with email | Client + server |
| 3 | Abstract 150–300 words | Client (live) + server |
| 4 | 3–10 keywords | Client + server |
| 5 | DOI matches `10.\d{4,}/\S+` | Client (inline) + server |
| 6 | All sections have non-empty heading | Client + server |
| 7 | References sequential from [1] | Server |
| 8 | All figures have a caption | Client + server |

---

## Dependencies

### Backend
```
flask==3.0.3
flask-cors==4.0.1
python-docx==1.1.2
lxml==5.2.2
anthropic==0.30.0
python-dotenv==1.0.1
Werkzeug==3.0.3
```

### Frontend (key packages)
```
react, react-dom
tailwindcss (v4, @tailwindcss/vite)
@dnd-kit/core, @dnd-kit/sortable, @dnd-kit/utilities
lucide-react
react-hot-toast
html2pdf.js (loaded via CDN in index.html)
mammoth (installed, reserved for future client-side fallback)
xmlbuilder2 (installed, reserved for future client-side generation)
```

---

---

### 2026-05-14 — Bug Fixes (End of Day)

#### Bug 1 — File picker popup not opening on upload screen
**Symptom:** Clicking the drag-and-drop area did nothing; no file browser appeared.  
**Root cause:** `Card` component in `FormField.jsx` only destructured `className` and `children` — all other props (`onClick`, `onDragOver`, `onDragLeave`, `onDrop`) were silently discarded and never reached the DOM.  
**Fix:** Added `...props` spread to `Card` so all event handlers pass through to the underlying `<div>`.  
**File:** `frontend/src/components/FormField.jsx`

Also added a dedicated **"Browse files"** button inside the upload zone as a reliable fallback, using `e.stopPropagation()` to avoid double-triggering the card's own click handler.  
**File:** `frontend/src/screens/UploadScreen.jsx`

#### Bug 2 — `Parsing failed: <Paragraph object> is not in list`
**Symptom:** Every DOCX upload failed with this error from the `/parse` endpoint.  
**Root cause:** `_extract_inline_images()` called `doc.paragraphs.index(para)` to find the current paragraph's position. `doc.paragraphs` is a property that returns a **new list of new objects** on every call, so the `para` instance from the `enumerate()` loop was never present in the freshly-generated list — causing a `ValueError`.  
**Fix:** Captured `doc.paragraphs` once into `all_paragraphs` before the loop, and replaced `doc.paragraphs.index(para)` with the loop index `i` (already available from `enumerate`).  
**File:** `backend/parser/docx_parser.py`

#### Status at end of day
- Upload flow: working (file picker opens, DOCX parses successfully)
- Backend: running on port 5001
- Frontend: running on port 3000
- Full parse → metadata → sections → export flow: ready to test tomorrow

---

---

### 2026-05-16 — Table Parsing, Journal Name Fix, PDF Export

#### Feature 1 — Table Parsing (Backend + Frontend)

**Backend (`parser/docx_parser.py`):**
- Added `_extract_tables(doc)`, `_para_el_text(el)`, `_row_cells(row)` functions
- Iterates `doc.element.body` in document order to match each `w:tbl` element to its label paragraph (searches up to 8 paragraphs back, then 4 forward as fallback)
- Deduplicates merged cells via `id(cell._tc)` identity
- Returns `[{label, caption, headers, rows}]` per table
- `parse_docx` return now includes `"tables": _extract_tables(doc)`

**Frontend:**
- `store.js` `defaultArticle()` — added `tables: []`
- `App.jsx` `handleParsed` — merges `parsed.tables`
- `SectionsScreen.jsx` — added `TablePreview` component (first 3 rows as HTML table, "+N more rows" footer) and a Tables panel between Figures and References with editable label/caption fields and Remove button

#### Bug Fix — Journal Name Default Corrupted After Parse

**Symptom:** Journal name field showed manuscript body text (e.g. "Novel Energy") instead of "Novel Future Proceedings" after uploading a file.
**Root cause:** Stale localStorage draft with a wrong `journal_name` value was being spread into article state via `...prev` in `handleParsed`. The parse response was not the direct cause but could theoretically contribute.
**Fix (two parts):**
- `parser/docx_parser.py` — parse return now explicitly includes `"journal_name": None, "publisher_name": None, "publisher_loc": None` to make the contract clear: the parser never infers journal identity from manuscript content
- `App.jsx` — `handleParsed` now explicitly resets `journal_name`, `publisher_name`, `publisher_loc` to NFP defaults (from a module-level `NFP_DEFAULTS = defaultArticle()` snapshot) on every parse, so a stale draft can never corrupt these fields

#### Feature 2 — PDF Export via WeasyPrint

**New files:**
- `pdf_gen/__init__.py` — package marker
- `pdf_gen/html_template.py` — builds full academic article HTML with:
  - 3-column header: journal thumbnail initials placeholder (left), "From the journal: / Journal Name" (center), SVG N-mark logo with red diagonal slash + "OVEL Publisher" text (right)
  - Navy `<hr>` rule below header
  - Article type badge (blue pill) + OPEN ACCESS badge (green pill)
  - Article title (16pt bold navy)
  - Authors line with superscript affiliation numbers and `*` for corresponding
  - Numbered affiliations block (8pt muted gray)
  - Corresponding author email line
  - Dates row: Received / Accepted / Published
  - Abstract section with keywords line
  - Body sections with subsections
  - Tables: full-width with navy header row, alternating `#F5F7FA` row shading
  - Figure placeholder boxes with italic centered captions
  - References numbered list (9pt)
  - `@page` CSS footer: journal name left, page number right, thin top border
- `pdf_gen/renderer.py` — single WeasyPrint `HTML(string=...).write_pdf()` call

**`app.py`:**
- Added `POST /export/pdf` endpoint — builds HTML, renders PDF, returns `application/pdf` binary with `Content-Disposition: attachment; filename="[slug].pdf"`
- Added `import re` and `make_response` import

**`vite.config.js`:** Added `/export` → `http://localhost:5001` proxy rule

**`frontend/src/screens/ExportScreen.jsx`:**
- Replaced old client-side `html2pdf.js` approach with a `fetch("/export/pdf", ...)` POST
- Added `pdfLoading` state — button shows animated spinner + "Generating PDF…" while WeasyPrint renders
- On success: streams blob → triggers browser download

**`requirements.txt`:** Added `weasyprint==68.1`

**`start.sh`:** Added `DYLD_LIBRARY_PATH="/opt/homebrew/lib"` so WeasyPrint's cffi loader finds Pango/GLib dylibs on macOS Homebrew

**System dependency:** `brew install pango` (pulls GLib, Cairo, HarfBuzz)

#### Bug Fix — 502 on PDF Download (Unicode Title)

**Symptom:** Browser got 502 Bad Gateway when downloading PDF for articles with Unicode in the title (e.g. `CO₂`).
**Root cause:** The `Content-Disposition: attachment; filename="..."` header was built with `re.sub(r"[^\w\-]", "_", title)` — Python's `\w` matches Unicode word chars including `₂` (U+2082). Werkzeug encodes HTTP headers as Latin-1 and threw `UnicodeEncodeError`, dropping the connection mid-response. Vite proxy saw the dropped connection and reported 502.
**Fix:** Changed slug regex to `[^a-zA-Z0-9_\-]` (ASCII-only) and added `or "article"` fallback for empty slugs.

---

---

### 2026-05-18 — Figure Images, Equations, Exports, Web Viewer, Deployment

#### Feature 1 — Real Figure Images from DOCX (EMF/WMF Support)

**Problem:** Figures were showing `[Figure N]` placeholder boxes — images were not extracted.

**Root cause chain:**
1. `_has_image()` only checked DrawingML (`wp:inline`/`wp:anchor`) but older DOCX files embed images via VML (`v:imagedata`).
2. Even when found, EMF/WMF format images (used by Microsoft Office) cannot be decoded by Pillow on macOS/Linux.

**Fixes (`parser/docx_parser.py`):**
- Added VML namespace constants: `_VML_NS`, `_O_NS`
- Updated `_has_image()` to also check `v:imagedata` elements
- Added `_build_figure_block()` with two extraction paths: DrawingML first, VML fallback
- Added `_blob_to_data_uri()`:
  - Direct base64 for supported formats (PNG, JPEG, GIF, SVG, WebP, BMP)
  - LibreOffice headless for EMF/WMF: `soffice --headless --convert-to png`
  - Pillow auto-crop on LibreOffice output: `ImageChops.difference(img, bg).getbbox()` with 8px padding to remove the A4 whitespace canvas
  - Pillow fallback for other formats

**System dependency:** `brew install libreoffice` (macOS dev), installed in Docker for production.

**`requirements.txt`:** Added `Pillow>=10.0.0`

---

#### Bug Fix — Blank Figure List Before References

**Symptom:** A block of empty `[Figure 1]`, `[Figure 2]` boxes appeared before the References section.

**Root cause:** `article.figures` (top-level array without `data_uri`) was being rendered in two places — `ExportScreen.jsx` AND `html_template.py` — even though figures are already embedded inline inside section content blocks.

**Fix:** Removed the standalone `figures_html` rendering block from `html_template.py` and the `article.figures` render loop from `ExportScreen.jsx`. Figures now only render inline within their section.

---

#### Bug Fix — Captions Missing for Non-Adjacent Figures

**Symptom:** Figures 2, 4, 5, 6 showed no captions — only Figure 1 had one.

**Root cause:** The parser looked for a caption only in the immediately following paragraph. In these documents, captions are placed separately from figures (several paragraphs away).

**Fix:** Two-stage caption lookup in `_extract_structure()`:
1. **Lookahead**: scan up to 2 blank paragraphs after each image for a `Fig. N` caption
2. **Pre-scan fallback**: `_collect_fig_captions(doc)` pre-scans the entire document before parsing begins, building a `{fig_number: caption_text}` map. Prefers real captions (e.g. "Fig. 2. SEM micrographs…") over body-text references (e.g. "Fig. 2 presents…") via priority scoring.

---

#### Feature 2 — Clickable Citation Links

**`ExportScreen.jsx`:** Added `citify()` function using regex `\[([\d,\s–—-]+)\]` — wraps each number inside citation brackets with `<a href="#ref-N">`. Applied to paragraph text and table cells.

**`html_template.py` and `html_web_template.py`:** Same `_citify()` function applied to all rendered text. Reference list items get `id="ref-{num}"` anchors so in-page jumping works.

---

#### Feature 3 — OMML Equation Rendering

**Symptom:** Word equations (OMML format, `oMath` XML) were silently dropped.

**Fix (`parser/docx_parser.py`):**
- Added `_MATH_NS` namespace constant
- Added `_has_math(p_element)` — checks for `oMath` elements
- Added `_math_para_to_image(p)` — copies the equation paragraph into a minimal temp DOCX, converts to PNG via LibreOffice, auto-crops with Pillow
- New `"equation"` block type added to section content; rendered as centered `<img>` (max 80px height) in both ExportScreen and html_template

---

#### Feature 4 — HTML Export, Web ZIP Export, In-Browser Previews

**New backend endpoints (`app.py`):**
- `POST /export/html` — returns standalone HTML file as attachment
- `POST /export/web-zip` — returns ZIP containing `{slug}/index.html`
- `POST /preview/web` — returns HTML inline (no attachment header) for browser display

**New file `pdf_gen/html_web_template.py`** — JATS Editor-style web viewer:
- Left TOC sidebar (280px): auto-generated from sections, active section highlighting via `IntersectionObserver`
- Right icon sidebar (44px): 5 vertical tab buttons
- Slide-out panel (340px): Metrics, Media, Tables, References, Contributors panels
- Affiliation index building for numbered superscripts on author names
- All text passed through `_citify(_linkify())`

**`ExportScreen.jsx`:**
- Added `previewXml()` — opens syntax-highlighted XML in new tab (synchronous `window.open` to avoid popup blocker, then `document.write`)
- Added `previewWeb()` — opens new tab synchronously, writes "Building…" placeholder, fetches HTML from backend as blob, navigates via `win.location.replace(blobUrl)` (avoids `document.write` breaking on large base64-embedded images)
- Added `downloadHtml()`, `downloadWebZip()` functions
- Added 6 buttons to header: View XML, Download XML, View Web, Download HTML, Download Web ZIP, Download PDF

**`vite.config.js`:** Added `/preview` proxy rule.

---

#### Bug Fix — Heading Detection for Bold-Style Documents

**Symptom:** A new uploaded document placed all content in "Other" — no sections detected.

**Root cause:** The document used **bold 12pt Normal paragraphs** as headings instead of numbered headings or Word Heading styles. `_classify_heading()` only detected those two patterns.

**Fix (`parser/docx_parser.py`):**
- Added `is_bold: bool = False` parameter to `_classify_heading()`
- Added third detection path: if a paragraph is bold, 2–80 chars, starts uppercase, doesn't end with sentence-terminating punctuation, and isn't a figure caption → classify as heading
- Uses `_guess_section_type()` to distinguish h2 (Introduction, Methods, Results…) from h3 (SEM Analysis, Characterization, etc.)
- Updated call site in `_extract_structure()` to pass `is_bold=is_bold`

---

#### Bug Fix — Abstract Skipped When Graphical Abstract Present

**Symptom:** After the bold heading fix, documents with a "Graphical Abstract" section before the real abstract lost their abstract content.

**Root cause:** "Graphical Abstract" (short, bold) now triggered the bold heuristic → `heading_level="h3"` → the `authors` phase exited early to `body`, never reaching the real "Abstract" heading.

**Fix:** Added `heading_explicit = _classify_heading(text, style_name)` (no bold heuristic) alongside `heading_level`. Phase transitions in `pre_title` and `authors` now use `heading_explicit` (strict detection only). The `abstract` phase and body section handling continue using the full `heading_level` (with bold heuristic) so real section headings still work after the abstract.

---

#### Bug Fix — Author Last Name from Trailing Initials

**Old behaviour:** "Ravi K N" → `first_name="Ravi K N"`, `last_name=""`

**New behaviour (South Indian / abbreviated suffix names):**

| Input | first_name | last_name |
|---|---|---|
| `Shankar S` | `Shankar` | `S` |
| `Ravi K N` | `Ravi` | `K N` |
| `Manju Kumar S N` | `Manju Kumar` | `S N` |
| `Mylarappa M` | `Mylarappa` | `M` |
| `S.K RaviKumar` | `S.K` | `RaviKumar` |

**Fix (`_split_name()` in `parser/docx_parser.py`):** Walks backwards through name tokens collecting consecutive single-letter initials (with optional trailing dot) into `last_name`. Non-initial last token still becomes `last_name` normally (covers Western names and "S.K RaviKumar" style).

---

#### Deployment — Render (Docker)

**New files:**
- `backend/Dockerfile` — `python:3.11-slim` base, installs WeasyPrint system libs and LibreOffice, runs `gunicorn` with 1 worker / 4 threads / 120s timeout
- `backend/.dockerignore`
- `render.yaml` — Blueprint config: backend as Docker web service, frontend as static site
- `frontend/src/utils/api.js` — exports `API_BASE = import.meta.env.VITE_API_BASE || ""`. Empty in dev (Vite proxy handles routing); set to deployed backend URL in production.

**Modified for production API routing:**
- `UploadScreen.jsx` — `/parse` → `` `${API_BASE}/parse` ``
- `SectionsScreen.jsx` — `/autotag` → `` `${API_BASE}/autotag` ``
- `ExportScreen.jsx` — all 6 fetch calls updated
- `requirements.txt` — added `gunicorn>=21.2.0`

**GitHub repo:** https://github.com/ruksarsb25-rgb/noveltor.git

---

---

### 2026-05-18 (Session 2) — Parser & Export Fixes

#### Fix 1 — Citation Range Expansion
`_citify()` in both templates now expands ranges like `[17–24]` → `[17,18,19,20,21,22,23,24]` with individual anchor links per number.

#### Fix 2 — Bold Headings Without Section Number Ignored
Removed the bold heuristic from `_classify_heading()` entirely. Only explicitly numbered headings or Word Heading styles are now recognised as section headings, preventing decorative bold lines from corrupting the section list.

#### Fix 3 — Corresponding Author `*` Prefix Format
`_CORRESP_LINE_RE` updated to accept `*Corresponding author:` (leading asterisk) in addition to the plain `Corresponding author:` format.

#### Fix 4 — Author Superscript Comma Strip
`_AUTHOR_MARKER_RE` now allows a comma before `*` (e.g. `Ravikumar5,*`). The comma and asterisk are stripped when building the numeric affiliation key.

#### Fix 5 — Expanded Figure / Table Caption Patterns
Updated `_FIG_CAPTION_RE` and `_TABLE_CAPTION_RE` to match all common abbreviation variants:
`Fig. n`, `Fig.n`, `Fig n`, `Figure. n`, `Figure-n`, `Fig-1`, `Fig. (n)`, `Fig.(n)`, `Fig (n)`, `Figure. (n)`, `Figure-(n)`, `Fig-(1)` — and equivalents for Table.

#### Fix 6 — Graphical Abstract / Schema Images No Longer Skipped
`_SKIP_FIG_RE` matched "schema" but not "scheme" — fixed to `sch(?:ema|eme)`. Images matching the pattern now render as **unnumbered figure blocks** with their original label (e.g. "Graphical Abstract", "Scheme-1") instead of being dropped.

#### Fix 7 — Double Figure Captions Removed
Template was prepending "Figure N." while the caption text still contained "Fig.N:" prefix. Added `_strip_fig_label()` to strip the `Fig. N:` / `Figure (12).` prefix from caption text before rendering. Result: only the template-generated label appears.

#### Fix 8 — Graphical Abstract Missing (Phase Guard)
The image detection block had `if phase == "body"` — Graphical Abstract images appear in the pre-body phase and were silently dropped. Fixed: image detection now runs for all phases; non-skip images in pre-body are still ignored, but skip images (Graphical Abstract, Scheme) are included.

#### Fix 9 — Period-Separated Author Name Format
`_split_name()` now handles `S.N.Manjula` style: if a single space-token matches `(X\.)+Word` (single-letter initials + multi-char surname), it splits at the last period segment.

| Input | first_name | last_name |
|---|---|---|
| `S.N.Manjula` | `S.N.` | `Manjula` |
| `K.Ravikumar` | `K.` | `Ravikumar` |

#### Fix 10 — Smart Crop Over-Trimming Chart Borders
`_smart_crop()` was cutting the top edge off charts that have a thick outer border frame (e.g. Fig. 5). The outer border top line was being removed, making the inset sub-chart appear to float above it. Fixed with a `min_blank_run=30` guard: a side is only cropped if there are ≥30 px of blank canvas on that edge — preventing fringe/rounding losses while still removing large blank EMF canvas areas.

#### Fix 11 — DOI Added to PDF Export
The article's DOI (entered in the Metadata screen) was present in the web preview but missing from the PDF output. Added DOI rendering to `html_template.py` below the dates row as a clickable `https://doi.org/…` link.

#### Fix 12 — Trailing Periods Stripped from URLs in References
`_linkify()` in both templates now strips trailing `.,;` from matched URLs before building the `href`, and re-appends the stripped punctuation as plain text after the link.

#### Fix 13 — Trailing Periods Stripped from Reference Lines
All reference `raw_text` values are now `.rstrip(".")` before rendering in both templates, removing the sentence-ending period that academic reference formatters typically append.

---

## Known Limitations / Future Work

- [ ] OJS integration (explicitly out of scope for now)
- [ ] DOCX parsing is heuristic — complex author blocks or non-standard formatting may need manual correction
- [ ] No user authentication — single-user local tool
- [ ] AI auto-tag requires API key; gracefully degrades (button shows server error toast)
- [ ] ISSN online field left blank by default per NFP workflow
- [ ] Free-tier Render backend spins down after inactivity — first request after idle takes ~30s to wake
