/**
 * Naive XML syntax highlighter — returns HTML string safe to set via dangerouslySetInnerHTML.
 */
export function highlightXML(xml) {
  return xml
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(
      /(&lt;\/?)([\w:.-]+)/g,
      '<span class="xml-tag">$1$2</span>'
    )
    .replace(
      /([\w:.-]+=)(&quot;[^&]*&quot;|"[^"]*")/g,
      '<span class="xml-attr">$1</span><span class="xml-value">$2</span>'
    )
    .replace(/&quot;/g, '"');
}
