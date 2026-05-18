# NFP Article Formatter

A JATS XML editor for academic journal publishing. Upload a manuscript DOCX, clean metadata, tag sections, and export a valid JATS XML file (NISO Z39.96 Publishing DTD v1.3).

## Quick Start

### 1 — Backend (Flask)

```bash
cd backend
cp .env.example .env          # add your ANTHROPIC_API_KEY
bash start.sh                 # creates venv, installs deps, starts on :5001
```

Or manually:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
FLASK_PORT=5001 .venv/bin/python app.py
```

### 2 — Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev                   # starts on http://localhost:3000
```

> Port 5000 is reserved by macOS AirPlay. The backend defaults to **5001**.
> The Vite dev server proxies `/parse`, `/generate`, `/validate`, `/autotag` → `http://localhost:5001`.

---

## API Endpoints

| Method | Path        | Description                                    |
|--------|-------------|------------------------------------------------|
| GET    | `/health`   | Health check                                   |
| POST   | `/parse`    | Upload DOCX → structured JSON                  |
| POST   | `/generate` | Structured JSON → JATS XML string              |
| POST   | `/validate` | JATS XML string → `{valid, errors, warnings}`  |
| POST   | `/autotag`  | Raw text → Claude AI section type suggestions  |

### `/parse` — multipart form
```
file: <.docx file>
```
Returns: `{title, authors[], abstract, keywords[], sections[], references[], figures[]}`

### `/generate` — JSON body
Full article object (same shape as `/parse` response + metadata fields).  
Returns: `{xml: "<article>…</article>"}`

### `/validate` — JSON body
```json
{ "xml": "<?xml version…" }
```
Returns: `{valid: true, errors: [], warnings: []}`

### `/autotag` — JSON body
```json
{ "text": "raw article text…" }
```
Returns: `{article_type, sections: [{heading, type}], missing_sections[]}`

---

## Environment Variables

| Variable           | Default | Description                              |
|--------------------|---------|------------------------------------------|
| `ANTHROPIC_API_KEY`| —       | Required for AI Auto-tag feature         |
| `FLASK_PORT`       | 5000    | Backend port (use 5001 on macOS)         |
| `FLASK_DEBUG`      | true    | Flask debug mode                         |

---

## JATS XML Output

- DTD: JATS Publishing v1.3 (`-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN`)
- Includes `<journal-meta>`, `<article-meta>`, `<body>`, `<back>`
- Authors: `<contrib contrib-type="author">` with `<name>`, `<aff>`, `<email>`
- Sections: `<sec>` with `<title>` and `<p>` tags
- References: `<ref-list>` with `<ref id="refN">` + `<mixed-citation>`
- Figures: `<fig>` with `<label>`, `<caption>`, `<graphic xlink:href>`

---

## Project Structure

```
NovelTOR/
├── backend/
│   ├── app.py                  Flask REST API
│   ├── requirements.txt
│   ├── start.sh
│   ├── parser/
│   │   └── docx_parser.py      python-docx DOCX parser
│   └── jats/
│       ├── generator.py        JATS XML generator
│       └── validator.py        Structural + NFP rule validator
└── frontend/
    ├── src/
    │   ├── App.jsx             Root app + step routing
    │   ├── store.js            State defaults + localStorage draft
    │   ├── components/
    │   │   ├── Header.jsx      Nav + stepper
    │   │   └── FormField.jsx   Shared UI primitives
    │   ├── screens/
    │   │   ├── UploadScreen.jsx
    │   │   ├── MetadataScreen.jsx
    │   │   ├── SectionsScreen.jsx
    │   │   └── ExportScreen.jsx
    │   └── utils/
    │       ├── validation.js   Client-side NFP consistency checks
    │       └── xmlHighlight.js XML syntax highlighter
    └── vite.config.js
```

---

## NFP Defaults (pre-filled)

| Field              | Default                                                        |
|--------------------|----------------------------------------------------------------|
| Journal name       | Novel Future Proceedings                                       |
| Publisher          | Novel Future Publishers Inc.                                   |
| Location           | Canada                                                         |
| Article type       | Conference Proceeding                                          |
| Copyright          | © 2026 Novel Future Publishers Inc. Open Access under CC BY 4.0|

## Validation Rules

1. All author names must have both first and last name  
2. At least one author must be corresponding with an email  
3. Abstract: 150–300 words (live word count shown)  
4. Keywords: 3–10  
5. DOI must match `10.\d{4,}/\S+`  
6. All sections must have a non-empty heading  
7. References numbered sequentially from `[1]`  
8. All figures must have a caption  
