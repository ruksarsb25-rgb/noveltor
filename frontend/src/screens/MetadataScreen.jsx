import React, { useState, useRef } from "react";
import { Button, Card } from "../components/FormField.jsx";
import { FormField, Input, Textarea, Select } from "../components/FormField.jsx";
import { ARTICLE_TYPES } from "../store.js";
import { defaultAuthor } from "../store.js";
import { countAbstractWords, isDOIValid } from "../utils/validation.js";

function LogoUpload({ label, hint, value, onChange }) {
  const inputRef = useRef(null);

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => onChange(ev.target.result);
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  return (
    <div className="flex items-start gap-3">
      <div
        className="w-20 h-16 flex-shrink-0 rounded border border-slate-200 bg-slate-50 flex items-center justify-center overflow-hidden cursor-pointer hover:border-slate-400 transition-colors"
        onClick={() => inputRef.current?.click()}
        title="Click to upload"
      >
        {value ? (
          <img src={value} alt={label} className="max-w-full max-h-full object-contain p-1" />
        ) : (
          <span className="text-slate-300 text-2xl select-none">+</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-slate-700 mb-0.5">{label}</div>
        {hint && <div className="text-xs text-slate-400 mb-1.5">{hint}</div>}
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => inputRef.current?.click()}>
            {value ? "Replace" : "Upload"}
          </Button>
          {value && (
            <Button variant="secondary" onClick={() => onChange("")}>
              Remove
            </Button>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="image/png,image/jpeg,image/svg+xml,image/webp"
          className="hidden"
          onChange={handleFile}
        />
      </div>
    </div>
  );
}

export default function MetadataScreen({ article, onChange, onNext }) {
  const [kwInput, setKwInput] = useState("");

  const set = (field, value) => onChange({ ...article, [field]: value });

  const updateAuthor = (i, field, value) => {
    const authors = [...article.authors];
    authors[i] = { ...authors[i], [field]: value };
    // Ensure at least one corresponding author
    if (field === "corresponding" && value === true) {
      // Allow multiple corresponding authors
    }
    onChange({ ...article, authors });
  };

  const addAuthor = () => onChange({ ...article, authors: [...article.authors, defaultAuthor()] });

  const removeAuthor = (i) => {
    const authors = article.authors.filter((_, idx) => idx !== i);
    onChange({ ...article, authors: authors.length ? authors : [defaultAuthor()] });
  };

  const moveAuthor = (i, dir) => {
    const authors = [...article.authors];
    const j = i + dir;
    if (j < 0 || j >= authors.length) return;
    [authors[i], authors[j]] = [authors[j], authors[i]];
    onChange({ ...article, authors });
  };

  const addKeyword = () => {
    const kws = kwInput.split(",").map((k) => k.trim()).filter(Boolean);
    if (!kws.length) return;
    const merged = [...new Set([...article.keywords, ...kws])];
    onChange({ ...article, keywords: merged });
    setKwInput("");
  };

  const removeKeyword = (kw) => {
    onChange({ ...article, keywords: article.keywords.filter((k) => k !== kw) });
  };

  const wordCount = countAbstractWords(article.abstract);
  const wcColor = wordCount < 150 || wordCount > 300 ? "text-amber-600" : "text-green-600";

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[#0F3557]">Article Metadata</h2>
          <p className="text-slate-500 text-sm mt-1">Review and edit the extracted metadata.</p>
        </div>
        <Button onClick={onNext}>Continue to Sections →</Button>
      </div>

      {/* Article basics */}
      <Card className="p-5 space-y-4">
        <h3 className="font-semibold text-slate-800 border-b border-slate-100 pb-2">Article Details</h3>

        <FormField label="Article Title" required>
          <Input value={article.title} onChange={(e) => set("title", e.target.value)} placeholder="Full article title" />
        </FormField>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Article Type">
            <Select
              value={article.article_type}
              onChange={(e) => set("article_type", e.target.value)}
              options={ARTICLE_TYPES}
            />
          </FormField>
          <FormField label="DOI" error={article.doi && !isDOIValid(article.doi) ? "Format: 10.XXXX/xxx" : ""}>
            <Input value={article.doi} onChange={(e) => set("doi", e.target.value)} placeholder="10.12345/example" />
          </FormField>
        </div>

        <FormField label={`Abstract (${wordCount} words)`} required error={wordCount > 0 && (wordCount < 150 || wordCount > 300) ? `Word count out of range (150–300)` : ""}>
          <Textarea
            rows={6}
            value={article.abstract}
            onChange={(e) => set("abstract", e.target.value)}
            placeholder="Article abstract…"
          />
          <span className={`text-xs font-medium ${wcColor}`}>{wordCount} / 150–300 words</span>
        </FormField>

        <FormField label="Keywords (min 3, max 10)" hint="Type a keyword and press Enter or comma">
          <div className="flex gap-2">
            <Input
              value={kwInput}
              onChange={(e) => setKwInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addKeyword(); } }}
              placeholder="Add keyword…"
            />
            <Button variant="secondary" onClick={addKeyword}>Add</Button>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {(article.keywords || []).map((kw) => (
              <span key={kw} className="inline-flex items-center gap-1 bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                {kw}
                <button onClick={() => removeKeyword(kw)} className="text-blue-500 hover:text-blue-800 leading-none">×</button>
              </span>
            ))}
            {article.keywords?.length === 0 && <span className="text-slate-400 text-xs italic">No keywords added yet</span>}
          </div>
        </FormField>
      </Card>

      {/* Authors */}
      <Card className="p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="font-semibold text-slate-800">Authors</h3>
          <Button variant="secondary" onClick={addAuthor}>+ Add Author</Button>
        </div>

        {article.authors?.map((author, i) => (
          <div key={i} className="border border-slate-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-600">Author {i + 1}</span>
              <div className="flex items-center gap-1">
                <button onClick={() => moveAuthor(i, -1)} disabled={i === 0} className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30">↑</button>
                <button onClick={() => moveAuthor(i, 1)} disabled={i === article.authors.length - 1} className="p-1 text-slate-400 hover:text-slate-600 disabled:opacity-30">↓</button>
                <button onClick={() => removeAuthor(i)} className="p-1 text-red-400 hover:text-red-600">✕</button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <FormField label="First Name" required>
                <Input value={author.first_name} onChange={(e) => updateAuthor(i, "first_name", e.target.value)} placeholder="Jane" />
              </FormField>
              <FormField label="Last Name" required>
                <Input value={author.last_name} onChange={(e) => updateAuthor(i, "last_name", e.target.value)} placeholder="Doe" />
              </FormField>
              <FormField label="Email">
                <Input type="email" value={author.email} onChange={(e) => updateAuthor(i, "email", e.target.value)} placeholder="jane@university.edu" />
              </FormField>
              <FormField label="ORCID">
                <Input value={author.orcid} onChange={(e) => updateAuthor(i, "orcid", e.target.value)} placeholder="0000-0000-0000-0000" />
              </FormField>
              <FormField label="Affiliation" className="col-span-2">
                <Input value={author.affiliation} onChange={(e) => updateAuthor(i, "affiliation", e.target.value)} placeholder="Department, University, Country" />
              </FormField>
            </div>

            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={!!author.corresponding}
                onChange={(e) => updateAuthor(i, "corresponding", e.target.checked)}
                className="w-4 h-4 accent-[#0F3557]"
              />
              <span className="text-slate-700">Corresponding author</span>
            </label>
          </div>
        ))}
      </Card>

      {/* Journal info */}
      <Card className="p-5 space-y-4">
        <h3 className="font-semibold text-slate-800 border-b border-slate-100 pb-2">Journal & Publication Info</h3>

        <div className="grid grid-cols-2 gap-4">
          <FormField label="Journal Name">
            <Select
              value={article.journal_name}
              onChange={(e) => set("journal_name", e.target.value)}
              options={["Novel Energy", "Photomaterials & Devices", "Novel Future Proceedings"]}
            />
          </FormField>
          <FormField label="Publisher Name">
            <Input value={article.publisher_name} onChange={(e) => set("publisher_name", e.target.value)} />
          </FormField>
          <FormField label="ISSN (Print)">
            <Input value={article.issn_print} onChange={(e) => set("issn_print", e.target.value)} placeholder="XXXX-XXXX" />
          </FormField>
          <FormField label="ISSN (Online)">
            <Input value={article.issn_online} onChange={(e) => set("issn_online", e.target.value)} placeholder="XXXX-XXXX" />
          </FormField>
          <FormField label="Volume">
            <Input value={article.volume} onChange={(e) => set("volume", e.target.value)} placeholder="1" />
          </FormField>
          <FormField label="Issue">
            <Input value={article.issue} onChange={(e) => set("issue", e.target.value)} placeholder="1" />
          </FormField>
          <FormField label="Publication Year">
            <Input value={article.pub_date_year} onChange={(e) => set("pub_date_year", e.target.value)} placeholder="2026" />
          </FormField>
          <FormField label="Publisher Location">
            <Input value={article.publisher_loc} onChange={(e) => set("publisher_loc", e.target.value)} />
          </FormField>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <FormField label="Received Date">
            <Input type="date" value={article.received_date} onChange={(e) => set("received_date", e.target.value)} />
          </FormField>
          <FormField label="Accepted Date">
            <Input type="date" value={article.accepted_date} onChange={(e) => set("accepted_date", e.target.value)} />
          </FormField>
          <FormField label="Published Date">
            <Input type="date" value={article.published_date} onChange={(e) => set("published_date", e.target.value)} />
          </FormField>
        </div>

        <FormField label="Copyright Statement">
          <Input value={article.copyright_statement} onChange={(e) => set("copyright_statement", e.target.value)} />
        </FormField>

        <div className="border-t border-slate-100 pt-4">
          <div className="text-sm font-semibold text-slate-700 mb-3">PDF Logos</div>
          <div className="grid grid-cols-2 gap-6">
            <LogoUpload
              label="Journal Logo"
              hint="Replaces the journal initials box (top-left of PDF header)"
              value={article.journal_logo || ""}
              onChange={(v) => set("journal_logo", v)}
            />
            <LogoUpload
              label="Brand / Publisher Logo"
              hint="Replaces the NovelTOR logo (top-right of PDF header)"
              value={article.brand_logo || ""}
              onChange={(v) => set("brand_logo", v)}
            />
          </div>
        </div>
      </Card>

      <div className="flex justify-end pb-8">
        <Button onClick={onNext}>Continue to Sections →</Button>
      </div>
    </div>
  );
}
