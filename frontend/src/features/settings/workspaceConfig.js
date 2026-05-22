export const FIXED_WORKSPACE_OCR_ENGINE = 'qwen_vision'
export const DOC_TYPES = ['到货单', '物流通知书', '送货单', '发票', '报关单']
export const COMMON_TEMPLATE_VENDOR = '通用模板'

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

export function isCommonTemplateVendor(value = '') {
  const raw = String(value || '').trim()
  const compact = raw.toLowerCase().replace(/[\s._-]+/g, '')
  return ['通用模板', '通用', 'common', 'default', '*', '__common__'].includes(raw) ||
    ['通用模板', '通用', 'common', 'default', '*', 'common'].includes(compact)
}

export function normalizeTemplateVendor(value = '') {
  return isCommonTemplateVendor(value) ? COMMON_TEMPLATE_VENDOR : String(value || '').trim()
}

export function templateScopeOf(item) {
  return isCommonTemplateVendor(item?.vendor) ? 'common' : 'vendor'
}

function sameTemplateVendor(left = '', right = '') {
  if (isCommonTemplateVendor(left) || isCommonTemplateVendor(right)) {
    return isCommonTemplateVendor(left) && isCommonTemplateVendor(right)
  }
  return normalizeVendorKey(left) === normalizeVendorKey(right)
}

export function buildVendorOptions(items = []) {
  const vendors = new Set(
    (Array.isArray(items) ? items : [])
      .map((item) => normalizeTemplateVendor(item?.vendor))
      .filter((vendor) => !isCommonTemplateVendor(vendor))
      .filter(Boolean),
  )
  return Array.from(vendors).sort((a, b) => a.localeCompare(b, 'zh-CN'))
}

export function buildDocTypeOptionsForVendor(items = [], vendor = '') {
  const targetVendor = String(vendor || '').trim()
  const docTypes = new Set(
    (Array.isArray(items) ? items : [])
      .filter((item) => {
        if (isCommonTemplateVendor(item?.vendor)) return true
        return targetVendor && sameTemplateVendor(item?.vendor, targetVendor)
      })
      .map((item) => String(item?.doc_type || '').trim())
      .filter(Boolean),
  )
  return Array.from(docTypes)
}

export function resolveTemplateForSelection(items = [], vendor = '', docType = '') {
  const list = Array.isArray(items) ? items : []
  const targetVendor = String(vendor || '').trim()
  const targetDocType = String(docType || '').trim()
  if (!targetDocType) return null
  if (targetVendor) {
    const vendorTemplate = list.find(
      (item) =>
        !isCommonTemplateVendor(item?.vendor) &&
        sameTemplateVendor(item?.vendor, targetVendor) &&
        String(item?.doc_type || '').trim() === targetDocType,
    )
    if (vendorTemplate) return vendorTemplate
  }
  return list.find(
    (item) => isCommonTemplateVendor(item?.vendor) && String(item?.doc_type || '').trim() === targetDocType,
  ) || null
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
    scope: 'common',
    vendor: COMMON_TEMPLATE_VENDOR,
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
  const requestedVendor = String(previousVendor || '').trim()
  const requestedDocType = String(previousDocType || '').trim()
  if (keepCurrentSelection) {
    const matched = resolveTemplateForSelection(list, requestedVendor, requestedDocType)
    if (matched) {
      return {
        vendor: isCommonTemplateVendor(matched.vendor) ? requestedVendor : String(matched.vendor || '').trim(),
        docType: String(matched.doc_type || '').trim(),
        matchedTemplate: matched,
      }
    }
  }
  const fallback = resolveTemplateForSelection(list, requestedVendor, fallbackDocType)
  if (fallback) {
    return {
      vendor: isCommonTemplateVendor(fallback.vendor) ? requestedVendor : String(fallback.vendor || '').trim(),
      docType: String(fallback.doc_type || '').trim(),
      matchedTemplate: fallback,
    }
  }
  return {
    vendor: '',
    docType: '',
    matchedTemplate: null,
  }
}
