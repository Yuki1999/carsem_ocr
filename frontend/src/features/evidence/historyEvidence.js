function getPath(file) {
  return String(file?.path || '').trim()
}

function getLowerPath(file) {
  return getPath(file).toLowerCase()
}

export function classifyEvidenceFile(file) {
  const path = getLowerPath(file)
  const mime = String(file?.mime || '').toLowerCase()
  const isImage = Boolean(file?.is_image) || /\.(png|jpe?g|gif|bmp|webp|tiff?)$/.test(path)
  const isPdf = mime.includes('pdf') || path.endsWith('.pdf')
  const isMarkdown = Boolean(file?.is_text) && (path.endsWith('.md') || path.endsWith('.markdown'))
  const isJson = Boolean(file?.is_text) && path.endsWith('.json')
  const isText = Boolean(file?.is_text) && (path.endsWith('.txt') || isMarkdown)

  if (isPdf) return 'pdf'
  if (isImage) return 'image'
  if (isMarkdown) return 'markdown'
  if (isText || isJson) return 'text'
  return 'download'
}

export function pickPrimaryOriginalFile(files) {
  const list = Array.isArray(files) ? files.filter((file) => getPath(file)) : []
  if (list.length === 0) return null

  const originalPdf = list.find((file) => {
    const path = getLowerPath(file)
    return path.includes('_origin.') && classifyEvidenceFile(file) === 'pdf'
  })
  if (originalPdf) return originalPdf

  const originImage = list.find((file) => {
    const path = getLowerPath(file)
    return path.includes('_origin.') && classifyEvidenceFile(file) === 'image'
  })
  if (originImage) return originImage

  const correctedPdf = list.find((file) => {
    const path = getLowerPath(file)
    return path.includes('preview/final_selected') && classifyEvidenceFile(file) === 'pdf'
  })
  if (correctedPdf) return correctedPdf

  const anyPdf = list.find((file) => classifyEvidenceFile(file) === 'pdf')
  if (anyPdf) return anyPdf

  const correctedImage = list.find((file) => {
    const path = getLowerPath(file)
    return path.includes('preview/final_selected') && classifyEvidenceFile(file) === 'image'
  })
  if (correctedImage) return correctedImage

  return list.find((file) => classifyEvidenceFile(file) === 'image') || null
}

export function chooseDefaultEvidenceTab({ files, hasMarkdownPreview }) {
  if (pickPrimaryOriginalFile(files)) return 'original'
  if (hasMarkdownPreview) return 'markdown'
  if (Array.isArray(files) && files.length > 0) return 'assets'
  return 'markdown'
}

export function resolveOriginalPreviewFile(selectedFile, primaryOriginalFile) {
  if (primaryOriginalFile && getPath(primaryOriginalFile)) return primaryOriginalFile
  return selectedFile && getPath(selectedFile) ? selectedFile : null
}

export function pickPrimaryMarkdownFile(files) {
  const list = Array.isArray(files) ? files.filter((file) => {
    const path = getLowerPath(file)
    return Boolean(path) && Boolean(file?.is_text) && (path.endsWith('.md') || path.endsWith('.markdown'))
  }) : []
  if (list.length === 0) return null

  const exact = list.find((file) => getLowerPath(file) === 'full.md')
  if (exact) return exact

  const withSlash = list.find((file) => getLowerPath(file).endsWith('/full.md'))
  if (withSlash) return withSlash

  const opendataloader = list.find((file) => getLowerPath(file).startsWith('opendataloader/') && getLowerPath(file).endsWith('.md'))
  if (opendataloader) return opendataloader

  return list[0] || null
}
