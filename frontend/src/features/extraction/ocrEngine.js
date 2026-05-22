export const OCR_ENGINE_OPTIONS = [
  { label: 'MinerU', value: 'mineru' },
  { label: 'OpenDataLoader PDF', value: 'opendataloader' },
  { label: 'Qwen3.5-Plus 端到端', value: 'qwen_vision' },
]

export const DEFAULT_OCR_ENGINE = 'mineru'
export const EXTRACT_UPLOAD_ACCEPT = '.pdf,.png,.jpg,.jpeg,.tiff,.bmp,.gif,.doc,.docx,.ppt,.pptx,.xlsx'

export function normalizeOcrEngine(value) {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'opendataloader') return 'opendataloader'
  if (normalized === 'qwen_vision') return 'qwen_vision'
  return DEFAULT_OCR_ENGINE
}

export function normalizeTemplateOcrEngine(item) {
  return normalizeOcrEngine(item?.ocr_engine)
}

export function ocrEngineLabel(value) {
  return OCR_ENGINE_OPTIONS.find((item) => item.value === normalizeOcrEngine(value))?.label || 'MinerU'
}

export function buildExtractRequestFields(form) {
  return [
    ['vendor', String(form.vendor || '').trim()],
    ['doc_type', String(form.doc_type || '').trim()],
    ['llm_prompt', String(form.llm_prompt || '').trim()],
    ['llm_base_url', String(form.llm_base_url || '').trim()],
    ['llm_model', String(form.llm_model || '').trim()],
    ['llm_api_key', String(form.llm_api_key || '')],
    ['region_rules', String(form.region_rules || '')],
    ['mineru_model_version', String(form.backend || 'vlm')],
    ['backend', String(form.backend || 'vlm')],
    ['parse_method', String(form.parse_method || 'auto')],
    ['lang_list', String(form.lang_list || 'en')],
    ['ocr_engine', normalizeOcrEngine(form.ocr_engine)],
  ]
}
