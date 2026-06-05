import React, { useState, useEffect, useRef } from "react";
import { Button, Card, Badge } from "../components/FormField.jsx";
import { highlightXML } from "../utils/xmlHighlight.js";
import { validateArticle } from "../utils/validation.js";
import { sectionBodyText } from "../store.js";

const URL_RE  = /(\bhttps?:\/\/[^\s<>"')\]]+)/gi;
const CITE_RE = /\[([\d,\s–—-]+)\]/g;

function linkify(text) {
  if (!text) return "";
  return text.replace(URL_RE, (url) => `<a href="${url}" target="_blank" rel="noreferrer" style="color:#0F3557;">${url}</a>`);
}

function citify(text) {
  if (!text) return "";
  return text.replace(CITE_RE, (_, inner) => {
    const linked = inner.replace(/\d+/g, (n) => `<a href="#ref-${n}" style="color:#0F3557;">${n}</a>`);
    return `[${linked}]`;
  });
}

function safeHtml(text) {
  // Escape HTML but preserve <sub>/<sup> tags produced by the parser.
  return (text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/&lt;(\/?(?:sub|sup))&gt;/gi, "<$1>");
}
import toast from "react-hot-toast";
import { API_BASE } from "../utils/api.js";

function renderContentBlocks(sec) {
  const content = sec?.content;
  if (Array.isArray(content) && content.length > 0) {
    return content.map((block, i) => {
      if (block.type === "paragraph") {
        return block.text
          ? <p key={i} dangerouslySetInnerHTML={{ __html: citify(linkify(safeHtml(block.text))) }} />
          : null;
      }
      if (block.type === "table") return <PreviewTable key={i} table={block} />;
      if (block.type === "figure") return <PreviewFigure key={i} figure={block} />;
      if (block.type === "equation") return (
        <div key={i} className="my-4 text-center">
          <img src={block.data_uri} alt="equation" className="inline max-w-full" style={{ maxHeight: "80px" }} />
        </div>
      );
      return null;
    });
  }
  const body = sectionBodyText(sec);
  return body
    ? <p dangerouslySetInnerHTML={{ __html: citify(linkify(safeHtml(body))) }} />
    : null;
}

function PreviewFigure({ figure }) {
  const label   = figure.label || "Figure";
  const caption = figure.caption || "";
  const dataUri = figure.data_uri || "";
  return (
    <div className="my-4 text-center">
      {dataUri ? (
        <img src={dataUri} alt={label} className="max-w-full mx-auto rounded" style={{ maxHeight: "70vh" }} />
      ) : (
        <div className="border border-slate-200 bg-slate-50 py-10 rounded text-slate-400 text-sm">
          [{label}]
        </div>
      )}
      <div className="text-xs text-slate-600 mt-1 italic">
        <strong dangerouslySetInnerHTML={{ __html: safeHtml(label) + (caption ? "." : "") }} />
        {caption && <span dangerouslySetInnerHTML={{ __html: " " + safeHtml(caption) }} />}
      </div>
    </div>
  );
}

function PreviewTable({ table }) {
  const headers = table.headers || [];
  const rows = table.rows || [];
  return (
    <div className="my-4">
      {(table.caption || table.label) && (
        <div className="text-sm font-semibold text-slate-700 mb-1" dangerouslySetInnerHTML={{ __html: safeHtml(table.caption || table.label) }} />
      )}
      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="min-w-full text-xs">
          {headers.length > 0 && (
            <thead className="bg-[#0F3557] text-white">
              <tr>{headers.map((h, i) => <th key={i} className="px-2 py-1 text-left font-medium" dangerouslySetInnerHTML={{ __html: citify(linkify(safeHtml(h || "—"))) }} />)}</tr>
            </thead>
          )}
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                {row.map((cell, ci) => <td key={ci} className="px-2 py-1 text-slate-600 border-b border-slate-100" dangerouslySetInnerHTML={{ __html: citify(linkify(safeHtml(cell || "—"))) }} />)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ArticlePreview({ article }) {
  const authors = (article.authors || []).map((a) => `${a.first_name} ${a.last_name}`.trim()).join(", ");
  const affiliations = [...new Set((article.authors || []).map((a) => a.affiliation).filter(Boolean))];
  const corrAuthor = (article.authors || []).find((a) => a.corresponding);
  const journalName = article.journal_name || "Novel Future Proceedings";
  const journalLogo = article.journal_logo || "";
  const brandLogo   = article.brand_logo   || "";

  return (
    <div className="article-preview p-8 max-w-none">
      {/* PDF-style header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b-2 border-[#0F3557]">
        <div className="flex items-center gap-3">
          {journalLogo ? (
            <img src={journalLogo} alt="Journal logo" className="w-12 h-12 object-contain" />
          ) : (
            <div className="w-12 h-12 bg-blue-50 border border-[#0F3557] rounded flex items-center justify-center font-bold text-[#0F3557] text-sm">
              {journalName.split(/\s+/).slice(0,2).map(w => w[0]?.toUpperCase() || "").join("") || "NP"}
            </div>
          )}
          <div>
            <div className="text-xs text-slate-400">From the journal:</div>
            <div className="text-sm font-bold text-[#0F3557]">{journalName}</div>
          </div>
        </div>
        {brandLogo ? (
          <img src={brandLogo} alt="Brand logo" className="max-h-9 max-w-28 object-contain" />
        ) : (
          <div className="text-sm font-bold text-[#0F3557]">N<span className="font-normal text-slate-500">ovel Publisher</span></div>
        )}
      </div>

      {article.title && <h1 className="text-center" dangerouslySetInnerHTML={{ __html: safeHtml(article.title) }} />}
      {authors && <div className="authors text-center">{authors}</div>}
      {affiliations.map((aff, i) => (
        <div key={i} className="text-center text-xs text-slate-500 mb-1">{aff}</div>
      ))}
      {corrAuthor?.email && (
        <div className="text-center text-xs text-slate-500 mb-4">
          Corresponding author: {corrAuthor.email}
        </div>
      )}

      {article.abstract && (
        <div className="abstract my-6">
          <div className="abstract-title">Abstract</div>
          <p dangerouslySetInnerHTML={{ __html: safeHtml(article.abstract) }} />
        </div>
      )}
      {article.keywords?.length > 0 && (
        <div className="keywords mb-4">
          <strong>Keywords:</strong> {article.keywords.join("; ")}
        </div>
      )}

      {(article.sections || []).map((sec, i) => (
        <div key={i}>
          {sec.heading && <h2 dangerouslySetInnerHTML={{ __html: safeHtml(sec.heading) }} />}
          {renderContentBlocks(sec)}
          {(sec.subsections || []).map((sub, j) => (
            <div key={j}>
              {sub.heading && <h3 dangerouslySetInnerHTML={{ __html: safeHtml(sub.heading) }} />}
              {renderContentBlocks(sub)}
            </div>
          ))}
        </div>
      ))}

      {article.references?.length > 0 && (
        <div className="ref-list mt-6">
          <h2>References</h2>
          {article.references.map((ref, i) => {
            const raw = typeof ref === "object" && ref !== null ? ref.raw_text : ref;
            const doi = typeof ref === "object" && ref !== null ? ref.doi : "";
            let cleanText = (raw || "").trim();
            if (doi) {
              cleanText = cleanText
                .replace(/\bhttps?:\/\/doi\.org\/\S+/gi, "")
                .replace(/\bdoi:\s*10\.\S+/gi, "")
                .trim().replace(/\s+/g, " ");
            }
            const doiHtml = doi
              ? ` <a href="https://doi.org/${doi}" target="_blank" rel="noreferrer" style="color:#0F3557;">https://doi.org/${doi}</a>`
              : "";
            const fullHtml = `[${i + 1}]&nbsp;${linkify(safeHtml(cleanText))}${doiHtml}`;
            return <p key={i} id={`ref-${i + 1}`} dangerouslySetInnerHTML={{ __html: fullHtml }} />;
          })}
        </div>
      )}
    </div>
  );
}

/** Uniform toolbar button — same height, same font, same radius everywhere. */
function ToolBtn({ children, onClick, disabled, loading, loadingLabel, primary }) {
  const base =
    "inline-flex items-center justify-center gap-1.5 h-9 px-3 text-sm font-medium rounded-lg border transition-colors whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed";
  const style = primary
    ? "bg-[#0F3557] text-white border-[#0F3557] hover:bg-[#0c2a45]"
    : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50";
  return (
    <button className={`${base} ${style}`} onClick={onClick} disabled={disabled || loading}>
      {loading ? (
        <>
          <span className={`w-3.5 h-3.5 border-2 ${primary ? "border-white border-t-transparent" : "border-slate-400 border-t-transparent"} rounded-full animate-spin`} />
          {loadingLabel || "Loading…"}
        </>
      ) : children}
    </button>
  );
}

export default function ExportScreen({ article }) {
  const [xml, setXml] = useState("");
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [htmlLoading, setHtmlLoading] = useState(false);
  const [webLoading, setWebLoading] = useState(false);
  const [xmlZipLoading, setXmlZipLoading] = useState(false);
  const [serverValidation, setServerValidation] = useState(null);
  const [validating, setValidating] = useState(false);
  const [activeTab, setActiveTab] = useState("preview"); // preview | xml
  const previewRef = useRef(null);

  const clientChecks = validateArticle(article);

  const generateXml = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) throw new Error("Generation failed");
      const data = await res.json();
      setXml(data.xml || "");
      toast.success("JATS XML generated");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const runValidation = async () => {
    if (!xml) { toast.error("Generate XML first"); return; }
    setValidating(true);
    try {
      const res = await fetch(`${API_BASE}/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ xml }),
      });
      const data = await res.json();
      setServerValidation(data);
    } catch (e) {
      toast.error("Validation request failed");
    } finally {
      setValidating(false);
    }
  };

  const downloadXml = () => {
    if (!xml) return;
    const blob = new Blob([xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}.xml`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadXmlZip = async () => {
    setXmlZipLoading(true);
    try {
      const res = await fetch(`${API_BASE}/export/xml-zip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "XML package generation failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}_xml_package.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("XML package downloaded");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setXmlZipLoading(false);
    }
  };

  const downloadPdf = async () => {
    setPdfLoading(true);
    try {
      const res = await fetch(`${API_BASE}/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "PDF generation failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("PDF downloaded");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setPdfLoading(false);
    }
  };

  const [wordLoading, setWordLoading] = useState(false);

  const downloadWord = async () => {
    setWordLoading(true);
    try {
      const res = await fetch(`${API_BASE}/export/word`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Word export failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Word document downloaded");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setWordLoading(false);
    }
  };

  const downloadHtml = async () => {
    setHtmlLoading(true);
    try {
      const res = await fetch(`${API_BASE}/export/html`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "HTML generation failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}.html`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("HTML downloaded");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setHtmlLoading(false);
    }
  };

  const previewXml = () => {
    if (!xml) { toast.error("Generate XML first"); return; }
    const win = window.open("", "_blank");
    if (!win) { toast.error("Popup blocked — please allow popups for this site"); return; }
    // Wrap in HTML so the browser renders it with syntax highlighting
    const escaped = xml.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
      <title>JATS XML</title>
      <style>
        body { background:#1e1e2e; color:#cdd6f4; font-family:monospace; font-size:13px;
               padding:24px; white-space:pre-wrap; word-break:break-all; line-height:1.6; }
        .tag { color:#89b4fa; } .attr { color:#a6e3a1; } .val { color:#fab387; }
        .pi  { color:#f38ba8; } .cmt { color:#6c7086; font-style:italic; }
      </style></head><body>${escaped}</body></html>`);
    win.document.close();
  };

  const previewWeb = async () => {
    // Open immediately (synchronous) so popup blocker treats it as a user gesture
    const win = window.open("", "_blank");
    if (!win) { toast.error("Popup blocked — please allow popups for this site"); return; }
    win.document.write(`<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;color:#555;background:#f4f6f9">
      <p>Building web preview…</p></body></html>`);
    try {
      const res = await fetch(`${API_BASE}/preview/web`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        win.close();
        toast.error(err.error || "Web preview failed");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      win.location.replace(url);
    } catch (e) {
      win.close();
      toast.error("Web preview failed: " + e.message);
    }
  };

  const downloadWebZip = async () => {
    setWebLoading(true);
    try {
      const res = await fetch(`${API_BASE}/export/web-zip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(article),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Web ZIP generation failed");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(article.title || "article").replace(/\s+/g, "_").slice(0, 60)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Web ZIP downloaded");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setWebLoading(false);
    }
  };

  useEffect(() => {
    generateXml();
  }, []); // Generate once on mount

  const allErrors = [...clientChecks.errors, ...(serverValidation?.errors || [])];
  const allWarnings = [...clientChecks.warnings, ...(serverValidation?.warnings || [])];
  const isValid = allErrors.length === 0;

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[#0F3557]">Preview & Export</h2>
          <p className="text-slate-500 text-sm mt-1">Review, validate, and download your JATS XML and PDF galley.</p>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">

          {/* ── Utility actions ── */}
          <ToolBtn onClick={generateXml} disabled={loading} loading={loading} loadingLabel="Generating…">
            ↺ Regenerate
          </ToolBtn>
          <ToolBtn onClick={runValidation} disabled={validating || !xml} loading={validating} loadingLabel="Validating…">
            ✓ Validate
          </ToolBtn>
          <ToolBtn onClick={previewXml} disabled={!xml}>
            👁 View XML
          </ToolBtn>
          <ToolBtn onClick={previewWeb}>
            👁 Web Preview
          </ToolBtn>

          {/* ── Divider ── */}
          <div className="w-px h-6 bg-slate-300 mx-1 self-center" />

          {/* ── Downloads ── */}
          <ToolBtn primary onClick={downloadXml} disabled={!xml}>
            ⬇ XML
          </ToolBtn>
          <ToolBtn primary onClick={downloadXmlZip} disabled={xmlZipLoading} loading={xmlZipLoading} loadingLabel="Packaging…">
            ⬇ XML + Images
          </ToolBtn>
          <ToolBtn primary onClick={downloadHtml} disabled={htmlLoading} loading={htmlLoading} loadingLabel="Building…">
            ⬇ HTML
          </ToolBtn>
          <ToolBtn primary onClick={downloadWebZip} disabled={webLoading} loading={webLoading} loadingLabel="Zipping…">
            ⬇ Web ZIP
          </ToolBtn>
          <ToolBtn primary onClick={downloadPdf} disabled={pdfLoading} loading={pdfLoading} loadingLabel="Rendering…">
            ⬇ PDF
          </ToolBtn>
          <ToolBtn primary onClick={downloadWord} disabled={wordLoading} loading={wordLoading} loadingLabel="Exporting…">
            ⬇ Word
          </ToolBtn>

        </div>
      </div>

      {/* Validation panel */}
      <Card className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <h3 className="font-semibold text-slate-800">Validation</h3>
          <Badge color={isValid ? "green" : "red"}>
            {isValid ? "Valid" : `${allErrors.length} error${allErrors.length !== 1 ? "s" : ""}`}
          </Badge>
          {allWarnings.length > 0 && (
            <Badge color="yellow">{allWarnings.length} warning{allWarnings.length !== 1 ? "s" : ""}</Badge>
          )}
        </div>

        {allErrors.length === 0 && allWarnings.length === 0 && (
          <p className="text-green-700 text-sm">All checks passed ✓</p>
        )}

        {allErrors.length > 0 && (
          <ul className="space-y-1 mb-2">
            {allErrors.map((e, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                <span className="mt-0.5 flex-shrink-0">✗</span> {e}
              </li>
            ))}
          </ul>
        )}

        {allWarnings.length > 0 && (
          <ul className="space-y-1">
            {allWarnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                <span className="mt-0.5 flex-shrink-0">⚠</span> {w}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Content panels */}
      <div className="flex gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab("preview")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "preview" ? "border-[#0F3557] text-[#0F3557]" : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          Article Preview
        </button>
        <button
          onClick={() => setActiveTab("xml")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "xml" ? "border-[#0F3557] text-[#0F3557]" : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          JATS XML
        </button>
      </div>

      {activeTab === "preview" && (
        <Card className="overflow-auto max-h-[70vh]">
          <div ref={previewRef}>
            <ArticlePreview article={article} />
          </div>
        </Card>
      )}

      {activeTab === "xml" && (
        <Card className="overflow-auto max-h-[70vh]">
          {xml ? (
            <div className="bg-slate-900 rounded-lg p-4">
              <div
                className="xml-viewer text-slate-200"
                dangerouslySetInnerHTML={{ __html: highlightXML(xml) }}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center p-16 text-slate-400">
              {loading ? "Generating XML…" : "Click 'Regenerate XML' to generate"}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
