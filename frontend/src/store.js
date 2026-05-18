/**
 * Central article state — passed down as props.
 * Saved to / loaded from localStorage as a single JSON blob.
 */

export const STORAGE_KEY = "nfp_draft";

export const ARTICLE_TYPES = [
  "Research Article",
  "Review",
  "Conference Proceeding",
  "Enhanced Poster Article",
  "Conference Report",
];

export const SECTION_TYPES = [
  "Introduction",
  "Methods",
  "Results",
  "Discussion",
  "Conclusion",
  "Acknowledgements",
  "Other",
];

export function defaultArticle() {
  return {
    // Metadata
    title: "",
    authors: [defaultAuthor()],
    abstract: "",
    keywords: [],
    journal_name: "Novel Future Proceedings",
    journal_id: "nfp",
    issn_print: "",
    issn_online: "",
    volume: "",
    issue: "",
    pub_date_year: new Date().getFullYear().toString(),
    pub_date_month: "",
    pub_date_day: "",
    doi: "",
    article_type: "Conference Proceeding",
    received_date: "",
    accepted_date: "",
    published_date: "",
    publisher_name: "Novel Future Publishers Inc.",
    publisher_loc: "Canada",
    copyright_statement:
      "© 2026 Novel Future Publishers Inc. Open Access article under CC BY 4.0 license.",

    // Logos (base64 data URIs, set by user upload)
    journal_logo: "",
    brand_logo: "",

    // Content
    sections: [],
    references: [],
    figures: [],
  };
}

export function defaultAuthor() {
  return {
    first_name: "",
    last_name: "",
    affiliation: "",
    email: "",
    orcid: "",
    corresponding: true,
  };
}

export function defaultSection() {
  return {
    id: crypto.randomUUID(),
    heading: "",
    type: "Other",
    content: [],
    subsections: [],
    ai_suggested: false,
  };
}

/** Extract the plain paragraph text from a section (or subsection) for display in a textarea. */
export function sectionBodyText(sec) {
  const content = sec?.content;
  if (Array.isArray(content) && content.length > 0) {
    return content
      .filter((b) => b.type === "paragraph")
      .map((b) => b.text || "")
      .join("\n\n");
  }
  return sec?.body || "";
}

/** Return a new section with updated paragraph text, preserving inline table blocks. */
export function setSectionBody(sec, text) {
  const newParas = text
    .split(/\n{2,}/)
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t) => ({ type: "paragraph", text: t }));

  if (Array.isArray(sec.content)) {
    const tableBlocks = sec.content.filter((b) => b.type === "table");
    return { ...sec, content: [...newParas, ...tableBlocks] };
  }
  return { ...sec, body: text };
}

/** Return table blocks embedded in a section's content array. */
export function sectionTableBlocks(sec) {
  if (Array.isArray(sec?.content)) {
    return sec.content.filter((b) => b.type === "table");
  }
  return [];
}

/** Return figure blocks embedded in a section's content array. */
export function sectionFigureBlocks(sec) {
  if (Array.isArray(sec?.content)) {
    return sec.content.filter((b) => b.type === "figure");
  }
  return [];
}

export function saveDraft(article) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(article));
  } catch (e) {
    console.warn("Could not save draft:", e);
  }
}

export function loadDraft() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function clearDraft() {
  localStorage.removeItem(STORAGE_KEY);
}
