import React, { useState } from "react";
import { API_BASE } from "../utils/api.js";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, Card } from "../components/FormField.jsx";
import { FormField, Input, Textarea, Select } from "../components/FormField.jsx";
import { SECTION_TYPES, defaultSection, sectionBodyText, setSectionBody, sectionTableBlocks, sectionFigureBlocks } from "../store.js";
import toast from "react-hot-toast";

function SortableSection({ section, onChange, onRemove }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 50 : "auto",
  };

  const updateSub = (i, field, value) => {
    const subs = [...(section.subsections || [])];
    subs[i] = field === "body" ? setSectionBody(subs[i], value) : { ...subs[i], [field]: value };
    onChange({ ...section, subsections: subs });
  };

  const addSub = () =>
    onChange({ ...section, subsections: [...(section.subsections || []), { heading: "", content: [] }] });

  const removeSub = (i) =>
    onChange({ ...section, subsections: section.subsections.filter((_, idx) => idx !== i) });

  return (
    <div ref={setNodeRef} style={style} className="border border-slate-200 rounded-lg bg-white shadow-sm">
      <div className="flex items-start gap-3 p-4">
        {/* Drag handle */}
        <button
          {...attributes}
          {...listeners}
          className="drag-handle mt-1 text-slate-300 hover:text-slate-500 p-1 -ml-1"
          title="Drag to reorder"
        >
          ⠿
        </button>

        <div className="flex-1 space-y-3">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <Input
                  value={section.heading}
                  onChange={(e) => onChange({ ...section, heading: e.target.value })}
                  placeholder="Section heading"
                  className="font-semibold"
                />
                {section.ai_suggested && (
                  <span title="AI-suggested tag" className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                )}
              </div>
            </div>
            <Select
              value={section.type}
              onChange={(e) => onChange({ ...section, type: e.target.value, ai_suggested: false })}
              options={SECTION_TYPES}
              className="w-44"
            />
            <button onClick={onRemove} className="text-red-400 hover:text-red-600 p-1 mt-0.5">✕</button>
          </div>

          <Textarea
            value={sectionBodyText(section)}
            onChange={(e) => onChange(setSectionBody(section, e.target.value))}
            placeholder="Section body text…"
            rows={4}
          />

          {/* Inline table and figure previews */}
          {sectionTableBlocks(section).map((tbl, ti) => (
            <div key={`tbl-${ti}`} className="ml-1 mt-1">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{tbl.label || tbl.caption}</span>
              <TablePreview table={tbl} />
            </div>
          ))}
          {sectionFigureBlocks(section).map((fig, fi) => (
            <FigurePreview key={`fig-${fi}`} figure={fig} />
          ))}

          {/* Subsections */}
          {(section.subsections || []).map((sub, i) => (
            <div key={i} className="ml-4 border-l-2 border-slate-200 pl-4 space-y-2">
              <div className="flex items-center gap-2">
                <Input
                  value={sub.heading}
                  onChange={(e) => updateSub(i, "heading", e.target.value)}
                  placeholder="Subsection heading"
                  className="text-sm"
                />
                <button onClick={() => removeSub(i)} className="text-red-400 hover:text-red-600 text-xs">✕</button>
              </div>
              <Textarea
                value={sectionBodyText(sub)}
                onChange={(e) => updateSub(i, "body", e.target.value)}
                placeholder="Subsection body…"
                rows={3}
                className="text-sm"
              />
              {sectionTableBlocks(sub).map((tbl, ti) => (
                <div key={`tbl-${ti}`} className="ml-1">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{tbl.label || tbl.caption}</span>
                  <TablePreview table={tbl} />
                </div>
              ))}
              {sectionFigureBlocks(sub).map((fig, fi) => (
                <FigurePreview key={`fig-${fi}`} figure={fig} />
              ))}
            </div>
          ))}

          <button
            onClick={addSub}
            className="text-xs text-blue-600 hover:text-blue-800 mt-1"
          >
            + Add subsection
          </button>
        </div>
      </div>
    </div>
  );
}

function FigurePreview({ figure }) {
  const label   = figure.label || "Figure";
  const caption = figure.caption || "";
  const dataUri = figure.data_uri || "";
  return (
    <div className="mt-2 rounded border border-slate-200 overflow-hidden">
      {dataUri ? (
        <img src={dataUri} alt={label} className="max-w-full block mx-auto" />
      ) : (
        <div className="bg-slate-50 py-6 text-center text-xs text-slate-400">[{label}]</div>
      )}
      {caption && (
        <div className="px-2 py-1 text-xs text-slate-500 bg-white border-t border-slate-100 italic">
          <strong>{label}.</strong> {caption}
        </div>
      )}
    </div>
  );
}

function TablePreview({ table }) {
  const previewRows = table.rows.slice(0, 3);
  const hasCols = table.headers?.length > 0;
  if (!hasCols && previewRows.length === 0) return null;
  return (
    <div className="overflow-x-auto mt-2 rounded border border-slate-200">
      <table className="min-w-full text-xs">
        {hasCols && (
          <thead className="bg-slate-100">
            <tr>
              {table.headers.map((h, i) => (
                <th key={i} className="px-2 py-1 text-left font-medium text-slate-700 border-b border-slate-200">{h || "—"}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {previewRows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-slate-50"}>
              {row.map((cell, ci) => (
                <td key={ci} className="px-2 py-1 text-slate-600 border-b border-slate-100">{cell || "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {table.rows.length > 3 && (
        <div className="text-center text-xs text-slate-400 py-1 bg-slate-50">
          +{table.rows.length - 3} more row{table.rows.length - 3 !== 1 ? "s" : ""}
        </div>
      )}
    </div>
  );
}

export default function SectionsScreen({ article, onChange, onNext }) {
  const [autoTagging, setAutoTagging] = useState(false);
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const sections = article.sections || [];
  const references = article.references || [];
  const figures = article.figures || [];

  // Tables now live inside section content blocks; collect them for the overview card
  const allTables = sections.flatMap((sec) => {
    const top = sectionTableBlocks(sec);
    const sub = (sec.subsections || []).flatMap((s) => sectionTableBlocks(s));
    return [...top, ...sub];
  });

  const updateSection = (i, updated) => {
    const next = [...sections];
    next[i] = updated;
    onChange({ ...article, sections: next });
  };

  const removeSection = (i) => {
    onChange({ ...article, sections: sections.filter((_, idx) => idx !== i) });
  };

  const addSection = () => {
    onChange({ ...article, sections: [...sections, defaultSection()] });
  };

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = sections.findIndex((s) => s.id === active.id);
      const newIndex = sections.findIndex((s) => s.id === over.id);
      onChange({ ...article, sections: arrayMove(sections, oldIndex, newIndex) });
    }
  };

  const handleAutoTag = async () => {
    const text = [
      article.title,
      article.abstract,
      ...sections.map((s) => `${s.heading}\n${sectionBodyText(s)}`),
    ].join("\n\n");

    setAutoTagging(true);
    try {
      const res = await fetch(`${API_BASE}/autotag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || "Auto-tag failed");
      }
      const data = await res.json();

      // Apply section types from AI response
      let updated = [...sections];
      if (data.sections && Array.isArray(data.sections)) {
        data.sections.forEach((aiSec) => {
          const match = updated.findIndex(
            (s) => s.heading?.toLowerCase().includes(aiSec.heading?.toLowerCase().slice(0, 10))
          );
          if (match >= 0) {
            updated[match] = { ...updated[match], type: aiSec.type, ai_suggested: true };
          }
        });
      }

      const articleType = data.article_type || article.article_type;
      onChange({ ...article, sections: updated, article_type: articleType });

      const missing = data.missing_sections || [];
      if (missing.length) {
        toast(`AI flagged missing sections: ${missing.join(", ")}`, { icon: "⚠️" });
      } else {
        toast.success("AI auto-tag applied successfully");
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setAutoTagging(false);
    }
  };

  // Normalize a reference to a dict (handles legacy string refs gracefully)
  const refText = (ref) => (typeof ref === "object" && ref !== null ? ref.raw_text ?? "" : ref ?? "");
  const refDoi  = (ref) => (typeof ref === "object" && ref !== null ? ref.doi ?? "" : "");

  const updateReference = (i, field, value) => {
    const refs = [...references];
    const cur = refs[i];
    refs[i] = typeof cur === "object" && cur !== null
      ? { ...cur, [field]: value }
      : { number: i + 1, raw_text: field === "raw_text" ? value : cur, doi: field === "doi" ? value : "" };
    onChange({ ...article, references: refs });
  };

  const addReference = () =>
    onChange({ ...article, references: [...references, { number: references.length + 1, raw_text: "", doi: "" }] });
  const removeReference = (i) =>
    onChange({ ...article, references: references.filter((_, idx) => idx !== i) });

  const updateFigure = (i, field, value) => {
    const figs = [...figures];
    figs[i] = { ...figs[i], [field]: value };
    onChange({ ...article, figures: figs });
  };

  const addFigure = () =>
    onChange({
      ...article,
      figures: [...figures, { id: `fig${figures.length + 1}`, label: `Figure ${figures.length + 1}`, caption: "", href: "" }],
    });
  const removeFigure = (i) => onChange({ ...article, figures: figures.filter((_, idx) => idx !== i) });

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-[#0F3557]">Section Editor</h2>
          <p className="text-slate-500 text-sm mt-1">
            Drag to reorder sections. Blue dot = AI-suggested tag.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleAutoTag}
            disabled={autoTagging}
          >
            {autoTagging ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
                Tagging…
              </>
            ) : (
              "✨ AI Auto-tag"
            )}
          </Button>
          <Button onClick={onNext}>Continue to Export →</Button>
        </div>
      </div>

      {/* Body sections */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-800">Body Sections</h3>
          <Button variant="secondary" onClick={addSection}>+ Add Section</Button>
        </div>

        {sections.length === 0 ? (
          <p className="text-slate-400 text-sm italic text-center py-8">
            No sections found. Add one manually or upload a document with headings.
          </p>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {sections.map((section, i) => (
                  <SortableSection
                    key={section.id}
                    section={section}
                    onChange={(updated) => updateSection(i, updated)}
                    onRemove={() => removeSection(i)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </Card>

      {/* Figures */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-800">Figures & Tables</h3>
          <Button variant="secondary" onClick={addFigure}>+ Add Figure</Button>
        </div>
        {figures.length === 0 ? (
          <p className="text-slate-400 text-sm italic">No figures detected.</p>
        ) : (
          <div className="space-y-3">
            {figures.map((fig, i) => (
              <div key={fig.id} className="border border-slate-200 rounded-lg p-4 grid grid-cols-3 gap-3 items-start">
                <FormField label="Label">
                  <Input value={fig.label} onChange={(e) => updateFigure(i, "label", e.target.value)} />
                </FormField>
                <FormField label="File / href">
                  <Input value={fig.href} onChange={(e) => updateFigure(i, "href", e.target.value)} placeholder="figure1.png" />
                </FormField>
                <div className="flex items-end">
                  <button onClick={() => removeFigure(i)} className="text-red-400 hover:text-red-600 text-sm pb-2">Remove</button>
                </div>
                <FormField label="Caption" className="col-span-3">
                  <Textarea value={fig.caption} onChange={(e) => updateFigure(i, "caption", e.target.value)} rows={2} />
                </FormField>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Tables — inline in sections, shown here as overview only */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-800">Tables</h3>
          {allTables.length > 0 && (
            <span className="text-xs text-slate-400">{allTables.length} table{allTables.length !== 1 ? "s" : ""} — appear inline in PDF</span>
          )}
        </div>
        {allTables.length === 0 ? (
          <p className="text-slate-400 text-sm italic">No tables detected.</p>
        ) : (
          <div className="space-y-4">
            {allTables.map((tbl, i) => (
              <div key={i} className="border border-slate-200 rounded-lg p-4 space-y-2">
                <p className="text-sm font-semibold text-slate-700">{tbl.caption || tbl.label}</p>
                <TablePreview table={tbl} />
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* References */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-800">References</h3>
          <Button variant="secondary" onClick={addReference}>+ Add Reference</Button>
        </div>
        {references.length === 0 ? (
          <p className="text-slate-400 text-sm italic">No references detected.</p>
        ) : (
          <div className="space-y-3">
            {references.map((ref, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-xs text-slate-400 mt-2.5 w-7 text-right flex-shrink-0">[{i + 1}]</span>
                <div className="flex-1 space-y-1">
                  <Input
                    value={refText(ref)}
                    onChange={(e) => updateReference(i, "raw_text", e.target.value)}
                    placeholder="Reference citation text…"
                  />
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-slate-400 flex-shrink-0">DOI</span>
                    <Input
                      value={refDoi(ref)}
                      onChange={(e) => updateReference(i, "doi", e.target.value)}
                      placeholder="10.xxxx/xxxxx"
                      className="text-xs"
                    />
                    {refDoi(ref) && (
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded flex-shrink-0">✓</span>
                    )}
                  </div>
                </div>
                <button onClick={() => removeReference(i)} className="text-red-400 hover:text-red-600 mt-2 text-sm flex-shrink-0">✕</button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="flex justify-end pb-8">
        <Button onClick={onNext}>Continue to Export →</Button>
      </div>
    </div>
  );
}
