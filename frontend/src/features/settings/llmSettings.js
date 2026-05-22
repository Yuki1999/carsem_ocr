const DEFAULT_LLM_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
const DEFAULT_LLM_MODEL = 'gemini-3-flash-preview'
const DEFAULT_LLM_API_KEY = ''
const DEFAULT_CUSTOMS_SUBMIT_MODE = 'http'
const LLM_PROVIDER_OPTIONS = ['deepseek', 'gemini', 'bailian', 'custom']

function createId() {
  return `llm-${Math.random().toString(36).slice(2, 10)}`
}

function inferLlmProvider(baseUrl, model) {
  const base = String(baseUrl || '').toLowerCase()
  const mdl = String(model || '').toLowerCase()
  if (base.includes('deepseek.com') || mdl.includes('deepseek')) return 'deepseek'
  if (base.includes('generativelanguage.googleapis.com') || mdl.includes('gemini')) return 'gemini'
  if (base.includes('dashscope.aliyuncs.com') || base.includes('dashscope-intl.aliyuncs.com') || mdl.includes('qwen')) return 'bailian'
  return 'custom'
}

export function normalizeCustomsSubmitMode(mode) {
  const normalized = String(mode || '').trim().toLowerCase()
  return ['http', 'playwright'].includes(normalized) ? normalized : DEFAULT_CUSTOMS_SUBMIT_MODE
}

export function normalizeLlmConfig(item = {}, fallbackName = 'LLM 配置') {
  const base = String(item.llm_base_url || '').trim()
  const model = String(item.llm_model || '').trim()
  const provider = LLM_PROVIDER_OPTIONS.includes(String(item.provider || '').trim())
    ? String(item.provider || '').trim()
    : inferLlmProvider(base, model)
  return {
    id: String(item.id || '').trim() || createId(),
    name: String(item.name || '').trim() || fallbackName,
    provider,
    llm_base_url: base || DEFAULT_LLM_BASE_URL,
    llm_model: model || DEFAULT_LLM_MODEL,
    llm_api_key: String(item.llm_api_key || ''),
  }
}

export function loadLlmSettings(source = null) {
  const defaultItem = normalizeLlmConfig({
    id: createId(),
    name: 'Gemini 默认',
    provider: 'gemini',
    llm_base_url: DEFAULT_LLM_BASE_URL,
    llm_model: DEFAULT_LLM_MODEL,
    llm_api_key: DEFAULT_LLM_API_KEY,
  }, 'Gemini 默认')
  const fallback = {
    active_id: defaultItem.id,
    items: [defaultItem],
    auto_mode_enabled: false,
    customs_submit_mode: DEFAULT_CUSTOMS_SUBMIT_MODE,
  }
  const parsed = source
  if (!parsed || typeof parsed !== 'object') return fallback

  if (typeof parsed.llm_base_url === 'string' || typeof parsed.llm_model === 'string') {
    const single = normalizeLlmConfig({
      id: createId(),
      name: '迁移配置',
      provider: parsed.provider,
      llm_base_url: parsed.llm_base_url,
      llm_model: parsed.llm_model,
      llm_api_key: parsed.llm_api_key,
    }, '迁移配置')
    return {
      active_id: single.id,
      items: [single],
      auto_mode_enabled: Boolean(parsed.auto_mode_enabled),
      customs_submit_mode: normalizeCustomsSubmitMode(parsed.customs_submit_mode),
    }
  }

  if (!Array.isArray(parsed.items) || parsed.items.length === 0) return fallback
  const cleaned = parsed.items
    .map((x, idx) => normalizeLlmConfig(x, `LLM 配置 ${idx + 1}`))
    .filter(Boolean)
  if (cleaned.length === 0) return fallback
  const active = String(parsed.active_id || '').trim()
  const active_id = cleaned.some((x) => x.id === active) ? active : cleaned[0].id
  return {
    active_id,
    items: cleaned,
    auto_mode_enabled: Boolean(parsed.auto_mode_enabled),
    customs_submit_mode: normalizeCustomsSubmitMode(parsed.customs_submit_mode),
  }
}

export function buildLlmSettingsPayloadForTest({
  items = [],
  active_id = '',
  auto_mode_enabled = false,
  customs_submit_mode = DEFAULT_CUSTOMS_SUBMIT_MODE,
} = {}) {
  return {
    active_id,
    items,
    auto_mode_enabled: Boolean(auto_mode_enabled),
    customs_submit_mode: normalizeCustomsSubmitMode(customs_submit_mode),
  }
}
