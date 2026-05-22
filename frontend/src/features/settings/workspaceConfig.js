export const FIXED_WORKSPACE_OCR_ENGINE = 'qwen_vision'
export const DOC_TYPES = ['到货单', '物流通知书', '送货单', '发票', '报关单']

const VENDOR_ALIAS_KEYS = {
  st: 'stmicroelectronics',
  stmicroelectronics: 'stmicroelectronics',
}

export function normalizeVendorKey(value = '') {
  const compact = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[\s._-]+/g, '')
  return VENDOR_ALIAS_KEYS[compact] || compact
}

export function buildVendorOptions(items = []) {
  const vendors = new Set(
    (Array.isArray(items) ? items : [])
      .map((item) => String(item?.vendor || '').trim())
      .filter(Boolean),
  )
  return Array.from(vendors).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export function buildDocTypeOptionsForVendor(items = [], vendor = '') {
  const targetVendor = normalizeVendorKey(vendor)
  if (!targetVendor) return []
  const docTypes = new Set(
    (Array.isArray(items) ? items : [])
      .filter((item) => normalizeVendorKey(item?.vendor) === targetVendor)
      .map((item) => String(item?.doc_type || '').trim())
      .filter(Boolean),
  )
  return Array.from(docTypes)
}

export function resolveDocTypeForVendor(items = [], vendor = '', currentDocType = '') {
  const options = buildDocTypeOptionsForVendor(items, vendor)
  const normalizedDocType = String(currentDocType || '').trim()
  if (options.includes(normalizedDocType)) return normalizedDocType
  return options[0] || ''
}

export function createInitialWorkspaceSelection(docTypes = []) {
  return {
    vendor: '',
    docType: '',
    ocrEngine: FIXED_WORKSPACE_OCR_ENGINE,
  }
}

export function createTemplateDraftDefaults(docTypes = []) {
  return {
    vendor: '',
    doc_type: Array.isArray(docTypes) && docTypes.length > 0 ? docTypes[0] : '',
  }
}

export function chooseTemplateSelection({
  templates = [],
  previousVendor = '',
  previousDocType = '',
  keepCurrentSelection = true,
  fallbackDocType = '',
} = {}) {
  const list = Array.isArray(templates) ? templates : []
  if (keepCurrentSelection) {
    const matched = list.find(
      (item) =>
        normalizeVendorKey(item?.vendor) === normalizeVendorKey(previousVendor) &&
        String(item?.doc_type || '').trim() === String(previousDocType || '').trim(),
    )
    if (matched) {
      return {
        vendor: String(matched.vendor || '').trim(),
        docType: String(matched.doc_type || '').trim(),
        matchedTemplate: matched,
      }
    }
  }
  return {
    vendor: '',
    docType: '',
    matchedTemplate: null,
  }
}
