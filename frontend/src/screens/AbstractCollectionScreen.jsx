import React, { useState } from "react";
import { Card, Button } from "../components/FormField.jsx";
import { API_BASE } from "../utils/api.js";
import toast from "react-hot-toast";

function Spinner({ white }) {
  return (
    <span className={`w-3.5 h-3.5 border-2 ${white ? "border-white border-t-transparent" : "border-slate-400 border-t-transparent"} rounded-full animate-spin inline-block`} />
  );
}

export default function AbstractCollectionScreen({ collection, onReset }) {
  const abstracts       = collection.abstracts || [];
  const docTitle        = collection.doc_title || "Abstract Collection";
  const collectionType  = collection.collection_type === "poster_abstracts"
    ? "Poster Abstract Collection"
    : "Abstract Collection";

  const [search, setSearch]       = useState("");
  const [expanded, setExpanded]   = useState(null);
  const [exporting, setExporting] = useState(false);
  const [eventName, setEventName] = useState(docTitle);
  const [year, setYear]           = useState(new Date().getFullYear().toString());
  const [journal, setJournal]     = useState("Novel Future Proceedings");
  const [sectionRef, setSectionRef] = useState("ABS");
  const [locale, setLocale]         = useState("en");
  const [volume, setVolume]         = useState("1");
  const [issueNum, setIssueNum]     = useState("1");

  const filtered = abstracts.filter((ab) => {
    const q = search.toLowerCase();
    return (
      !q ||
      ab.title?.toLowerCase().includes(q) ||
      ab.abstract?.toLowerCase().includes(q) ||
      (ab.authors || []).some((a) =>
        `${a.first_name} ${a.last_name}`.toLowerCase().includes(q)
      )
    );
  });

  const downloadXmlZip = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API_BASE}/export/abstracts-xml`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...collection,
          event_name:   eventName,
          year:         year,
          journal_name: journal,
          section_ref:  sectionRef,
          locale:       locale,
          volume:       volume,
          issue_num:    issueNum,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${eventName.replace(/\s+/g, "_").slice(0, 50)}_ojs.xml`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Downloaded XML with ${abstracts.length} abstracts`);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-5">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-[#0F3557]">{collectionType}</h2>
          <p className="text-slate-500 text-sm mt-1">
            {abstracts.length} abstract{abstracts.length !== 1 ? "s" : ""} parsed — review and export as JATS XML bundle.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onReset}
            className="h-9 px-3 text-sm font-medium rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition-colors"
          >
            ← Upload New
          </button>
          <button
            onClick={downloadXmlZip}
            disabled={exporting || abstracts.length === 0}
            className="inline-flex items-center gap-2 h-9 px-4 text-sm font-medium rounded-lg bg-[#0F3557] text-white hover:bg-[#0c2a45] disabled:opacity-50 transition-colors"
          >
            {exporting ? <><Spinner white /> Exporting…</> : `⬇ Download XML (${abstracts.length} abstracts)`}
          </button>
        </div>
      </div>

      {/* Export settings */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-sm font-semibold text-slate-700">OJS Export Settings</h3>
          <span className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">Native XML Plugin</span>
        </div>

        {/* OJS pre-requisites warning */}
        <div className="mb-3 p-2.5 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800 flex gap-2">
          <span className="flex-shrink-0 mt-0.5">⚠️</span>
          <div className="space-y-1">
            <p><strong>Before importing, create these in your OJS journal:</strong></p>
            <ol className="list-decimal ml-4 space-y-0.5">
              <li><strong>Section</strong> — Settings → Journal → Sections → Add Section. Set abbreviation to match <em>Section Ref</em> below (e.g. <code className="bg-amber-100 px-1 rounded">ABS</code>).</li>
              <li><strong>Issue</strong> — Issues → Create Issue. Note the volume and number and enter them below.</li>
            </ol>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-slate-500 block mb-1">Conference / Event Name</label>
            <input
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F3557]"
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Journal Name</label>
            <input
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F3557]"
              value={journal}
              onChange={(e) => setJournal(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Year</label>
            <input
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F3557]"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">
              OJS Section Ref
              <span className="ml-1 font-normal text-amber-600">← must exist in OJS first</span>
            </label>
            <input
              className="w-full border-2 border-amber-300 rounded-md px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-amber-400"
              value={sectionRef}
              onChange={(e) => setSectionRef(e.target.value.toUpperCase())}
              placeholder="ABS"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Locale</label>
            <input
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F3557]"
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
              placeholder="en"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">
              OJS Issue Volume <span className="font-normal text-amber-600">← must exist in OJS</span>
            </label>
            <input
              className="w-full border-2 border-amber-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              placeholder="1"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">
              OJS Issue Number <span className="font-normal text-amber-600">← must exist in OJS</span>
            </label>
            <input
              className="w-full border-2 border-amber-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
              value={issueNum}
              onChange={(e) => setIssueNum(e.target.value)}
              placeholder="1"
            />
          </div>
        </div>
      </Card>

      {/* Search */}
      <input
        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#0F3557]"
        placeholder={`Search ${abstracts.length} abstracts…`}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {/* Abstract list */}
      <div className="space-y-2">
        {filtered.length === 0 && (
          <p className="text-slate-400 text-sm text-center py-8">No abstracts match your search.</p>
        )}
        {filtered.map((ab, i) => {
          const isOpen = expanded === i;
          const authors = (ab.authors || [])
            .map((a) => `${a.first_name} ${a.last_name}`.trim())
            .filter(Boolean)
            .join(", ");

          return (
            <Card key={i} className="p-4">
              <button
                className="w-full text-left"
                onClick={() => setExpanded(isOpen ? null : i)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-mono text-slate-400 flex-shrink-0">
                        #{abstracts.indexOf(ab) + 1}
                      </span>
                      <span className="font-semibold text-slate-800 text-sm leading-snug">
                        {ab.title || "Untitled"}
                      </span>
                    </div>
                    {authors && (
                      <p className="text-xs text-slate-500 ml-7">{authors}</p>
                    )}
                    {!isOpen && ab.abstract && (
                      <p className="text-xs text-slate-400 mt-1 ml-7 line-clamp-2">
                        {ab.abstract}
                      </p>
                    )}
                  </div>
                  <span className="text-slate-400 text-xs flex-shrink-0 mt-0.5">
                    {isOpen ? "▲" : "▼"}
                  </span>
                </div>
              </button>

              {isOpen && (
                <div className="mt-3 ml-7 space-y-3 border-t border-slate-100 pt-3">
                  {authors && (
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Authors</p>
                      <p className="text-sm text-slate-700">{authors}</p>
                    </div>
                  )}
                  {(ab.affiliations || []).length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Affiliations</p>
                      <ul className="text-xs text-slate-600 space-y-0.5">
                        {ab.affiliations.map((aff, j) => <li key={j}>{aff}</li>)}
                      </ul>
                    </div>
                  )}
                  {ab.abstract && (
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Abstract</p>
                      <p className="text-sm text-slate-700 leading-relaxed">{ab.abstract}</p>
                    </div>
                  )}
                  {(ab.keywords || []).length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Keywords</p>
                      <div className="flex flex-wrap gap-1">
                        {ab.keywords.map((kw, j) => (
                          <span key={j} className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>

    </div>
  );
}
