export function isImageOnlyMarkdown(content) {
  const raw = String(content || '').trim()
  if (!raw) return false
  const blocks = raw
    .split(/\n\s*\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
  if (blocks.length === 0) return false
  return blocks.every((block) => /^!\[[^\]]*\]\([^)]+\)$/.test(block))
}

export function choosePreferredMarkdownPreview({ ocrEngine, markdownContent, fallbackText }) {
  const markdown = String(markdownContent || '').trim()
  const fallback = String(fallbackText || '').trim()
  if (String(ocrEngine || '').trim().toLowerCase() === 'opendataloader' && isImageOnlyMarkdown(markdown) && fallback) {
    return fallback
  }
  return markdown || fallback
}
