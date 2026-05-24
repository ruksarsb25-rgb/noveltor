"""
NFP Article Formatter — Flask REST API
Endpoints: POST /parse, POST /generate, POST /validate, POST /autotag
"""
import os
import tempfile
import json
import anthropic

import re
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv

from parser.docx_parser import parse_docx
from jats.generator import generate_jats
from jats.validator import validate_jats

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

ALLOWED_EXTENSIONS = {"docx"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/parse", methods=["POST"])
def parse():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only .docx files are supported"}), 400

    try:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        result = parse_docx(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Parsing failed: {str(e)}"}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    try:
        xml = generate_jats(data)
        return jsonify({"xml": xml})
    except Exception as e:
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json(force=True)
    if not data or "xml" not in data:
        return jsonify({"error": "Expected JSON body with 'xml' key"}), 400

    try:
        result = validate_jats(data["xml"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500


@app.route("/autotag", methods=["POST"])
def autotag():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured on server"}), 503

    data = request.get_json(force=True)
    if not data or "text" not in data:
        return jsonify({"error": "Expected JSON body with 'text' key"}), 400

    raw_text = data["text"][:12000]  # Limit input to keep costs low

    try:
        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = (
            "You are a JATS XML tagging assistant for academic journals. "
            "Given raw article text, identify and return JSON with: "
            "article_type (one of: Research Article, Review, Conference Proceeding, "
            "Enhanced Poster Article, Conference Report), "
            "sections (array of {heading: string, type: one of Introduction, Methods, "
            "Results, Discussion, Conclusion, Acknowledgements, Other}), "
            "and missing_sections (array of section type strings that are required but absent). "
            "Return only valid JSON with no markdown fences."
        )

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": raw_text}],
        )

        response_text = message.content[0].text.strip()
        # Strip markdown fences if model adds them despite instructions
        response_text = response_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        parsed = json.loads(response_text)
        return jsonify(parsed)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"AI returned invalid JSON: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"AI auto-tag failed: {str(e)}"}), 500


@app.route("/preview/web", methods=["POST"])
def preview_web():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        from pdf_gen.html_web_template import build_web_html
        html_str = build_web_html(data)
        resp = make_response(html_str.encode("utf-8"))
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        return resp
    except Exception as e:
        return jsonify({"error": f"Web preview failed: {str(e)}"}), 500


@app.route("/export/web-zip", methods=["POST"])
def export_web_zip():
    import zipfile, io as _io
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        from pdf_gen.html_web_template import build_web_html
        html_str = build_web_html(data)
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", data.get("title", "article"))[:60].strip("_") or "article"
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{slug}/index.html", html_str.encode("utf-8"))
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "application/zip"
        resp.headers["Content-Disposition"] = f'attachment; filename="{slug}.zip"'
        return resp
    except Exception as e:
        return jsonify({"error": f"Web ZIP generation failed: {str(e)}"}), 500


@app.route("/export/xml-zip", methods=["POST"])
def export_xml_zip():
    """
    Return a ZIP package containing:
      - article.xml  (JATS XML with filename-based graphic hrefs)
      - figure images extracted from the parsed data_uri fields
        (named using the same convention as the XML: Journal-vol-issue-gN.jpeg)

    Upload both to the journal website so the XML graphic hrefs resolve.
    """
    import zipfile, io as _io, base64
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        from jats.generator import generate_jats, fig_filename, eq_filename

        xml_str = generate_jats(data)
        slug    = re.sub(r"[^a-zA-Z0-9_\-]", "_", data.get("title", "article"))[:60].strip("_") or "article"

        buf = _io.BytesIO()
        fig_counter = 0
        eq_counter  = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("article.xml", xml_str.encode("utf-8"))

            # Walk sections content in document order — extract figures and equations
            for sec in data.get("sections", []):
                all_content = [sec.get("content", [])] + \
                              [s.get("content", []) for s in sec.get("subsections", [])]
                for content_list in all_content:
                    for block in content_list:
                        btype = block.get("type")
                        uri   = block.get("data_uri", "")
                        if not uri:
                            if btype in ("figure", "equation"):
                                if btype == "figure":  fig_counter += 1
                                else:                  eq_counter  += 1
                            continue

                        b64 = uri.split(",", 1)[-1] if "," in uri else uri
                        try:
                            img_bytes = base64.b64decode(b64)
                        except Exception:
                            img_bytes = None

                        if btype == "figure":
                            fig_counter += 1
                            fname = fig_filename(data, fig_counter)
                            if img_bytes:
                                zf.writestr(fname, img_bytes)
                        elif btype == "equation":
                            eq_counter += 1
                            fname = eq_filename(data, eq_counter)
                            if img_bytes:
                                zf.writestr(fname, img_bytes)

        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers["Content-Type"] = "application/zip"
        resp.headers["Content-Disposition"] = f'attachment; filename="{slug}_xml_package.zip"'
        return resp
    except Exception as e:
        return jsonify({"error": f"XML package generation failed: {str(e)}"}), 500


@app.route("/export/html", methods=["POST"])
def export_html():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    try:
        from pdf_gen.html_template import build_html

        html_str = build_html(data)
        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", data.get("title", "article"))[:60].strip("_") or "article"
        resp = make_response(html_str.encode("utf-8"))
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        resp.headers["Content-Disposition"] = f'attachment; filename="{slug}.html"'
        return resp
    except Exception as e:
        return jsonify({"error": f"HTML generation failed: {str(e)}"}), 500


@app.route("/export/pdf", methods=["POST"])
def export_pdf():
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    try:
        from pdf_gen.html_template import build_html
        from pdf_gen.renderer import render_pdf

        html_str  = build_html(data)
        pdf_bytes = render_pdf(html_str)

        slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", data.get("title", "article"))[:60].strip("_") or "article"
        resp = make_response(pdf_bytes)
        resp.headers["Content-Type"] = "application/pdf"
        resp.headers["Content-Disposition"] = f'attachment; filename="{slug}.pdf"'
        return resp
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


@app.route("/enrich-refs", methods=["POST"])
def enrich_refs():
    """
    For each reference that has no DOI, query the Crossref API using the
    raw_text as a bibliographic search string. Returns the same refs list
    with doi fields filled in where a confident match was found.
    """
    import requests as _req
    import time

    data = request.get_json(force=True)
    if not data or "refs" not in data:
        return jsonify({"error": "Expected JSON body with 'refs' key"}), 400

    refs = data["refs"]
    enriched = []
    found = 0

    for ref in refs:
        raw_text = ref.get("raw_text", "").strip()
        existing_doi = ref.get("doi", "").strip()

        # Already has DOI — skip Crossref lookup
        if existing_doi:
            enriched.append(ref)
            continue

        if not raw_text:
            enriched.append(ref)
            continue

        try:
            resp = _req.get(
                "https://api.crossref.org/works",
                params={"query.bibliographic": raw_text, "rows": 1, "select": "DOI,score,title"},
                timeout=6,
                headers={"User-Agent": "NovelTOR/1.0 (mailto:support@noveltor.com)"},
            )
            items = resp.json().get("message", {}).get("items", [])
            doi = ""
            if items:
                top = items[0]
                score = top.get("score", 0)
                # Crossref scores > 50 indicate a confident bibliographic match
                if score > 50:
                    doi = top.get("DOI", "").strip()

            new_ref = dict(ref)
            new_ref["doi"] = doi
            if doi:
                found += 1
            enriched.append(new_ref)

            # Be polite to Crossref — 10 req/s max
            time.sleep(0.12)

        except Exception:
            enriched.append(ref)

    return jsonify({"refs": enriched, "found": found})


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
