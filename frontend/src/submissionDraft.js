export const CUSTOMS_HEADER_FIELDS = [
  'Mawb',
  'Hawb',
  'CustomerName',
  'TradeType',
  'OriginCountry',
  'InvoiceNo',
  'Quantity',
  'GrossWeight',
  'NetWeight',
  'TotalSheets',
  'TotalQuantity',
  'GoodQuantity',
  'TotalPrice',
]

export const CUSTOMS_DETAIL_FIELDS = [
  'ItemCode',
  'ItemOrigin',
  'ItemQuantity',
  'ItemGoodQuantity',
  'ItemPrice',
  'ItemUnitPrice',
]

const DEFAULT_FIELD_TEXT = '-1'
const LEGACY_HEADER_FIELD_MAP = {
  MainBLNo: 'Mawb',
  SubBLNo: 'Hawb',
}

export function createEmptySubmissionDraft() {
  return {
    target: 'vatest.carsem.com.cn',
    header: Object.fromEntries(CUSTOMS_HEADER_FIELDS.map((field) => [field, DEFAULT_FIELD_TEXT])),
    details: [createEmptyDetailRow()],
    meta: {
      required_missing: [],
      unmapped_fields: [],
      auto_mapped: {},
      last_edited_at: '',
      submit_status: 'idle',
      submit_message: '',
      submit_result: null,
    },
  }
}

export function normalizeSubmissionDraft(draft) {
  const normalized = createEmptySubmissionDraft()
  if (!draft || typeof draft !== 'object') return normalized
  normalized.target = String(draft.target || normalized.target)

  if (draft.header && typeof draft.header === 'object') {
    const sourceHeader = normalizeLegacyHeader(draft.header)
    for (const field of CUSTOMS_HEADER_FIELDS) normalized.header[field] = toText(sourceHeader[field], DEFAULT_FIELD_TEXT)
  }

  if (Array.isArray(draft.details)) {
    const detailRows = draft.details
      .filter((item) => item && typeof item === 'object')
      .map((item) => Object.fromEntries(CUSTOMS_DETAIL_FIELDS.map((field) => [field, toText(item[field], DEFAULT_FIELD_TEXT)])))
    normalized.details = detailRows.length > 0 ? detailRows : [createEmptyDetailRow()]
  }

  if (draft.meta && typeof draft.meta === 'object') {
    normalized.meta = {
      ...normalized.meta,
      ...draft.meta,
      required_missing: Array.isArray(draft.meta.required_missing) ? draft.meta.required_missing.map((x) => String(x || '')) : [],
      unmapped_fields: Array.isArray(draft.meta.unmapped_fields) ? draft.meta.unmapped_fields : [],
      auto_mapped: draft.meta.auto_mapped && typeof draft.meta.auto_mapped === 'object' ? draft.meta.auto_mapped : {},
    }
  }

  return normalized
}

export function buildDraftSummary(draft) {
  const normalized = normalizeSubmissionDraft(draft)
  return {
    missingCount: normalized.meta.required_missing.length,
    detailCount: normalized.details.length,
    submitStatus: String(normalized.meta.submit_status || 'idle'),
    submitMessage: String(normalized.meta.submit_message || ''),
  }
}

export function updateDraftHeaderField(draft, field, value) {
  const normalized = normalizeSubmissionDraft(draft)
  if (!CUSTOMS_HEADER_FIELDS.includes(field)) return normalized
  return {
    ...normalized,
    header: {
      ...normalized.header,
      [field]: toText(value, DEFAULT_FIELD_TEXT),
    },
  }
}

export function updateDraftDetailField(draft, index, field, value) {
  const normalized = normalizeSubmissionDraft(draft)
  if (!CUSTOMS_DETAIL_FIELDS.includes(field)) return normalized
  const nextDetails = normalized.details.map((item, idx) => (
    idx === index
      ? { ...item, [field]: toText(value, DEFAULT_FIELD_TEXT) }
      : item
  ))
  return {
    ...normalized,
    details: nextDetails,
  }
}

export function appendDraftDetailRow(draft) {
  const normalized = normalizeSubmissionDraft(draft)
  return {
    ...normalized,
    details: [
      ...normalized.details,
      createEmptyDetailRow(),
    ],
  }
}

export function removeDraftDetailRow(draft, index) {
  const normalized = normalizeSubmissionDraft(draft)
  return {
    ...normalized,
    details: normalized.details.filter((_, idx) => idx !== index),
  }
}

function createEmptyDetailRow() {
  return Object.fromEntries(CUSTOMS_DETAIL_FIELDS.map((field) => [field, DEFAULT_FIELD_TEXT]))
}

function normalizeLegacyHeader(header) {
  const normalized = { ...header }
  for (const [legacyField, currentField] of Object.entries(LEGACY_HEADER_FIELD_MAP)) {
    if (legacyField in normalized && !(currentField in normalized)) normalized[currentField] = normalized[legacyField]
  }
  return normalized
}

function toText(value, fallback = '') {
  if (value == null) return fallback
  if (typeof value === 'string') {
    const text = value.trim()
    return text || fallback
  }
  const text = String(value)
  return text || fallback
}
