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
      packet: createEmptyPacketMeta(),
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
      packet: normalizePacketMeta(draft.meta.packet),
    }
  }

  return normalized
}

export function buildDraftSummary(draft) {
  const normalized = normalizeSubmissionDraft(draft)
  const missingCount = normalized.meta.required_missing.length
  const reviewCount = countPacketReviewItems(normalized.meta.packet)
  return {
    missingCount,
    reviewCount,
    hasReviewWarnings: missingCount > 0 || reviewCount > 0,
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

function createEmptyPacketMeta() {
  return {
    packet_id: '',
    source_files: [],
    header_candidates: {},
    field_reviews: [],
    invoice_lines: [],
    packing_groups: [],
    detail_reviews: [],
  }
}

function normalizePacketMeta(packet) {
  const normalized = createEmptyPacketMeta()
  if (!packet || typeof packet !== 'object') return normalized
  return {
    ...normalized,
    ...packet,
    packet_id: toText(packet.packet_id, ''),
    source_files: Array.isArray(packet.source_files) ? packet.source_files.filter((item) => item && typeof item === 'object') : [],
    header_candidates: packet.header_candidates && typeof packet.header_candidates === 'object' ? packet.header_candidates : {},
    field_reviews: Array.isArray(packet.field_reviews) ? packet.field_reviews.filter((item) => item && typeof item === 'object') : [],
    invoice_lines: Array.isArray(packet.invoice_lines) ? packet.invoice_lines.filter((item) => item && typeof item === 'object') : [],
    packing_groups: Array.isArray(packet.packing_groups) ? packet.packing_groups.filter((item) => item && typeof item === 'object') : [],
    detail_reviews: Array.isArray(packet.detail_reviews) ? packet.detail_reviews.filter((item) => item && typeof item === 'object') : [],
  }
}

function countPacketReviewItems(packet) {
  const normalized = normalizePacketMeta(packet)
  const fieldCount = normalized.field_reviews.filter((item) => Boolean(item.review_required)).length
  const detailCount = normalized.detail_reviews.filter((item) => Boolean(item.review_required)).length
  return fieldCount + detailCount
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
