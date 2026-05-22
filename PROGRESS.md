# NFP Article Formatter — Build Progress

**Project:** Novel Future Publishers — JATS XML Article Formatting Tool  
**Repo:** `/Users/kareem/Github/NovelTOR`  
**Last updated:** 2026-05-21

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
- `


\SectionsScreen.jsx` — added `TablePreview` component (first 3 rows as HTML table, "+N more rows" footer) and a Tables panel between Figures and References with editable label/caption fields and Remove button

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

### 2026-05-18 — Sub/Superscript, DOI Dedup, PDF Layout, Web Export

#### Feature — Sub/Superscript Throughout Document

**Problem:** Chemical formulas like Ag₂O, H₂O and mathematical superscripts were not rendered as `<sub>`/`<sup>` in any output (preview, PDF, web).

**Root cause:** `python-docx`'s `p.text` strips all run-level formatting. Sub/sup info lives in `w:rPr/w:vertAlign[@w:val="subscript"|"superscript"]` and was never read.

**Fix — Backend (`parser/docx_parser.py`):**
- Added `import html as _html_lib`
- Added constants: `_W_VALIGN`, `_W_VAL`, `_W_RPR`
- Added `_para_text_with_fmt(p)` — iterates runs, wraps sub/sup runs in `<sub>`/`<sup>` HTML tags, HTML-escapes plain text
- Added `_cell_text_with_fmt(cell)` — same treatment for table cells
- Applied `_para_text_with_fmt` everywhere text is captured: title, abstract, section headings, subsection headings, body paragraphs, references
- Updated `_row_cells()` to use `_cell_text_with_fmt`

**Fix — Frontend (`ExportScreen.jsx`):**
- Updated `safeHtml()` to restore `<sub>`/`<sup>` after HTML-escaping:
  ```js
  .replace(/&lt;(\/?(?:sub|sup))&gt;/gi, "<$1>")
  ```
- Applied `dangerouslySetInnerHTML={{ __html: safeHtml(...) }}` to title, abstract, section headings, subsection headings, figure labels/captions, table captions
- Removed old `subscriptFormulas` regex function entirely

**Fix — Backend PDF (`pdf_gen/html_template.py`) and Web (`pdf_gen/html_web_template.py`):**
- Added `_SUB_SUP_RE` and `_e_fmt(s)` helper — HTML-escapes text then restores `<sub>`/`<sup>` tags
- Replaced all direct `html.escape()` calls with `_e_fmt()`
- Updated `_linkify()` to use `_e_fmt()` for non-URL text segments
- Removed `_subscript_formulas` and `_CHEM_RE` functions

---

#### Bug Fix — Double DOI URL in References

**Symptom:** Reference entries showed the DOI hyperlink twice — once embedded in `raw_text` (the linkified URL from the parser) and once from the structured `doi` field.

**Fix — Frontend (`ExportScreen.jsx`):** When a `doi` field is present, strip `https://doi.org/…` and `doi: 10.…` patterns from `cleanText` before rendering, then append a single formatted link from the `doi` field.

**Fix — Backend (`html_template.py`, `html_web_template.py`):** Same stripping logic applied before `_linkify()` runs on the reference `raw_text`.

---

#### Fix — Keywords Placement

**Problem:** Keywords appeared inside the abstract block in both the HTML preview and PDF.

**Fix:** Moved the Keywords line to render as a separate block immediately **after** the abstract `<div>`, in both `ExportScreen.jsx`, `html_template.py`, and `html_web_template.py`.

---

#### Fix — PDF Image Overflow / Blank Pages

**Problem:** Large figures caused blank page gaps because they overflowed the page height.

**Fix (`html_template.py`):**
- Added `.figure-img { max-height: 170mm; width: auto; }` CSS rule
- Removed `page-break-inside: avoid` from `.figure-wrap` so WeasyPrint can flow text after a large image instead of pushing it to a new page
- Added `page-break-before: avoid` on `.figure-caption` to keep caption with image

**Fix (`ExportScreen.jsx`, `html_web_template.py`):** Set `maxHeight: "70vh"` on figure `<img>` elements.

---

#### Fix — Remove "Novel Publisher" Label from PDF Header

**Problem:** The PDF header showed "Novel Publisher" as plain text behind the logo thumbnail.

**Fix (`html_template.py`):** Removed the `<div class="hdr-publisher-label">Novel Publisher</div>` element from the header template.

---

#### Feature — Journal Name Dropdown (Metadata Screen)

Changed the Journal Name field from a free-text `<Input>` to a `<Select>` with three fixed options:
- Novel Energy
- Photomaterials & Devices
- Novel Future Proceedings

**File:** `frontend/src/screens/MetadataScreen.jsx`

Updated default article type from `"Conference Proceeding"` to `"Research Article"` in `store.js` and `html_template.py`.

---

#### Feature — Web HTML Export

Added two new export modes:

**`POST /preview/web`** — returns a self-contained HTML document for instant browser preview (opens in new tab).

**`POST /export/web-zip`** — returns a ZIP archive containing `index.html` + extracted figure images as separate PNG files.

**`pdf_gen/html_web_template.py`** — new template file mirroring `html_template.py` but optimised for web (fluid layout, responsive breakpoints, TOC sidebar, social share icons).

**Frontend (`ExportScreen.jsx`):** Added "View Web" and "Download Web ZIP" buttons with loading states.

---

### 2026-05-18 (Session 2) — References Heading Detection + Missing-References Warning

#### Fix — References Heading Detection (All Punctuation Variants)

**Problem:** Parser only detected a heading as "References" if it matched exactly. Variations like `References:`, `References;`, `References.`, and numbered variants (`4. References`) were silently ignored, causing the entire references section to be missed.

**Fix (`parser/docx_parser.py`):**
```python
_REFS_HEADING_RE = re.compile(
    r'^(?:\d+[\.\d]*\.?\s+)?references?\s*[;:.,]?\s*$', re.IGNORECASE
)
```
Handles: leading section number, optional trailing `: ; . ,` and trailing whitespace.

#### Feature — Missing References Alert (Upload Screen)

After a successful parse, if `data.references` is empty the app now shows a persistent amber warning banner:

> ⚠️ No References section was found in this document. Make sure your document contains a heading that reads "References", "References:", "References;" or similar.

**File:** `frontend/src/screens/UploadScreen.jsx` — added `warnMsg` state; amber warning rendered below the error block; cleared on Reset.

---

### 2026-05-21 — Parser Image Fix + Build Fix

#### Fix — Abstract-Phase Images No Longer Dropped

**Problem:** The parser guard `if not is_skip and phase != "body": continue` dropped any non-skip image that appeared while the parser was still in the `abstract` phase (i.e. between the abstract text and the Keywords line, or in edge-case documents).

**Fix (`parser/docx_parser.py`):** Changed condition to `phase in ("pre_title", "authors")` so only truly decorative pre-content images (author headshots, cover art appearing before the title or in the author block) are dropped. Images in the abstract or body phase are always captured.

**Verified:** On the BAHAJ file (`Template+EPA+-+BAHAJ+Imane+.docx`), the inline image at paragraph 14 (after Keywords) is correctly extracted with its full base64 `data_uri` and placed in the first body section for rendering.

#### Fix — Production Build Failure (Smart Quotes)

**Problem:** Render's production build (Vite + Rolldown) failed with:
```
Expected `,` or `)` but found `Identifier`
src/screens/UploadScreen.jsx:51
```

**Root cause:** The warning string used Unicode curly/smart quotes (`"References"`) which Rolldown treated as ASCII `"` delimiters, terminating the string literal early.

**Fix (`UploadScreen.jsx`):** Replaced Unicode smart quotes with escaped ASCII quotes (`\"References\"`).

**Commit:** `e62b596`

---

## Known Limitations / Future Work

- [ ] OJS integration (explicitly out of scope for now)
- [ ] DOCX parsing is heuristic — complex author blocks or non-standard formatting may need manual correction
- [ ] Figures are detected structurally but image binaries are not extracted (only captions + placeholders)
- [ ] No user authentication — single-user local tool
- [ ] AI auto-tag requires API key; gracefully degrades (button shows server error toast)
- [ ] PDF export uses client-side html2pdf.js — complex layouts may need tuning
- [ ] ISSN online field left blank by default per NFP workflow
