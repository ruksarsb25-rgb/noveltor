import React, { useRef, useState, useCallback } from "react";
import { Button, Card } from "../components/FormField.jsx";
import { API_BASE } from "../utils/api.js";

const DOC_MODES = [
  { value: "article",          label: "Research Article",         desc: "Full paper with sections, references, figures" },
  { value: "abstracts",        label: "Abstract Collection",      desc: "Multiple oral/poster abstracts in one document" },
  { value: "poster",           label: "Poster",                   desc: "Single poster with metadata and image" },
];

function saveToRecentDocuments(data, fileName, docMode) {
  try {
    const stored = localStorage.getItem("recentDocuments");
    let documents = stored ? JSON.parse(stored) : [];

    const docTypeLabel = DOC_MODES.find(m => m.value === docMode)?.label || docMode;

    const newDoc = {
      title: data.title || "Untitled",
      docType: docTypeLabel,
      fileName: fileName,
      uploadDate: Date.now(),
      version: 1,
      data: data,
    };

    // Add to front and keep only last 10
    documents = [newDoc, ...documents].slice(0, 10);
    localStorage.setItem("recentDocuments", JSON.stringify(documents));
    window.dispatchEvent(new Event("recentDocumentsSaved"));
  } catch (e) {
    console.error("Failed to save to recent documents", e);
  }
}

export default function UploadScreen({ onParsed }) {
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | parsing | done | error
  const [errorMsg, setErrorMsg] = useState("");
  const [warnMsg, setWarnMsg] = useState("");
  const [fileName, setFileName] = useState("");
  const [docMode, setDocMode] = useState("article");
  const inputRef = useRef(null);

  const handleFile = useCallback(async (file) => {
    if (!file) return;
    if (!file.name.endsWith(".docx")) {
      setErrorMsg("Only .docx files are supported.");
      setStatus("error");
      return;
    }

    setFileName(file.name);
    setStatus("parsing");
    setErrorMsg("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("doc_mode", docMode);

      const res = await fetch(`${API_BASE}/parse`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Server returned ${res.status}`);
      }

      const data = await res.json();

      if (data.type === "abstract_collection") {
        // Abstract collection — pass through directly
        setStatus("done");
        setWarnMsg("");
        onParsed(data);
        return;
      }

      // Standard article — ensure sections have ids
      data.sections = (data.sections || []).map((s) => ({
        ...s,
        id: s.id || crypto.randomUUID(),
        ai_suggested: false,
      }));

      setStatus("done");

      if (!data.references || data.references.length === 0) {
        setWarnMsg(
          "⚠️ No References section was found in this document. " +
          "Make sure your document contains a heading that reads " +
          "\"References\", \"References:\", \"References;\" or similar."
        );
      } else {
        setWarnMsg("");
      }

      // Save to recent documents
      saveToRecentDocuments(data, file.name, docMode);

      onParsed(data);
    } catch (e) {
      setErrorMsg(e.message || "Parsing failed");
      setStatus("error");
    }
  }, [onParsed, docMode]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }, [handleFile]);

  const onInputChange = (e) => {
    const file = e.target.files?.[0];
    handleFile(file);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-64px)] p-8">
      <div className="w-full max-w-xl">
        <h1 className="text-3xl font-semibold text-[#0F3557] mb-2">Upload Document</h1>
        <p className="text-slate-500 mb-5">
          Upload a DOCX file and we'll extract the structure automatically.
        </p>

        {/* Document mode selector */}
        <div className="mb-6">
          <p className="text-sm font-medium text-slate-700 mb-2">Document type</p>
          <div className="grid grid-cols-3 gap-2">
            {DOC_MODES.map((m) => (
              <button
                key={m.value}
                onClick={() => setDocMode(m.value)}
                className={`text-left p-3 rounded-lg border-2 transition-all ${
                  docMode === m.value
                    ? "border-[#0F3557] bg-blue-50"
                    : "border-slate-200 hover:border-slate-300 bg-white"
                }`}
              >
                <div className={`text-sm font-semibold ${docMode === m.value ? "text-[#0F3557]" : "text-slate-700"}`}>
                  {m.label}
                </div>
                <div className="text-xs text-slate-400 mt-0.5">{m.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <Card
          className={`border-2 border-dashed transition-all cursor-pointer ${
            dragging ? "border-[#0F3557] bg-blue-50" : "border-slate-300 hover:border-slate-400"
          }`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className="flex flex-col items-center gap-4 p-12">
            {status === "parsing" ? (
              <>
                <div className="w-12 h-12 rounded-full border-4 border-[#0F3557] border-t-transparent animate-spin" />
                <p className="text-slate-600 text-sm font-medium">Parsing {fileName}…</p>
              </>
            ) : status === "done" ? (
              <>
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-2xl">✓</div>
                <p className="text-green-700 font-medium">Parsed successfully!</p>
                <p className="text-slate-500 text-xs">{fileName}</p>
              </>
            ) : (
              <>
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center">
                  <svg className="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="text-center">
                  <p className="text-slate-700 font-medium">Drag & drop your DOCX file here</p>
                  <p className="text-slate-400 text-sm mt-1">or</p>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                  className="px-5 py-2 bg-[#0F3557] text-white text-sm rounded-md hover:bg-[#0a2540] transition-colors"
                >
                  Browse files
                </button>
                <p className="text-xs text-slate-400">.docx files only · max 50 MB</p>
              </>
            )}
          </div>
        </Card>

        {status === "error" && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-3 text-red-700 text-sm">
            {errorMsg}
          </div>
        )}

        {warnMsg && (
          <div className="mt-4 bg-amber-50 border border-amber-300 rounded-md p-3 text-amber-800 text-sm flex items-start gap-2">
            <span className="shrink-0 text-base leading-5">⚠️</span>
            <span>{warnMsg.replace(/^⚠️\s*/, "")}</span>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".docx"
          className="hidden"
          onChange={onInputChange}
        />

        <div className="mt-6 flex items-center gap-3">
          <Button
            variant="secondary"
            onClick={() => {
              setStatus("idle");
              setErrorMsg("");
              setWarnMsg("");
              setFileName("");
            }}
            disabled={status === "parsing"}
          >
            Reset
          </Button>
          <p className="text-xs text-slate-400">
            Files are processed locally — nothing is stored on our servers.
          </p>
        </div>
      </div>
    </div>
  );
}
