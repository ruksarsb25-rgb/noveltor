/**
 * Client-side consistency checks matching the NFP enforcement rules.
 */

export function validateArticle(article) {
  const errors = [];
  const warnings = [];

  // Rule 1 — all authors need both names
  (article.authors || []).forEach((a, i) => {
    if (!a.first_name?.trim() || !a.last_name?.trim()) {
      errors.push(`Author ${i + 1}: both first and last name are required`);
    }
  });

  // Rule 2 — at least one corresponding author with email
  const correspondingWithEmail = (article.authors || []).filter(
    (a) => a.corresponding && a.email?.trim()
  );
  if (correspondingWithEmail.length === 0) {
    errors.push("At least one author must be marked as corresponding and have an email address");
  }

  // Rule 3 — abstract word count 150–300
  const words = (article.abstract || "").trim().split(/\s+/).filter(Boolean);
  const wc = words.length;
  if (wc === 0) {
    errors.push("Abstract is required");
  } else if (wc < 150) {
    warnings.push(`Abstract has ${wc} words — minimum is 150`);
  } else if (wc > 300) {
    warnings.push(`Abstract has ${wc} words — maximum is 300`);
  }

  // Rule 4 — 3–10 keywords
  const kwCount = (article.keywords || []).length;
  if (kwCount < 3) {
    errors.push(`Only ${kwCount} keyword(s) — minimum is 3`);
  } else if (kwCount > 10) {
    errors.push(`${kwCount} keywords — maximum is 10`);
  }

  // Rule 5 — DOI format
  if (article.doi?.trim()) {
    if (!/^10\.\d{4,}\/\S+$/.test(article.doi.trim())) {
      errors.push(`DOI format invalid: must match 10.XXXX/xxx`);
    }
  }

  // Rule 6 — section headings non-empty
  (article.sections || []).forEach((s, i) => {
    if (!s.heading?.trim()) {
      errors.push(`Section ${i + 1} has an empty heading`);
    }
  });

  // Rule 7 — references sequential (checked post-generation; skip here)

  // Rule 8 — all figures have captions
  (article.figures || []).forEach((f, i) => {
    if (!f.caption?.trim()) {
      errors.push(`Figure ${i + 1} (${f.label || f.id}) is missing a caption`);
    }
  });

  return { errors, warnings };
}

export function countAbstractWords(abstract) {
  return (abstract || "").trim().split(/\s+/).filter(Boolean).length;
}

export function isDOIValid(doi) {
  if (!doi?.trim()) return true; // blank is OK (just a warning)
  return /^10\.\d{4,}\/\S+$/.test(doi.trim());
}
