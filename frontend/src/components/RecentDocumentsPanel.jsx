import React, { useState, useEffect } from "react";

export default function RecentDocumentsPanel({ onSelectDocument }) {
  const [documents, setDocuments] = useState([]);
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    loadRecentDocuments();
    window.addEventListener("recentDocumentsSaved", loadRecentDocuments);
    return () => window.removeEventListener("recentDocumentsSaved", loadRecentDocuments);
  }, []);

  const loadRecentDocuments = () => {
    const stored = localStorage.getItem("recentDocuments");
    if (stored) {
      try {
        const docs = JSON.parse(stored);
        setDocuments(docs);
      } catch (e) {
        console.error("Failed to load recent documents", e);
      }
    }
  };

  const handleSelectDocument = (doc) => {
    onSelectDocument(doc);
  };

  const handleDeleteDocument = (e, index) => {
    e.stopPropagation();
    const updated = documents.filter((_, i) => i !== index);
    setDocuments(updated);
    localStorage.setItem("recentDocuments", JSON.stringify(updated));
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="w-80 bg-white border-l border-slate-200 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-200">
        <h2 className="font-semibold text-slate-800">Recent Documents</h2>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="text-slate-400 hover:text-slate-600"
        >
          {isOpen ? "−" : "+"}
        </button>
      </div>

      {/* Content */}
      {isOpen && (
        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {documents.length === 0 ? (
            <p className="text-xs text-slate-400 italic text-center py-8">
              No recent documents
            </p>
          ) : (
            documents.map((doc, idx) => (
              <div
                key={idx}
                onClick={() => handleSelectDocument(doc)}
                className="p-3 bg-slate-50 rounded-lg hover:bg-slate-100 cursor-pointer border border-slate-200 transition-all group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">
                      {doc.title || "Untitled"}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {doc.docType}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {doc.fileName}
                    </p>
                    <p className="text-xs text-slate-400">
                      {formatDate(doc.uploadDate)}
                    </p>
                    {doc.version && (
                      <p className="text-xs text-slate-400">
                        v{doc.version}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={(e) => handleDeleteDocument(e, idx)}
                    className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
