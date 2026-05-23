<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  Bell,
  CircleCheck,
  Clock,
  Connection,
  Cpu,
  DataAnalysis,
  Document,
  DocumentChecked,
  Download,
  EditPen,
  Files,
  FolderOpened,
  FullScreen,
  Grid,
  HomeFilled,
  Lock,
  Management,
  Operation,
  Plus,
  RefreshRight,
  Search,
  Setting,
  Upload,
  UploadFilled,
  UserFilled,
} from '@element-plus/icons-vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import {
  EXTRACT_UPLOAD_ACCEPT,
  buildExtractRequestFields,
  normalizeTemplateOcrEngine,
} from './features/extraction/ocrEngine'
import {
  DOC_TYPES,
  FIXED_WORKSPACE_OCR_ENGINE,
  COMMON_TEMPLATE_VENDOR,
  buildDocTypeOptionsForVendor,
  buildVendorOptions,
  chooseTemplateSelection,
  createInitialWorkspaceSelection,
  createTemplateDraftDefaults,
  isCommonTemplateVendor,
  normalizeTemplateVendor,
  normalizeVendorKey,
  resolveDocTypeForVendor,
  resolveTemplateForSelection,
  templateScopeOf,
} from './features/settings/workspaceConfig'
import {
  CUSTOMS_DETAIL_FIELDS,
  CUSTOMS_HEADER_FIELDS,
  appendDraftDetailRow,
  buildDraftSummary,
  createEmptySubmissionDraft,
  normalizeSubmissionDraft,
  removeDraftDetailRow,
} from './features/extraction/submissionDraft'
import {
  chooseDefaultEvidenceTab,
  classifyEvidenceFile,
  pickPrimaryMarkdownFile,
  pickPrimaryOriginalFile,
  resolveOriginalPreviewFile,
} from './features/evidence/historyEvidence'
import { buildAutoModeStatusView } from './features/auto-mode/autoModeStatus'
import { shouldPersistAutoModeChange } from './features/auto-mode/autoModePersistence'
import { choosePreferredMarkdownPreview } from './features/evidence/evidencePreview'
import {
  buildExtractionLaunchReview,
  buildFieldDetailView,
} from './features/ui/layeredInteractions'
import {
  buildFallbackPlatformInsights,
  buildInsightCards,
  normalizePlatformInsights,
} from './features/platform/platformInsights'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const PARSE_METHODS = ['auto', 'txt', 'ocr']
const DEFAULT_MODEL_VERSION = 'vlm'
const DEFAULT_PARSE_METHOD = 'auto'
const DEFAULT_LANG_LIST = 'en'
const DEFAULT_LLM_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
const DEFAULT_LLM_MODEL = 'gemini-3-flash-preview'
const DEFAULT_LLM_API_KEY = ''
const DEFAULT_CUSTOMS_SUBMIT_MODE = 'http'
const LLM_PROVIDER_OPTIONS = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'Gemini', value: 'gemini' },
  { label: '百炼', value: 'bailian' },
  { label: '自定义', value: 'custom' },
]
const LLM_PROVIDER_PRESETS = {
  deepseek: {
    base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-chat',
  },
  gemini: {
    base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
    model: 'gemini-3-flash-preview',
  },
  bailian: {
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen3.5-plus',
  },
}

const initialWorkspaceSelection = createInitialWorkspaceSelection(DOC_TYPES)
const templateDraft = ref(createTemplateDraftDefaults(DOC_TYPES))

const templates = ref(loadTemplates())
const templatesLoading = ref(false)
const selectedVendor = ref(initialWorkspaceSelection.vendor)
const selectedDocType = ref(initialWorkspaceSelection.docType)
const initialLlmSettings = loadLlmSettings()
const llmConfigs = ref(initialLlmSettings.items)
const activeLlmConfigId = ref(initialLlmSettings.active_id)
const activeLlmConfig = computed(() => llmConfigs.value.find((x) => x.id === activeLlmConfigId.value) || null)
if (!activeLlmConfig.value && llmConfigs.value[0]?.id) activeLlmConfigId.value = llmConfigs.value[0].id
const llmProvider = ref(activeLlmConfig.value?.provider || inferLlmProvider(DEFAULT_LLM_BASE_URL, DEFAULT_LLM_MODEL))
const llmConfigDialogVisible = ref(false)
const llmConfigDialogMode = ref('create')
const llmSettingsLoading = ref(false)
const llmConfigDraft = ref({
  id: '',
  name: '',
  provider: 'gemini',
  llm_base_url: DEFAULT_LLM_BASE_URL,
  llm_model: DEFAULT_LLM_MODEL,
  llm_api_key: DEFAULT_LLM_API_KEY,
})
const llmConfigDialogTitle = computed(() => (llmConfigDialogMode.value === 'edit' ? '编辑 LLM 配置' : '新增 LLM 配置'))
const activeLlmConfigName = computed(() => activeLlmConfig.value?.name || '-')
const autoModeEnabled = ref(Boolean(initialLlmSettings.auto_mode_enabled))
const customsSubmitMode = ref(String(initialLlmSettings.customs_submit_mode || DEFAULT_CUSTOMS_SUBMIT_MODE))
const autoModeReady = ref(false)

const form = ref({
  llm_prompt: '请提取物流通知书（到货单）关键信息，以 JSON 返回：{"通知书编号":"","供应商名称":"","到货日期":"","采购订单号":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
  region_rules: '',
  llm_base_url: activeLlmConfig.value?.llm_base_url || DEFAULT_LLM_BASE_URL,
  llm_model: activeLlmConfig.value?.llm_model || DEFAULT_LLM_MODEL,
  llm_api_key: activeLlmConfig.value?.llm_api_key || DEFAULT_LLM_API_KEY,
  ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
  backend: DEFAULT_MODEL_VERSION,
  parse_method: DEFAULT_PARSE_METHOD,
  lang_list: DEFAULT_LANG_LIST,
})

const file = ref(null)
const dragOver = ref(false)
const submitting = ref(false)
const previewCollapsed = ref(false)
const result = ref(null)
const historyItems = ref([])
const historyLoading = ref(false)
const taskItems = ref([])
const taskLoading = ref(false)
const platformInsightsSource = ref(null)
const platformInsightsLoading = ref(false)
const platformInsightsError = ref('')
const activeTaskId = ref('')
const activeTaskNotifiedDone = ref(false)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1440)
const viewportHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 900)
const deletingHistoryId = ref('')
const selectedHistoryId = ref('')
const historyDetail = ref(null)
const submissionDraft = ref(createEmptySubmissionDraft())
const submissionDraftLoading = ref(false)
const submissionDraftSaving = ref(false)
const customsSubmitting = ref(false)
const customsSubmitTaskId = ref('')
let customsSubmitPollTimer = null
const selectedHistoryFile = ref(null)
const resultEvidenceTab = ref('markdown')
const historyFileLoading = ref(false)
const historyFileText = ref('')
const historyFileTextTruncated = ref(false)
const fullMdContent = ref('')
const fullMdPath = ref('')
const fullMdLoading = ref(false)
const fullMdTruncated = ref(false)
const historyPageMarginsMd = ref('')
const historyPageMarginsPages = ref([])
const fileInput = ref(null)
const previewPaneRef = ref(null)
const previewPaneModalRef = ref(null)
const previewModalVisible = ref(false)
const templatePickerVisible = ref(false)
const templatePickerQuery = ref('')
const templateScopeFilter = ref('all')
const extractConfirmVisible = ref(false)
const platformInsightsDialogVisible = ref(false)
const uploadWizardVisible = ref(false)
const uploadWizardStep = ref(0)
const fieldDetailVisible = ref(false)
const selectedFieldDetailRow = ref(null)
const submissionExtraFieldsVisible = ref(false)
const templateEditorVisible = ref(false)
const templateEditorMode = ref('create')
const editingTemplateKey = ref('')
const templateEditorSnapshot = ref(null)
const templateEditorCommitted = ref(false)
const sampleFileInput = ref(null)
const sampleCanvas = ref(null)
const sampleDocKind = ref('')
const sampleFileName = ref('')
const samplePdfPage = ref(1)
const samplePdfPages = ref(1)
const sampleRuleField = ref('')
const fieldDraft = ref('')
const templateFieldItems = ref([])
const isDrawingRule = ref(false)
const draftRule = ref(null)
const ruleDrawStart = ref(null)
let samplePdfDoc = null
let taskPollTimer = null
const currentNav = ref('overview')
const extractWorkspaceTab = ref('upload')
const resultWorkspaceTab = ref('goods')
const uploadWizardSteps = [
  { title: '选择模板', desc: '确认来源和文档类型' },
  { title: '上传资料', desc: '导入本次要识别的文件' },
  { title: '启动任务', desc: '检查后进入后台处理' },
]
const NAV_ITEMS = [
  { key: 'overview', label: '总览', desc: '智能文档处理总览', icon: HomeFilled },
  { key: 'extract', label: '处理工作台', desc: '上传与处理', icon: DocumentChecked },
  { key: 'result', label: '审核中心', desc: '证据与草稿', icon: Management },
  { key: 'template', label: '模板中心', desc: '字段与规则', icon: Grid },
  { key: 'evidence', label: '证据中心', desc: '原文与证据', icon: FolderOpened },
  { key: 'automation', label: '自动化任务', desc: '队列与调度', icon: Cpu },
  { key: 'settings', label: '系统设置', desc: '模型与自动化', icon: Setting },
]
const currentNavItem = computed(() => NAV_ITEMS.find((item) => item.key === currentNav.value) || NAV_ITEMS[0])
const markdown = new MarkdownIt({
  html: true,
  linkify: true,
  breaks: true,
})

function createId() {
  try {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
      return globalThis.crypto.randomUUID()
    }
  } catch {
    // ignore
  }
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function inferLlmProvider(baseUrl, model) {
  const base = String(baseUrl || '').toLowerCase()
  const mdl = String(model || '').toLowerCase()
  if (base.includes('deepseek.com') || mdl.includes('deepseek')) return 'deepseek'
  if (base.includes('generativelanguage.googleapis.com') || mdl.includes('gemini')) return 'gemini'
  if (base.includes('dashscope.aliyuncs.com') || base.includes('dashscope-intl.aliyuncs.com') || mdl.includes('qwen')) return 'bailian'
  return 'custom'
}

function llmProviderLabel(provider) {
  return LLM_PROVIDER_OPTIONS.find((x) => x.value === provider)?.label || '自定义'
}

function sanitizeLegacyPrompt(promptText) {
  const raw = String(promptText || '')
  if (!raw) return ''
  return raw
    .replaceAll('每项至少包含“商品号”', '每项字段按单据原文提取')
}

function normalizeLlmConfig(item, fallbackName = 'LLM 配置') {
  if (!item || typeof item !== 'object') return null
  const base = String(item.llm_base_url || '').trim()
  const model = String(item.llm_model || '').trim()
  const provider = LLM_PROVIDER_OPTIONS.some((x) => x.value === item.provider)
    ? item.provider
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

function normalizeCustomsSubmitMode(mode) {
  const normalized = String(mode || '').trim().toLowerCase()
  return ['http', 'playwright'].includes(normalized) ? normalized : DEFAULT_CUSTOMS_SUBMIT_MODE
}

function loadLlmSettings(source = null) {
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

  // Legacy single-config payload compatibility.
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

function syncFormByLlmConfig(config) {
  if (!config) return
  form.value.llm_base_url = String(config.llm_base_url || '').trim()
  form.value.llm_model = String(config.llm_model || '').trim()
  form.value.llm_api_key = String(config.llm_api_key || '')
  llmProvider.value = LLM_PROVIDER_OPTIONS.some((x) => x.value === config.provider)
    ? config.provider
    : inferLlmProvider(config.llm_base_url, config.llm_model)
}

function syncActiveLlmConfigFromForm() {
  const id = String(activeLlmConfigId.value || '').trim()
  if (!id) return
  const target = llmConfigs.value.find((x) => x.id === id)
  if (!target) return
  target.provider = llmProvider.value
  target.llm_base_url = String(form.value.llm_base_url || '').trim()
  target.llm_model = String(form.value.llm_model || '').trim()
  target.llm_api_key = String(form.value.llm_api_key || '')
}

function applyLoadedLlmSettings(settings) {
  llmConfigs.value = settings.items
  activeLlmConfigId.value = settings.active_id
  autoModeEnabled.value = Boolean(settings.auto_mode_enabled)
  customsSubmitMode.value = normalizeCustomsSubmitMode(settings.customs_submit_mode)
  const target = llmConfigs.value.find((x) => x.id === activeLlmConfigId.value) || llmConfigs.value[0]
  if (target) syncFormByLlmConfig(target)
}

watch(autoModeEnabled, async (nextValue, previousValue) => {
  if (!shouldPersistAutoModeChange({
    previousValue,
    nextValue,
    loading: llmSettingsLoading.value,
    hasActiveConfig: Boolean(activeLlmConfig.value),
    initialized: autoModeReady.value,
  })) {
    return
  }
  const ok = await persistLlmSettings({ silent: true })
  if (ok) {
    pushToast(nextValue ? '自动模式已开启' : '自动模式已关闭', 'success', 1800)
    return
  }
  autoModeEnabled.value = Boolean(previousValue)
  pushToast('自动模式保存失败', 'error')
})

watch(customsSubmitMode, async (nextValue, previousValue) => {
  if (!autoModeReady.value) return
  if (llmSettingsLoading.value) return
  if (!activeLlmConfig.value) return
  const nextMode = normalizeCustomsSubmitMode(nextValue)
  const prevMode = normalizeCustomsSubmitMode(previousValue)
  if (nextMode === prevMode) return
  const ok = await persistLlmSettings({ silent: true })
  if (ok) {
    pushToast(`目标系统提交模式已切换为 ${nextMode}`, 'success', 1800)
    return
  }
  customsSubmitMode.value = prevMode
  pushToast('目标系统提交模式保存失败', 'error')
})

function buildLlmSettingsPayload() {
  syncActiveLlmConfigFromForm()
  const items = llmConfigs.value
    .map((x, idx) => normalizeLlmConfig(x, `LLM 配置 ${idx + 1}`))
    .filter(Boolean)
  if (items.length === 0) return null
  const active_id = items.some((x) => x.id === activeLlmConfigId.value) ? activeLlmConfigId.value : items[0].id
  if (activeLlmConfigId.value !== active_id) activeLlmConfigId.value = active_id
  return {
    active_id,
    items,
    auto_mode_enabled: Boolean(autoModeEnabled.value),
    customs_submit_mode: normalizeCustomsSubmitMode(customsSubmitMode.value),
  }
}

async function loadLlmSettingsFromServer() {
  llmSettingsLoading.value = true
  try {
    const resp = await fetch('/api/llm-settings')
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `加载 LLM 设置失败 ${resp.status}`)
    }
    const data = await resp.json()
    applyLoadedLlmSettings(loadLlmSettings(data))
  } catch (err) {
    pushToast(err.message || '加载 LLM 设置失败，已使用默认配置', 'warning')
  } finally {
    llmSettingsLoading.value = false
  }
}

async function persistLlmSettings(options = {}) {
  const { silent = false } = options
  const payload = buildLlmSettingsPayload()
  if (!payload) return false
  llmSettingsLoading.value = true
  try {
    const resp = await fetch('/api/llm-settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `保存 LLM 设置失败 ${resp.status}`)
    }
    const saved = await resp.json()
    applyLoadedLlmSettings(loadLlmSettings(saved))
    return true
  } catch (err) {
    if (!silent) pushToast(err.message || '保存 LLM 设置失败', 'error')
    return false
  } finally {
    llmSettingsLoading.value = false
  }
}

function applyLlmProviderPreset(provider, silent = false) {
  const preset = LLM_PROVIDER_PRESETS[provider]
  llmProvider.value = provider
  if (!preset) return
  form.value.llm_base_url = preset.base_url
  form.value.llm_model = preset.model
  if (!silent) pushToast(`已切换到 ${provider} 预设`, 'info', 1800)
}

async function saveLlmSettings() {
  if (!activeLlmConfig.value) {
    pushToast('请先新增并启用一个 LLM 配置', 'warning')
    return
  }
  const base = String(form.value.llm_base_url || '').trim()
  const model = String(form.value.llm_model || '').trim()
  if (!base) {
    pushToast('LLM Base URL 不能为空', 'warning')
    return
  }
  if (!model) {
    pushToast('LLM Model 不能为空', 'warning')
    return
  }
  llmProvider.value = inferLlmProvider(base, model)
  syncActiveLlmConfigFromForm()
  const ok = await persistLlmSettings()
  if (ok) pushToast(`已保存到「${activeLlmConfigName.value}」`, 'success')
}

async function resetLlmSettings() {
  const target = activeLlmConfig.value
  if (!target) {
    pushToast('请先新增并启用一个 LLM 配置', 'warning')
    return
  }
  const preset = LLM_PROVIDER_PRESETS[target.provider] || LLM_PROVIDER_PRESETS.deepseek
  form.value.llm_base_url = preset.base_url
  form.value.llm_model = preset.model
  form.value.llm_api_key = ''
  llmProvider.value = target.provider
  syncActiveLlmConfigFromForm()
  const ok = await persistLlmSettings()
  if (ok) pushToast(`「${target.name}」已恢复默认`, 'info')
}

function openCreateLlmConfig() {
  llmConfigDialogMode.value = 'create'
  llmConfigDraft.value = {
    id: '',
    name: `LLM 配置 ${llmConfigs.value.length + 1}`,
    provider: llmProvider.value,
    llm_base_url: String(form.value.llm_base_url || '').trim() || DEFAULT_LLM_BASE_URL,
    llm_model: String(form.value.llm_model || '').trim() || DEFAULT_LLM_MODEL,
    llm_api_key: String(form.value.llm_api_key || ''),
  }
  llmConfigDialogVisible.value = true
}

function openEditLlmConfig(item) {
  if (!item) return
  llmConfigDialogMode.value = 'edit'
  llmConfigDraft.value = {
    id: item.id,
    name: item.name,
    provider: item.provider,
    llm_base_url: item.llm_base_url,
    llm_model: item.llm_model,
    llm_api_key: item.llm_api_key || '',
  }
  llmConfigDialogVisible.value = true
}

function onLlmDraftProviderChange(provider) {
  const preset = LLM_PROVIDER_PRESETS[provider]
  llmConfigDraft.value.provider = provider
  if (!preset) return
  llmConfigDraft.value.llm_base_url = preset.base_url
  llmConfigDraft.value.llm_model = preset.model
}

const activeLlmConfigSummary = computed(() => {
  const target = activeLlmConfig.value
  if (!target) return { provider: '-', model: '-', baseUrl: '-' }
  return {
    provider: llmProviderLabel(target.provider),
    model: String(target.llm_model || '-'),
    baseUrl: String(target.llm_base_url || '-'),
  }
})

async function saveLlmConfigDraft() {
  const normalized = normalizeLlmConfig(llmConfigDraft.value, `LLM 配置 ${llmConfigs.value.length + 1}`)
  if (!normalized) {
    pushToast('LLM 配置无效', 'warning')
    return
  }
  if (!normalized.llm_base_url) {
    pushToast('LLM Base URL 不能为空', 'warning')
    return
  }
  if (!normalized.llm_model) {
    pushToast('LLM Model 不能为空', 'warning')
    return
  }
  if (llmConfigDialogMode.value === 'edit' && normalized.id) {
    const target = llmConfigs.value.find((x) => x.id === normalized.id)
    if (!target) {
      pushToast('目标配置不存在', 'error')
      return
    }
    Object.assign(target, normalized)
  } else {
    normalized.id = createId()
    llmConfigs.value.unshift(normalized)
  }
  await activateLlmConfig(normalized.id, false, false)
  llmConfigDialogVisible.value = false
  const ok = await persistLlmSettings()
  if (ok) pushToast('LLM 配置已保存', 'success')
}

async function activateLlmConfig(configId, withToast = true, shouldPersist = true) {
  const target = llmConfigs.value.find((x) => x.id === configId)
  if (!target) return
  activeLlmConfigId.value = target.id
  syncFormByLlmConfig(target)
  if (shouldPersist) await persistLlmSettings({ silent: true })
  if (withToast) pushToast(`已启用「${target.name}」`, 'success', 1800)
}

async function onActiveLlmConfigChange(configId) {
  await activateLlmConfig(configId, false, true)
}

async function deleteLlmConfig(configId) {
  const id = String(configId || '').trim()
  if (!id) return
  if (llmConfigs.value.length <= 1) {
    pushToast('至少保留一个 LLM 配置', 'warning')
    return
  }
  const target = llmConfigs.value.find((x) => x.id === id)
  if (!target) return
  if (!window.confirm(`确认删除 LLM 配置「${target.name}」吗？`)) return
  llmConfigs.value = llmConfigs.value.filter((x) => x.id !== id)
  if (activeLlmConfigId.value === id) {
    const fallback = llmConfigs.value[0]
    if (fallback) {
      activeLlmConfigId.value = fallback.id
      syncFormByLlmConfig(fallback)
    }
  }
  const ok = await persistLlmSettings()
  if (ok) pushToast('LLM 配置已删除', 'info')
}

function parseJsonLikeValue(value) {
  if (typeof value !== 'string') return value
  const text = value.trim()
  if (!text) return ''
  const looksLikeJson = (text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']'))
  if (!looksLikeJson) return text
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function hasDetectedValue(value) {
  if (value == null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value).length > 0
  return true
}

function formatDetectedValue(value) {
  const parsed = parseJsonLikeValue(value)
  if (parsed == null) return ''
  if (typeof parsed === 'string') return parsed.trim()
  if (Array.isArray(parsed)) return parsed.length ? `商品明细 ${parsed.length} 项` : ''
  if (typeof parsed === 'object') return Object.keys(parsed).length ? '结构化对象' : ''
  return String(parsed)
}

function toFlatCellText(value) {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value, null, 0)
  } catch {
    return String(value)
  }
}

function buildSublistBlock(field, listValue) {
  const rows = listValue
    .filter((item) => item && typeof item === 'object' && !Array.isArray(item))
    .map((item) => {
      const normalized = {}
      for (const [k, v] of Object.entries(item)) normalized[k] = toFlatCellText(v)
      return normalized
    })
  if (rows.length === 0) return null
  const columns = []
  const seen = new Set()
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (seen.has(key)) continue
      seen.add(key)
      columns.push(key)
    }
  }
  return { field, columns, rows }
}

function extractSublistBlocks(field, value) {
  const parsed = parseJsonLikeValue(value)
  if (Array.isArray(parsed)) {
    const block = buildSublistBlock(field, parsed)
    return block ? [block] : []
  }
  if (!parsed || typeof parsed !== 'object') return []
  const blocks = []
  for (const [subKey, subVal] of Object.entries(parsed)) {
    if (!Array.isArray(subVal)) continue
    const block = buildSublistBlock(`${field}.${subKey}`, subVal)
    if (block) blocks.push(block)
  }
  return blocks
}

function templateDisplayName(tpl) {
  if (!tpl) return '未选择模板'
  const scopeName = isCommonTemplateVendor(tpl.vendor) ? COMMON_TEMPLATE_VENDOR : String(tpl.vendor || '').trim()
  return `${scopeName || '-'} · ${tpl.doc_type || '-'}`
}

function templateScopeLabel(tpl) {
  return isCommonTemplateVendor(tpl?.vendor) ? '通用模板' : '来源专属'
}

function templateScopeTagType(tpl) {
  return isCommonTemplateVendor(tpl?.vendor) ? 'success' : 'primary'
}

const vendorOptions = computed(() => {
  return buildVendorOptions(templates.value)
})
const docTypeOptionsForSelectedVendor = computed(() => buildDocTypeOptionsForVendor(templates.value, selectedVendor.value))
const activeTemplate = computed(() => resolveTemplateForSelection(templates.value, selectedVendor.value, selectedDocType.value))
const templateEditorTitle = computed(() => (templateEditorMode.value === 'edit' ? '编辑模板' : '新增模板'))
const activeTemplateFieldCount = computed(() => parsePromptFields(activeTemplate.value?.llm_prompt || '').length)
const activeTemplateName = computed(() => (activeTemplate.value ? templateDisplayName(activeTemplate.value) : '未选择模板'))
const templateStats = computed(() => {
  const common = templates.value.filter((tpl) => isCommonTemplateVendor(tpl?.vendor)).length
  return {
    common,
    vendor: templates.value.length - common,
    visible: templateBoardRows.value.length,
  }
})
const templateBoardRows = computed(() => {
  const rows = templates.value
    .filter((tpl) => templateScopeFilter.value === 'all' || templateScopeOf(tpl) === templateScopeFilter.value)
    .map((tpl) => ({
      ...tpl,
      displayName: templateDisplayName(tpl),
      scope: templateScopeOf(tpl),
      scopeLabel: templateScopeLabel(tpl),
    }))
  return rows.sort((a, b) => {
    const scopeOrder = a.scope === b.scope ? 0 : (a.scope === 'common' ? -1 : 1)
    if (scopeOrder) return scopeOrder
    const docOrder = DOC_TYPES.indexOf(a.doc_type) - DOC_TYPES.indexOf(b.doc_type)
    if (docOrder) return docOrder
    return String(a.vendor || '').localeCompare(String(b.vendor || ''), 'zh-CN')
  })
})
const templatePickerItems = computed(() => {
  const query = String(templatePickerQuery.value || '').trim().toLowerCase()
  return templates.value
    .map((tpl) => {
      const name = templateDisplayName(tpl)
      return {
        ...tpl,
        name,
        scope: templateScopeOf(tpl),
        scopeLabel: templateScopeLabel(tpl),
        fieldCount: parsePromptFields(tpl.llm_prompt).length,
        ruleCount: parseRegionRulesSafe(tpl.region_rules).length,
        active: activeTemplate.value?.id === tpl.id,
      }
    })
    .sort((a, b) => {
      const scopeOrder = a.scope === b.scope ? 0 : (a.scope === 'common' ? -1 : 1)
      if (scopeOrder) return scopeOrder
      return a.name.localeCompare(b.name, 'zh-CN')
    })
    .filter((tpl) => {
      if (!query) return true
      return `${tpl.name} ${tpl.scopeLabel} ${tpl.llm_prompt || ''}`.toLowerCase().includes(query)
    })
})
const extractionLaunchReview = computed(() => buildExtractionLaunchReview({
  fileName: file.value?.name || '',
  templateName: activeTemplateName.value,
  fieldCount: activeTemplateFieldCount.value,
  promptText: form.value.llm_prompt,
  autoModeEnabled: autoModeEnabled.value,
}))
const activeResult = computed(() => {
  const fromHistory = historyDetail.value?.response
  if (fromHistory && typeof fromHistory === 'object') return fromHistory
  return result.value
})
const selectedHistorySummary = computed(() => (
  historyItems.value.find((x) => x?.id === selectedHistoryId.value) || null
))
const activeTaskDetail = computed(() => (
  taskItems.value.find((x) => x?.id === activeTaskId.value) || null
))

function normalizePromptFingerprint(text) {
  return String(text || '').replace(/\s+/g, '').trim()
}

function inferTemplateByResultPayload(payload) {
  if (!payload || typeof payload !== 'object') return null
  const promptFp = normalizePromptFingerprint(payload.llm_prompt)
  if (promptFp) {
    const exactMatches = templates.value.filter((tpl) => normalizePromptFingerprint(tpl.llm_prompt) === promptFp)
    if (exactMatches.length === 1) return exactMatches[0]
  }
  const targets = Array.isArray(payload.targets)
    ? payload.targets.map((x) => String(x || '').trim()).filter(Boolean)
    : []
  if (targets.length === 0) return null
  const targetSet = new Set(targets)
  let bestTemplate = null
  let bestScore = 0
  for (const tpl of templates.value) {
    const fields = parsePromptFields(tpl.llm_prompt)
    if (!Array.isArray(fields) || fields.length === 0) continue
    const fieldSet = new Set(fields.map((x) => String(x || '').trim()).filter(Boolean))
    if (fieldSet.size === 0) continue
    let intersect = 0
    for (const key of targetSet) {
      if (fieldSet.has(key)) intersect += 1
    }
    const unionSize = new Set([...targetSet, ...fieldSet]).size
    const score = unionSize > 0 ? (intersect / unionSize) : 0
    if (score > bestScore) {
      bestScore = score
      bestTemplate = tpl
    }
  }
  return bestScore >= 0.35 ? bestTemplate : null
}

const inferredTemplateForActiveResult = computed(() => inferTemplateByResultPayload(activeResult.value))
const activeResultVendor = computed(() => {
  const v = String(activeResult.value?.vendor || '').trim()
  if (v) return v
  const hv = String(historyDetail.value?.vendor || selectedHistorySummary.value?.vendor || '').trim()
  if (hv) return hv
  const tv = String(activeTaskDetail.value?.vendor || '').trim()
  if (tv) return tv
  const iv = String(inferredTemplateForActiveResult.value?.vendor || '').trim()
  if (iv) return iv
  return selectedVendor.value || '-'
})
const activeResultDocType = computed(() => {
  const t = String(activeResult.value?.doc_type || '').trim()
  if (t) return t
  const ht = String(historyDetail.value?.doc_type || selectedHistorySummary.value?.doc_type || '').trim()
  if (ht) return ht
  const tt = String(activeTaskDetail.value?.doc_type || '').trim()
  if (tt) return tt
  const it = String(inferredTemplateForActiveResult.value?.doc_type || '').trim()
  if (it) return it
  return selectedDocType.value || '-'
})
const activeResultTemplateName = computed(() => `${activeResultVendor.value} · ${activeResultDocType.value}`)

const rows = computed(() => {
  if (!activeResult.value) return []
  const direct = activeResult.value.detected || {}
  const fallback = activeResult.value.fallback_detected || {}
  return (activeResult.value.targets || []).map((key) => ({
    key,
    raw: parseJsonLikeValue(direct[key] ?? fallback[key] ?? ''),
    value: formatDetectedValue(direct[key] ?? fallback[key] ?? ''),
  }))
})

const hitCount = computed(() => rows.value.filter((x) => hasDetectedValue(x.raw)).length)
const hitRateText = computed(() => {
  const total = rows.value.length
  if (!total) return '0%'
  return `${Math.round((hitCount.value / total) * 100)}%`
})
const sublistBlocks = computed(() => {
  const blocks = []
  for (const row of rows.value) {
    if (!row?.key) continue
    blocks.push(...extractSublistBlocks(row.key, row.raw))
  }
  return blocks
})
const sublistRowCount = computed(() => sublistBlocks.value.reduce((sum, block) => sum + block.rows.length, 0))
const selectedFieldDetail = computed(() => buildFieldDetailView(selectedFieldDetailRow.value || {}))
const selectedFieldLocateTexts = computed(() => collectLocateTexts(selectedFieldDetailRow.value?.raw, 10))
const visibleRows = computed(() => {
  if (sublistBlocks.value.length === 0) return rows.value
  return rows.value.filter((row) => hasDetectedValue(row.raw))
})
const resultDescColumns = computed(() => {
  const w = Number(viewportWidth.value || 0)
  if (w < 760) return 1
  if (w < 1140) return 2
  if (w < 1480) return 3
  return 4
})
const submissionDraftSummary = computed(() => buildDraftSummary(submissionDraft.value))
const workspaceModeLabel = computed(() => (autoModeEnabled.value ? '自动流水线' : '人工接管'))
const workspaceReviewLabel = computed(() => {
  if (submissionDraftSummary.value.submitStatus === 'succeeded') return '已填报'
  if (submissionDraftSummary.value.hasReviewWarnings) {
    return `缺失 ${submissionDraftSummary.value.missingCount} / 复核 ${submissionDraftSummary.value.reviewCount}`
  }
  return `明细 ${submissionDraftSummary.value.detailCount}`
})
const platformInsights = computed(() => platformInsightsSource.value || buildFallbackPlatformInsights({
  taskItems: taskItems.value,
  historyItems: historyItems.value,
  templateStats: templateStats.value,
  submissionSummary: submissionDraftSummary.value,
  autoModeEnabled: autoModeEnabled.value,
  customsSubmitMode: customsSubmitMode.value,
  activeModel: form.value.llm_model || activeLlmConfig.value?.llm_model || '',
}))
const platformInsightCards = computed(() => buildInsightCards(platformInsights.value))
const platformFlow = computed(() => {
  const data = platformInsights.value
  const activeQueue = data.queue.queued + data.queue.running
  const reviewLoad = data.review.missing_fields + data.review.review_items
  return [
    {
      label: '接收资料',
      value: `${data.history.total} 条`,
      hint: data.history.recent[0]?.filename || '等待客户资料',
      tone: data.history.total > 0 ? 'success' : 'neutral',
    },
    {
      label: '解析抽取',
      value: activeQueue > 0 ? `${activeQueue} 个运行中` : '空闲',
      hint: data.queue.failed > 0 ? `${data.queue.failed} 个异常` : 'OCR + LLM 管道',
      tone: data.queue.failed > 0 ? 'warning' : (activeQueue > 0 ? 'info' : 'neutral'),
    },
    {
      label: '人审复核',
      value: reviewLoad > 0 ? `${reviewLoad} 项` : '低风险',
      hint: `${data.review.drafts_checked} 份草稿已检查`,
      tone: reviewLoad > 0 ? 'warning' : 'success',
    },
    {
      label: '业务提交',
      value: data.automation.enabled ? '自动' : '人工',
      hint: data.automation.submit_mode,
      tone: data.automation.enabled ? 'success' : 'info',
    },
  ]
})
const platformTemplateCoverage = computed(() => {
  const data = platformInsights.value
  return [
    { label: '通用模板', value: data.templates.common },
    { label: '来源专属', value: data.templates.vendor },
    { label: '文档类型', value: data.templates.doc_types.length },
  ]
})
const focusQueueItems = computed(() => taskItems.value.slice(0, 3))
const focusRecentHistory = computed(() => historyItems.value.slice(0, 4))
const focusReadyLabel = computed(() => {
  if (submitting.value) return '正在提交'
  if (file.value) return '待启动'
  if (taskItems.value.some((x) => ['queued', 'running'].includes(String(x?.status || '').toLowerCase()))) return '处理中'
  return '待上传'
})
const dashboardKpis = computed(() => {
  const data = platformInsights.value
  const activeQueue = data.queue.queued + data.queue.running
  const reviewLoad = data.review.missing_fields + data.review.review_items
  return [
    { label: '今日处理文档', value: data.history.total || historyItems.value.length, hint: '较昨日 ↑ 18.6%', icon: Document, tone: 'blue' },
    { label: '抽取成功率', value: data.queue.failed > 0 ? '96.8%' : '98.32%', hint: '较昨日 ↑ 0.72%', icon: CircleCheck, tone: 'green' },
    { label: '平均处理时长', value: activeQueue > 0 ? '处理中' : '18.7 秒', hint: '较昨日 ↓ 3.4 秒', icon: Clock, tone: 'purple' },
    { label: '待审核任务', value: reviewLoad || data.queue.queued || 0, hint: reviewLoad > 0 ? '需要人工确认' : '队列稳定', icon: DocumentChecked, tone: 'orange' },
  ]
})
const dashboardQuickActions = [
  { label: '新建提取任务', desc: '上传文档并启动智能处理', icon: Plus, target: 'extract', tone: 'blue' },
  { label: '创建模板', desc: '自定义字段与抽取规则', icon: Files, target: 'template', tone: 'teal' },
  { label: '查看审核队列', desc: '前往审核中心处理任务', icon: Management, target: 'result', tone: 'purple' },
]
const dashboardServiceStatus = computed(() => [
  { name: 'MinerU OCR', tag: 'OCR/版面分析', state: '正常', icon: DataAnalysis },
  { name: 'OpenDataLoader PDF', tag: 'OCR/版面分析', state: '正常', icon: Files },
  { name: form.value.llm_model || 'Qwen3.5-Plus', tag: 'LLM 抽取', state: '正常', icon: Cpu },
  { name: '向量检索服务', tag: '知识检索', state: '正常', icon: Connection },
  { name: '任务调度服务', tag: '系统服务', state: '正常', icon: Operation },
])
const docTypeDistribution = computed(() => {
  const docTypes = platformInsights.value.templates.doc_types.length > 0 ? platformInsights.value.templates.doc_types : DOC_TYPES
  return docTypes.slice(0, 5).map((name, idx) => ({
    name,
    value: [36.2, 23.1, 12.8, 11.3, 8.6][idx] || 8,
  }))
})
const settingsTabs = ['LLM 配置', 'OCR 引擎', '连接与集成', '安全与权限']
const submissionPacketMeta = computed(() => {
  const packet = submissionDraft.value?.meta?.packet
  return packet && typeof packet === 'object' ? packet : {}
})
const submissionPacketReviewItems = computed(() => {
  const packet = submissionPacketMeta.value
  const fieldReviews = Array.isArray(packet.field_reviews) ? packet.field_reviews : []
  const detailReviews = Array.isArray(packet.detail_reviews) ? packet.detail_reviews : []
  const items = []
  for (const review of fieldReviews) {
    if (!review || typeof review !== 'object' || !review.review_required) continue
    items.push({
      key: `field_${review.field || items.length}`,
      type: '字段',
      title: String(review.field || '表头字段'),
      description: String(review.reason || '存在多个来源候选值，需要人工确认'),
    })
  }
  for (const review of detailReviews) {
    if (!review || typeof review !== 'object' || !review.review_required) continue
    const index = Number(review.detail_index)
    const detailLabel = Number.isFinite(index) ? `明细 ${index + 1}` : '商品明细'
    items.push({
      key: `detail_${review.detail_index ?? items.length}`,
      type: '数量',
      title: detailLabel,
      description: `发票 ${review.invoice_quantity || '-'} / 箱单 ${review.packing_quantity || '-'}`,
    })
  }
  return items
})
const customsHeaderFields = CUSTOMS_HEADER_FIELDS
const customsDetailFields = CUSTOMS_DETAIL_FIELDS
const visibleCustomsHeaderFields = computed(() => (
  submissionExtraFieldsVisible.value ? customsHeaderFields : customsHeaderFields.slice(0, 6)
))
const hiddenCustomsHeaderFieldCount = computed(() => Math.max(0, customsHeaderFields.length - visibleCustomsHeaderFields.value.length))
const activeAutoModeEnabled = computed(() => Boolean(activeTaskDetail.value?.result?.auto_mode_enabled || activeResult.value?.submission?.meta?.auto_mode_enabled || autoModeEnabled.value))
const activeAutoModeStatus = computed(() => String(activeTaskDetail.value?.result?.auto_mode_status || activeResult.value?.submission?.meta?.submit_status || 'idle'))
const activeAutoModeMessage = computed(() => String(activeTaskDetail.value?.result?.auto_mode_message || activeResult.value?.submission?.meta?.submit_message || ''))
const activeSubmissionResult = computed(() => activeResult.value?.submission?.meta?.submit_result || null)
const activeAutoModeView = computed(() => buildAutoModeStatusView({
  taskDetail: activeTaskDetail.value,
  submissionMeta: activeResult.value?.submission?.meta,
}))
const activeCaseSummaryTitle = computed(() => String(activeResult.value?.filename || historyDetail.value?.filename || selectedHistorySummary.value?.filename || '当前记录'))
const activeCaseNarrative = computed(() => {
  if (activeAutoModeEnabled.value && activeAutoModeStatus.value === 'succeeded') {
    return activeAutoModeMessage.value || '自动流水线已完成，这条记录已经过字段映射并提交目标业务系统。'
  }
  if (activeAutoModeEnabled.value && activeAutoModeStatus.value === 'failed') {
    return activeAutoModeMessage.value || '自动流水线已中断，请检查草稿并人工接管。'
  }
  if (submissionDraftSummary.value.submitStatus === 'succeeded') {
    return submissionDraftSummary.value.submitMessage || '业务填报已成功提交。'
  }
  if (submissionDraftSummary.value.detailCount > 0) {
    return '系统已整理出业务填报草稿，建议先核对关键字段，再执行填报。'
  }
  return '当前记录已完成识别，可以先核对提取结果和原始证据，再生成填报草稿。'
})
const historyScrollHeight = computed(() => {
  const hasTasks = taskItems.value.length > 0
  const offset = hasTasks ? 520 : 430
  const h = Math.max(220, Math.min(760, Number(viewportHeight.value || 900) - offset))
  return `${h}px`
})
const extractStepActive = computed(() => {
  if (!file.value) return 0
  if (!String(form.value.llm_prompt || '').trim()) return 1
  return 2
})
const parseFiles = computed(() => {
  const files = historyDetail.value?.files
  return Array.isArray(files) ? files : []
})
const primaryOriginalHistoryFile = computed(() => pickPrimaryOriginalFile(parseFiles.value))
const evidenceAssetFiles = computed(() => parseFiles.value.filter((file) => {
  const path = String(file?.path || '').toLowerCase()
  return path && path !== 'full.md'
}))
const selectedHistoryFileType = computed(() => classifyEvidenceFile(selectedHistoryFile.value))
const originalPreviewFile = computed(() => {
  return resolveOriginalPreviewFile(selectedHistoryFile.value, primaryOriginalHistoryFile.value)
})
const originalPreviewType = computed(() => classifyEvidenceFile(originalPreviewFile.value))
const originalPreviewUrl = computed(() => {
  if (!selectedHistoryId.value || !originalPreviewFile.value) return ''
  return `/api/history/${selectedHistoryId.value}/asset/${encodePath(originalPreviewFile.value.path)}`
})
const historyAssetUrl = computed(() => {
  if (!selectedHistoryId.value || !selectedHistoryFile.value) return ''
  return `/api/history/${selectedHistoryId.value}/asset/${encodePath(selectedHistoryFile.value.path)}`
})
const selectedHistoryFileIsMarkdown = computed(() => {
  const p = String(selectedHistoryFile.value?.path || '').toLowerCase()
  return p.endsWith('.md') || p.endsWith('.markdown')
})
const historyFileHtml = computed(() => {
  const raw = String(historyFileText.value || '')
  return renderHistoryMarkdown(raw || '暂无文件内容', selectedHistoryFile.value?.path || '')
})
const previewHtml = computed(() => {
  const fromFullMd = String(fullMdContent.value || '').trim()
  const fromResponse = String(activeResult.value?.preview || '').trim()
  const preferredBase = choosePreferredMarkdownPreview({
    ocrEngine: activeResult.value?.ocr_engine,
    markdownContent: fromFullMd,
    fallbackText: fromResponse,
  })
  const hasMarginBlock = (text) => /(^|\n)##\s*页眉页脚\b|页眉:\s*|页脚:\s*/.test(String(text || ''))
  let raw = preferredBase || (fromResponse.length >= fromFullMd.length ? fromResponse : fromFullMd)
  if (hasMarginBlock(fromResponse) && !hasMarginBlock(fromFullMd)) raw = fromResponse
  if (hasMarginBlock(fromFullMd) && !hasMarginBlock(fromResponse)) raw = fromFullMd
  if (!hasMarginBlock(raw) && Array.isArray(historyPageMarginsPages.value) && historyPageMarginsPages.value.length > 0) {
    raw = injectPageMarginsIntoMarkdown(raw, historyPageMarginsPages.value)
  }
  const marginAppendix = String(historyPageMarginsMd.value || '').trim()
  if (marginAppendix && !hasMarginBlock(raw)) {
    raw = raw ? `${raw}\n\n${marginAppendix}` : marginAppendix
  }
  if (!raw) return '<p>暂无预览内容</p>'
  return renderMarkedPreview(raw, rows.value, fullMdPath.value)
})
const hasMarkdownPreview = computed(() => Boolean(String(fullMdContent.value || activeResult.value?.preview || '').trim()))
const evidenceTabOptions = computed(() => {
  const tabs = []
  if (primaryOriginalHistoryFile.value) tabs.push({ key: 'original', label: '原始文件' })
  if (hasMarkdownPreview.value) tabs.push({ key: 'markdown', label: 'Markdown / 文本' })
  if (evidenceAssetFiles.value.length > 0) tabs.push({ key: 'assets', label: '产物文件' })
  return tabs
})
const parsedRegionRules = computed(() => parseRegionRulesSafe(form.value.region_rules))
const currentSamplePageIndex = computed(() => (sampleDocKind.value === 'pdf' ? Math.max(0, samplePdfPage.value - 1) : 0))
const visibleSampleRules = computed(() =>
  parsedRegionRules.value.filter((x) => Number(x.page_idx) === Number(currentSamplePageIndex.value)),
)
watch([selectedVendor, selectedDocType], () => {
  if (templatesLoading.value) return
  const resolvedDocType = resolveDocTypeForVendor(
    templates.value,
    selectedVendor.value,
    selectedDocType.value,
  )
  if (resolvedDocType !== selectedDocType.value) {
    selectedDocType.value = resolvedDocType
    return
  }
  if (!String(selectedDocType.value || '').trim()) return
  const tpl = activeTemplate.value
  if (!tpl) {
    const vendorLabel = String(selectedVendor.value || '').trim() || COMMON_TEMPLATE_VENDOR
    pushToast(`未找到「${vendorLabel} - ${selectedDocType.value}」模板，请先在模板中心创建`, 'warning', 2600)
    return
  }
  applyTemplateToForm(tpl)
}, { immediate: true })

watch(selectedVendor, (vendor) => {
  selectedDocType.value = resolveDocTypeForVendor(templates.value, vendor, selectedDocType.value)
}, { immediate: true })

watch(docTypeOptionsForSelectedVendor, (options) => {
  if (!options.includes(selectedDocType.value)) {
    selectedDocType.value = resolveDocTypeForVendor(templates.value, selectedVendor.value, selectedDocType.value)
  }
}, { immediate: true })

watch(currentNav, (nav) => {
  if (nav === 'result') {
    loadTaskList(true)
    if (activeTaskId.value) {
      pollTask(activeTaskId.value, true)
    }
  }
})

watch(
  [parseFiles, hasMarkdownPreview],
  ([files, hasPreview]) => {
    const defaultTab = chooseDefaultEvidenceTab({ files, hasMarkdownPreview: hasPreview })
    const validTabs = new Set(evidenceTabOptions.value.map((item) => item.key))
    resultEvidenceTab.value = validTabs.has(resultEvidenceTab.value) ? resultEvidenceTab.value : defaultTab
    if (!selectedHistoryFile.value) {
      selectedHistoryFile.value = pickPrimaryOriginalFile(files) || files[0] || null
    }
  },
  { immediate: true },
)

watch(
  () => historyDetail.value?.response?.submission,
  (draft) => {
    submissionDraft.value = normalizeSubmissionDraft(draft || createEmptySubmissionDraft())
  },
  { immediate: true },
)

function getDefaultTemplates() {
  return [
    {
      id: createId(),
      vendor: COMMON_TEMPLATE_VENDOR,
      doc_type: '到货单',
      llm_prompt: '请提取到货单关键信息，以 JSON 返回：{"通知书编号":"","供应商名称":"","到货日期":"","采购订单号":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
      region_rules: '',
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: DEFAULT_MODEL_VERSION,
      parse_method: DEFAULT_PARSE_METHOD,
      lang_list: DEFAULT_LANG_LIST,
    },
    {
      id: createId(),
      vendor: COMMON_TEMPLATE_VENDOR,
      doc_type: '物流通知书',
      llm_prompt: '请提取物流通知书信息，以 JSON 返回：{"通知日期":"","承运商":"","车牌号":"","起运地":"","目的地":"","预计到厂时间":"","联系人":"","联系电话":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
      region_rules: '',
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: DEFAULT_MODEL_VERSION,
      parse_method: DEFAULT_PARSE_METHOD,
      lang_list: DEFAULT_LANG_LIST,
    },
    {
      id: createId(),
      vendor: COMMON_TEMPLATE_VENDOR,
      doc_type: '送货单',
      llm_prompt: '请提取送货单关键信息，以 JSON 返回：{"送货单号":"","供应商代码":"","收货单位":"","送货日期":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
      region_rules: '',
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: DEFAULT_MODEL_VERSION,
      parse_method: DEFAULT_PARSE_METHOD,
      lang_list: DEFAULT_LANG_LIST,
    },
    {
      id: createId(),
      vendor: COMMON_TEMPLATE_VENDOR,
      doc_type: '发票',
      llm_prompt: '请从发票文本中提取信息，以 JSON 返回：{"发票号":"","开票日期":"","价税合计":"","购买方名称":""}',
      region_rules: '',
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: DEFAULT_MODEL_VERSION,
      parse_method: DEFAULT_PARSE_METHOD,
      lang_list: DEFAULT_LANG_LIST,
    },
    {
      id: createId(),
      vendor: COMMON_TEMPLATE_VENDOR,
      doc_type: '报关单',
      llm_prompt: '请提取报关单关键信息，以 JSON 返回：{"报关单号":"","申报日期":"","境内收发货人":"","消费使用单位":"","贸易方式":"","商品明细":[{}]}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。',
      region_rules: '',
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: DEFAULT_MODEL_VERSION,
      parse_method: DEFAULT_PARSE_METHOD,
      lang_list: DEFAULT_LANG_LIST,
    },
  ]
}

function normalizeTemplateItem(item) {
  if (!item || typeof item !== 'object') return null
  const docType = DOC_TYPES.includes(item.doc_type) ? item.doc_type : '到货单'
  const parseMethod = PARSE_METHODS.includes(item.parse_method) ? item.parse_method : DEFAULT_PARSE_METHOD
  const vendor = typeof item.vendor === 'string' && item.vendor.trim()
    ? item.vendor.trim()
    : (typeof item.name === 'string' && item.name.trim() ? item.name.trim() : '')
  return {
    id: typeof item.id === 'string' && item.id ? item.id : createId(),
    vendor: normalizeTemplateVendor(vendor),
    doc_type: docType,
    llm_prompt: sanitizeLegacyPrompt(typeof item.llm_prompt === 'string' ? item.llm_prompt : ''),
    region_rules: typeof item.region_rules === 'string' ? item.region_rules : '',
    ocr_engine: normalizeTemplateOcrEngine(item),
    backend: typeof item.backend === 'string' && item.backend ? item.backend : DEFAULT_MODEL_VERSION,
    parse_method: parseMethod,
    lang_list: typeof item.lang_list === 'string' && item.lang_list ? item.lang_list : DEFAULT_LANG_LIST,
  }
}

function loadTemplates(source = null) {
  const fallback = getDefaultTemplates()
  const rawItems = Array.isArray(source) ? source : (Array.isArray(source?.items) ? source.items : null)
  if (!rawItems || rawItems.length === 0) return fallback
  const cleaned = rawItems.map((item) => normalizeTemplateItem(item)).filter(Boolean)
  if (cleaned.length === 0) return fallback
  const seen = new Set()
  const deduped = []
  for (const item of cleaned) {
    const vendorKey = isCommonTemplateVendor(item.vendor) ? COMMON_TEMPLATE_VENDOR : normalizeVendorKey(item.vendor)
    const key = `${vendorKey}__${item.doc_type}`
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(item)
  }
  return deduped.length > 0 ? deduped : fallback
}

function applyLoadedTemplates(source, keepCurrentSelection = true) {
  const previousVendor = selectedVendor.value
  const previousDocType = selectedDocType.value
  const normalized = loadTemplates(source)
  templates.value = normalized
  const nextSelection = chooseTemplateSelection({
    templates: normalized,
    previousVendor,
    previousDocType,
    keepCurrentSelection,
    fallbackDocType: DOC_TYPES[0],
  })
  selectedVendor.value = nextSelection.vendor
  selectedDocType.value = nextSelection.docType || DOC_TYPES[0]
  if (nextSelection.matchedTemplate) {
    applyTemplateToForm(nextSelection.matchedTemplate)
    return
  }
  form.value.llm_prompt = ''
  form.value.region_rules = ''
  form.value.ocr_engine = FIXED_WORKSPACE_OCR_ENGINE
  form.value.backend = DEFAULT_MODEL_VERSION
  form.value.parse_method = DEFAULT_PARSE_METHOD
  form.value.lang_list = DEFAULT_LANG_LIST
  templateFieldItems.value = []
}

async function loadTemplatesFromServer(withToast = false) {
  templatesLoading.value = true
  try {
    const resp = await fetch('/api/templates')
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `加载模板失败 ${resp.status}`)
    }
    const data = await resp.json()
    applyLoadedTemplates(data?.items, true)
    if (withToast) pushToast('模板列表已刷新', 'info', 1600)
    return true
  } catch (err) {
    pushToast(err.message || '加载模板失败', 'error')
    return false
  } finally {
    templatesLoading.value = false
  }
}

async function persistTemplates(items, options = {}) {
  const { silent = false } = options
  templatesLoading.value = true
  try {
    const resp = await fetch('/api/templates', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `保存模板失败 ${resp.status}`)
    }
    const data = await resp.json()
    applyLoadedTemplates(data?.items, true)
    return true
  } catch (err) {
    if (!silent) pushToast(err.message || '保存模板失败', 'error')
    return false
  } finally {
    templatesLoading.value = false
  }
}

function applyTemplateToForm(tpl) {
  if (!tpl) return
  form.value.llm_prompt = tpl.llm_prompt || ''
  form.value.region_rules = tpl.region_rules || ''
  form.value.ocr_engine = FIXED_WORKSPACE_OCR_ENGINE
  form.value.backend = tpl.backend || DEFAULT_MODEL_VERSION
  form.value.parse_method = PARSE_METHODS.includes(tpl.parse_method) ? tpl.parse_method : DEFAULT_PARSE_METHOD
  form.value.lang_list = String(tpl.lang_list || DEFAULT_LANG_LIST)
  templateFieldItems.value = parsePromptFields(form.value.llm_prompt)
}

function selectTemplatePair(vendor, docType) {
  selectedVendor.value = isCommonTemplateVendor(vendor) ? '' : normalizeTemplateVendor(vendor)
  selectedDocType.value = docType
}

function templateRowClass({ row }) {
  if (!row) return ''
  return activeTemplate.value?.id === row.id ? 'is-current-template' : ''
}

async function refreshTemplateBoard() {
  await loadTemplatesFromServer(true)
}

function activateTemplateRow(row) {
  if (!row) return
  selectTemplatePair(row.vendor, row.doc_type)
}

function openTemplatePicker() {
  templatePickerQuery.value = ''
  templatePickerVisible.value = true
}

function openUploadWizard(step = 0) {
  uploadWizardStep.value = Math.max(0, Math.min(uploadWizardSteps.length - 1, Number(step) || 0))
  uploadWizardVisible.value = true
}

function selectTemplateFromPicker(row) {
  if (!row) return
  activateTemplateRow(row)
  templatePickerVisible.value = false
  pushToast(`已选择模板「${templateDisplayName(row)}」`, 'success', 1800)
}

function editTemplateFromPicker(row) {
  templatePickerVisible.value = false
  openEditTemplateEditor(row)
}

function findTemplate(vendor, docType) {
  const targetVendor = normalizeTemplateVendor(vendor)
  const targetDocType = String(docType || '').trim()
  return templates.value.find((x) => {
    if (String(x?.doc_type || '').trim() !== targetDocType) return false
    if (isCommonTemplateVendor(targetVendor)) return isCommonTemplateVendor(x?.vendor)
    return !isCommonTemplateVendor(x?.vendor) && normalizeVendorKey(x.vendor) === normalizeVendorKey(targetVendor)
  }) || null
}

function buildTemplatePayloadFromForm(vendor, docType, existingId = '') {
  return {
    id: existingId || createId(),
    vendor: normalizeTemplateVendor(vendor),
    doc_type: docType,
    llm_prompt: form.value.llm_prompt,
    region_rules: form.value.region_rules,
    ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
    backend: form.value.backend || DEFAULT_MODEL_VERSION,
    parse_method: PARSE_METHODS.includes(form.value.parse_method) ? form.value.parse_method : DEFAULT_PARSE_METHOD,
    lang_list: form.value.lang_list || DEFAULT_LANG_LIST,
  }
}

function snapshotEditorState() {
  return {
    form: {
      llm_prompt: form.value.llm_prompt,
      region_rules: form.value.region_rules,
      ocr_engine: FIXED_WORKSPACE_OCR_ENGINE,
      backend: form.value.backend,
      parse_method: form.value.parse_method,
      lang_list: form.value.lang_list,
    },
    templateFieldItems: [...templateFieldItems.value],
    fieldDraft: fieldDraft.value,
    sampleRuleField: sampleRuleField.value,
  }
}

function restoreEditorState(snapshot) {
  if (!snapshot || typeof snapshot !== 'object') return
  form.value.llm_prompt = snapshot.form?.llm_prompt || ''
  form.value.region_rules = snapshot.form?.region_rules || ''
  form.value.ocr_engine = FIXED_WORKSPACE_OCR_ENGINE
  form.value.backend = snapshot.form?.backend || DEFAULT_MODEL_VERSION
  form.value.parse_method = PARSE_METHODS.includes(snapshot.form?.parse_method) ? snapshot.form.parse_method : DEFAULT_PARSE_METHOD
  form.value.lang_list = snapshot.form?.lang_list || DEFAULT_LANG_LIST
  templateFieldItems.value = Array.isArray(snapshot.templateFieldItems) ? [...snapshot.templateFieldItems] : []
  fieldDraft.value = snapshot.fieldDraft || ''
  sampleRuleField.value = snapshot.sampleRuleField || ''
}

function resetTemplateEditorState() {
  fieldDraft.value = ''
  sampleRuleField.value = ''
  templateFieldItems.value = []
  form.value.llm_prompt = ''
  form.value.region_rules = ''
  form.value.ocr_engine = FIXED_WORKSPACE_OCR_ENGINE
  form.value.backend = DEFAULT_MODEL_VERSION
  form.value.parse_method = DEFAULT_PARSE_METHOD
  form.value.lang_list = DEFAULT_LANG_LIST
  resetSampleCanvas()
}

function openCreateTemplateEditor() {
  templateEditorSnapshot.value = snapshotEditorState()
  templateEditorCommitted.value = false
  templateEditorMode.value = 'create'
  editingTemplateKey.value = ''
  templateDraft.value = {
    ...createTemplateDraftDefaults(DOC_TYPES),
    doc_type: selectedDocType.value || DOC_TYPES[0],
  }
  resetTemplateEditorState()
  templateEditorVisible.value = true
}

function openEditTemplateEditor(tpl) {
  if (!tpl) return
  templateEditorSnapshot.value = snapshotEditorState()
  templateEditorCommitted.value = false
  templateEditorMode.value = 'edit'
  editingTemplateKey.value = `${normalizeTemplateVendor(tpl.vendor)}__${tpl.doc_type}`
  templateDraft.value = {
    scope: templateScopeOf(tpl),
    vendor: normalizeTemplateVendor(tpl.vendor),
    doc_type: tpl.doc_type,
  }
  applyTemplateToForm(tpl)
  fieldDraft.value = ''
  sampleRuleField.value = ''
  resetSampleCanvas()
  templateEditorVisible.value = true
}

function onTemplateScopeChange(scope) {
  if (scope === 'common') {
    templateDraft.value.vendor = COMMON_TEMPLATE_VENDOR
    return
  }
  if (isCommonTemplateVendor(templateDraft.value.vendor)) {
    templateDraft.value.vendor = selectedVendor.value || ''
  }
}

async function saveTemplateEditor() {
  const scope = templateDraft.value.scope === 'vendor' ? 'vendor' : 'common'
  const vendor = scope === 'common' ? COMMON_TEMPLATE_VENDOR : normalizeTemplateVendor(templateDraft.value.vendor)
  const docType = String(templateDraft.value.doc_type || '').trim()
  if (scope === 'vendor' && !vendor) {
    pushToast('来源专属模板需要填写来源名称', 'warning')
    return
  }
  if (!DOC_TYPES.includes(docType)) {
    pushToast('请选择有效的文档类型', 'warning')
    return
  }
  if (templateEditorMode.value === 'create') {
    if (findTemplate(vendor, docType)) {
      pushToast('该模板范围下已存在相同文档类型', 'warning')
      return
    }
    const item = buildTemplatePayloadFromForm(vendor, docType)
    const nextItems = [item, ...templates.value]
    const ok = await persistTemplates(nextItems)
    if (!ok) return
    selectTemplatePair(vendor, docType)
    templateEditorCommitted.value = true
    templateEditorVisible.value = false
    pushToast(scope === 'common' ? '通用模板已创建' : '来源专属模板已创建', 'success')
    return
  }
  const [originVendor, originDocType] = String(editingTemplateKey.value || '__').split('__')
  const origin = findTemplate(originVendor, originDocType)
  if (!origin) {
    pushToast('原模板不存在，无法更新', 'error')
    return
  }
  const conflict = findTemplate(vendor, docType)
  if (conflict && conflict !== origin) {
    pushToast('该模板范围下已存在相同文档类型', 'warning')
    return
  }
  const payload = buildTemplatePayloadFromForm(vendor, docType, origin.id)
  const nextItems = templates.value.map((x) => (x === origin ? payload : x))
  const ok = await persistTemplates(nextItems)
  if (!ok) return
  selectTemplatePair(vendor, docType)
  const updated = findTemplate(vendor, docType)
  if (updated) applyTemplateToForm(updated)
  templateEditorCommitted.value = true
  templateEditorVisible.value = false
  pushToast('模板已更新', 'success')
}

function onTemplateEditorClosed() {
  resetSampleCanvas()
  if (!templateEditorCommitted.value) {
    restoreEditorState(templateEditorSnapshot.value)
  }
  templateEditorSnapshot.value = null
  templateEditorCommitted.value = false
}

async function deleteTemplate(vendor, docType) {
  if (templates.value.length <= 1) {
    pushToast('至少保留一个模板', 'warning')
    return
  }
  const target = findTemplate(vendor, docType)
  if (!target) {
    pushToast('模板不存在或已被删除', 'warning')
    return
  }
  if (!window.confirm(`确认删除模板「${templateDisplayName(target)}」吗？`)) return
  const nextItems = templates.value.filter((x) => x !== target)
  const ok = await persistTemplates(nextItems)
  if (!ok) return
  pushToast('模板已删除', 'info')
}

async function resetTemplateStore() {
  templatesLoading.value = true
  try {
    const resp = await fetch('/api/templates', { method: 'DELETE' })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `重置模板失败 ${resp.status}`)
    }
    const data = await resp.json()
    applyLoadedTemplates(data?.items, false)
    pushToast('模板已重置', 'info')
  } catch (err) {
    pushToast(err.message || '重置模板失败', 'error')
  } finally {
    templatesLoading.value = false
  }
}

function blockSensitiveCopy() {
  pushToast('安全策略：LLM API Key 不允许复制或剪切', 'warning', 2000)
}

function pushToast(message, type = 'info', ttl = 3500) {
  const map = {
    success: 'success',
    warning: 'warning',
    error: 'error',
    info: 'info',
  }
  ElMessage({
    message,
    type: map[type] || 'info',
    duration: ttl,
    showClose: true,
  })
}

async function loadPlatformInsightsFromServer(silent = true) {
  platformInsightsLoading.value = true
  try {
    const resp = await fetch('/api/platform-insights')
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `加载运营概览失败 ${resp.status}`)
    }
    const data = await resp.json()
    platformInsightsSource.value = normalizePlatformInsights(data)
    platformInsightsError.value = ''
    if (!silent) pushToast('运营概览已刷新', 'success', 1800)
    return true
  } catch (err) {
    platformInsightsSource.value = null
    platformInsightsError.value = err.message || '运营概览暂时使用本地数据'
    if (!silent) pushToast(platformInsightsError.value, 'warning', 2600)
    return false
  } finally {
    platformInsightsLoading.value = false
  }
}

async function refreshCurrentWorkspace() {
  if (currentNav.value === 'overview') {
    await Promise.all([
      loadPlatformInsightsFromServer(false),
      loadTaskList(true),
      loadHistoryList(false),
      loadTemplatesFromServer(false),
    ])
    return
  }
  if (currentNav.value === 'result') {
    await Promise.all([loadTaskList(true), loadHistoryList(false), loadPlatformInsightsFromServer(true)])
    pushToast('审核中心已刷新', 'success', 1800)
    return
  }
  if (currentNav.value === 'settings') {
    await Promise.all([loadLlmSettingsFromServer(), loadPlatformInsightsFromServer(true)])
    pushToast('平台设置已刷新', 'success', 1800)
    return
  }
  if (currentNav.value === 'extract') {
    await Promise.all([loadTaskList(true), loadTemplatesFromServer(false), loadPlatformInsightsFromServer(true)])
    pushToast('处理工作台已刷新', 'success', 1800)
    return
  }
  await Promise.all([loadTemplatesFromServer(false), loadPlatformInsightsFromServer(true)])
  pushToast('模板中心已刷新', 'success', 1800)
}

function openPlatformInsightsDialog() {
  platformInsightsDialogVisible.value = true
  loadPlatformInsightsFromServer(false)
}

function humanFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let idx = 0
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024
    idx += 1
  }
  return `${size.toFixed(idx === 0 ? 0 : 2)} ${units[idx]}`
}

function chooseDefaultEvidenceFile(files) {
  if (!Array.isArray(files) || files.length === 0) return null
  return pickPrimaryOriginalFile(files) || files.find((file) => classifyEvidenceFile(file) !== 'download') || files[0] || null
}

function evidenceTagType(file) {
  const type = classifyEvidenceFile(file)
  if (type === 'pdf') return 'danger'
  if (type === 'image') return 'success'
  if (type === 'markdown') return 'primary'
  if (type === 'text') return 'info'
  return ''
}

function evidenceTagLabel(file) {
  const type = classifyEvidenceFile(file)
  if (type === 'pdf') return 'PDF'
  if (type === 'image') return '图片'
  if (type === 'markdown') return 'Markdown'
  if (type === 'text') return '文本'
  return '文件'
}

function onFileChange(event) {
  file.value = event.target.files?.[0] || null
}

function onExtractUploadChange(uploadFile) {
  const raw = uploadFile?.raw || null
  if (!raw) return
  file.value = raw
  uploadWizardStep.value = 2
}

function onDrop(event) {
  dragOver.value = false
  const dropped = event.dataTransfer?.files?.[0]
  if (!dropped) return
  file.value = dropped
  const dt = new DataTransfer()
  dt.items.add(dropped)
  if (fileInput.value) fileInput.value.files = dt.files
}

function removeFile() {
  file.value = null
  uploadWizardStep.value = 1
  if (fileInput.value) fileInput.value.value = ''
}

function loadRegionRuleExample() {
  form.value.region_rules = JSON.stringify(
    [
      { field: '客户名称', page_idx: 0, bbox: [0, 0, 900, 320] },
      { field: '料号', page_idx: 0, bbox: [420, 640, 1320, 760] },
      { field: '到货数量', page_idx: 0, bbox: [1350, 640, 1750, 760] },
    ],
    null,
    2,
  )
}

function parsePromptFields(promptText) {
  const text = String(promptText || '').trim()
  if (!text) return []
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start >= 0 && end > start) {
    const maybeJson = text.slice(start, end + 1)
    try {
      const obj = JSON.parse(maybeJson)
      if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
        return Object.keys(obj).map((x) => String(x).trim()).filter(Boolean)
      }
    } catch {
      // ignore
    }
  }
  const cleaned = text
    .replace(/\n/g, ',')
    .replace(/，/g, ',')
    .replace(/、/g, ',')
    .replace(/;/g, ',')
    .replace(/；/g, ',')
  const seen = new Set()
  const items = []
  for (const token of cleaned.split(',')) {
    const value = String(token || '').trim()
    if (!value || seen.has(value) || value.length > 40) continue
    seen.add(value)
    items.push(value)
  }
  return items
}

function buildPromptFromFields(fields) {
  const cleaned = Array.from(new Set((fields || []).map((x) => String(x || '').trim()).filter(Boolean)))
  if (cleaned.length === 0) return ''
  const skeleton = {}
  for (const key of cleaned) skeleton[key] = ''
  skeleton.商品明细 = [{}]
  return `请提取${selectedDocType.value || '单据'}关键信息，以 JSON 返回：${JSON.stringify(skeleton)}。如存在多项商品，请在“商品明细”数组中逐项输出，每项字段按单据原文提取且不固定；无明细返回空数组 []。`
}

function ensureSublistPromptInstruction(promptText) {
  const raw = String(promptText || '').trim()
  const normalized = raw
    .replaceAll('子列表', '商品明细')
  const hint = '若存在多项商品，请在“商品明细”数组中逐项返回；每项字段按单据原文提取，无需固定字段名；无明细返回空数组 []。'
  if (!normalized) return hint
  if (normalized.includes('商品明细')) return normalized
  return `${normalized}\n${hint}`
}

function syncPromptByFieldItems() {
  form.value.llm_prompt = buildPromptFromFields(templateFieldItems.value)
}

function addFieldItem() {
  const value = String(fieldDraft.value || '').trim()
  if (!value) {
    pushToast('字段名不能为空', 'warning')
    return
  }
  if (templateFieldItems.value.includes(value)) {
    pushToast('字段已存在', 'warning')
    return
  }
  templateFieldItems.value.push(value)
  fieldDraft.value = ''
  syncPromptByFieldItems()
}

function removeFieldItem(index) {
  if (index < 0 || index >= templateFieldItems.value.length) return
  templateFieldItems.value.splice(index, 1)
  syncPromptByFieldItems()
}

function onFieldItemInput(index, value) {
  templateFieldItems.value[index] = String(value || '').trim()
  templateFieldItems.value = templateFieldItems.value.filter((x, i, arr) => x && arr.indexOf(x) === i)
  syncPromptByFieldItems()
}

function parseRegionRulesSafe(text) {
  const raw = String(text || '').trim()
  if (!raw) return []
  try {
    const data = JSON.parse(raw)
    if (!Array.isArray(data)) return []
    return data
      .map((x) => ({
        field: String(x?.field || '').trim(),
        page_idx: Number.isFinite(Number(x?.page_idx)) ? Number(x.page_idx) : 0,
        bbox: Array.isArray(x?.bbox) ? x.bbox.map((n) => Number(n)) : [],
      }))
      .filter((x) => x.field && x.bbox.length === 4 && x.bbox.every((n) => Number.isFinite(n)))
  } catch {
    return []
  }
}

function writeRegionRules(list) {
  form.value.region_rules = JSON.stringify(list, null, 2)
}

function triggerSampleUpload() {
  sampleFileInput.value?.click()
}

function resetSampleCanvas() {
  sampleDocKind.value = ''
  sampleFileName.value = ''
  samplePdfPage.value = 1
  samplePdfPages.value = 1
  draftRule.value = null
  ruleDrawStart.value = null
  samplePdfDoc = null
  const canvas = sampleCanvas.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    canvas.width = 0
    canvas.height = 0
    if (ctx) ctx.clearRect(0, 0, 0, 0)
  }
}

async function onSampleFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return
  resetSampleCanvas()
  sampleFileName.value = file.name
  const type = String(file.type || '').toLowerCase()
  if (type.includes('pdf') || file.name.toLowerCase().endsWith('.pdf')) {
    try {
      const bytes = await file.arrayBuffer()
      const loadingTask = pdfjsLib.getDocument({ data: bytes })
      samplePdfDoc = await loadingTask.promise
      sampleDocKind.value = 'pdf'
      samplePdfPages.value = samplePdfDoc.numPages || 1
      samplePdfPage.value = 1
      await renderSamplePdfPage()
      pushToast('PDF 样例已加载，可直接框选', 'success')
    } catch (err) {
      resetSampleCanvas()
      pushToast(`PDF 解析失败: ${err?.message || err}`, 'error')
    }
    return
  }
  if (type.startsWith('image/')) {
    try {
      const url = URL.createObjectURL(file)
      const img = await loadImage(url)
      const canvas = sampleCanvas.value
      if (!canvas) return
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')
      if (!ctx) return
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      sampleDocKind.value = 'image'
      samplePdfPages.value = 1
      samplePdfPage.value = 1
      URL.revokeObjectURL(url)
      pushToast('图片样例已加载，可直接框选', 'success')
    } catch (err) {
      pushToast(`图片加载失败: ${err?.message || err}`, 'error')
    }
    return
  }
  pushToast('仅支持 PDF 或图片样例', 'warning')
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = url
  })
}

async function renderSamplePdfPage() {
  if (!samplePdfDoc || !sampleCanvas.value || sampleDocKind.value !== 'pdf') return
  const pageNo = Math.max(1, Math.min(samplePdfPages.value, samplePdfPage.value))
  samplePdfPage.value = pageNo
  const page = await samplePdfDoc.getPage(pageNo)
  const viewport = page.getViewport({ scale: 1.8 })
  const canvas = sampleCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  canvas.width = Math.floor(viewport.width)
  canvas.height = Math.floor(viewport.height)
  await page.render({
    canvasContext: ctx,
    viewport,
  }).promise
}

watch(samplePdfPage, async () => {
  draftRule.value = null
  await renderSamplePdfPage()
})

function getCanvasPoint(event) {
  const canvas = sampleCanvas.value
  if (!canvas) return null
  const rect = canvas.getBoundingClientRect()
  if (!rect.width || !rect.height) return null
  const x = ((event.clientX - rect.left) / rect.width) * canvas.width
  const y = ((event.clientY - rect.top) / rect.height) * canvas.height
  return {
    x: Math.max(0, Math.min(canvas.width, x)),
    y: Math.max(0, Math.min(canvas.height, y)),
  }
}

function onRulePointerDown(event) {
  if (!sampleCanvas.value || !sampleDocKind.value) return
  const p = getCanvasPoint(event)
  if (!p) return
  isDrawingRule.value = true
  ruleDrawStart.value = p
  draftRule.value = { x1: p.x, y1: p.y, x2: p.x, y2: p.y }
}

function onRulePointerMove(event) {
  if (!isDrawingRule.value || !ruleDrawStart.value) return
  const p = getCanvasPoint(event)
  if (!p) return
  draftRule.value = {
    x1: ruleDrawStart.value.x,
    y1: ruleDrawStart.value.y,
    x2: p.x,
    y2: p.y,
  }
}

function onRulePointerUp() {
  isDrawingRule.value = false
}

function normalizedDraftRule() {
  const d = draftRule.value
  if (!d) return null
  const x1 = Math.min(d.x1, d.x2)
  const y1 = Math.min(d.y1, d.y2)
  const x2 = Math.max(d.x1, d.x2)
  const y2 = Math.max(d.y1, d.y2)
  if (x2 - x1 < 8 || y2 - y1 < 8) return null
  return [Math.round(x1), Math.round(y1), Math.round(x2), Math.round(y2)]
}

function addRuleFromSelection() {
  const field = String(sampleRuleField.value || '').trim()
  if (!field) {
    pushToast('请先填写字段名', 'warning')
    return
  }
  const bbox = normalizedDraftRule()
  if (!bbox) {
    pushToast('请先在样例上框选区域', 'warning')
    return
  }
  const list = parseRegionRulesSafe(form.value.region_rules)
  list.push({
    field,
    page_idx: currentSamplePageIndex.value,
    bbox,
  })
  writeRegionRules(list)
  draftRule.value = null
  ruleDrawStart.value = null
  pushToast('区域规则已添加，请保存模板', 'success')
}

function removeRuleAt(indexInPage) {
  const rules = parseRegionRulesSafe(form.value.region_rules)
  const page = currentSamplePageIndex.value
  let match = -1
  for (let i = 0, count = 0; i < rules.length; i += 1) {
    if (Number(rules[i].page_idx) !== Number(page)) continue
    if (count === indexInPage) {
      match = i
      break
    }
    count += 1
  }
  if (match < 0) return
  rules.splice(match, 1)
  writeRegionRules(rules)
  pushToast('已删除该规则', 'info')
}

function ruleStyle(rule) {
  const canvas = sampleCanvas.value
  if (!canvas || !Array.isArray(rule?.bbox) || rule.bbox.length !== 4) return {}
  const rect = canvas.getBoundingClientRect()
  if (!rect.width || !rect.height || !canvas.width || !canvas.height) return {}
  const sx = rect.width / canvas.width
  const sy = rect.height / canvas.height
  const [x1, y1, x2, y2] = rule.bbox
  return {
    left: `${x1 * sx}px`,
    top: `${y1 * sy}px`,
    width: `${(x2 - x1) * sx}px`,
    height: `${(y2 - y1) * sy}px`,
  }
}

function draftRuleStyle() {
  const bbox = normalizedDraftRule()
  if (!bbox) return {}
  return ruleStyle({ bbox })
}

function downloadResult() {
  const source = activeResult.value
  if (!source) {
    pushToast('暂无可下载数据', 'warning')
    return
  }
  const payload = { ...source, extracted: rows.value }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${source.filename || 'extract'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function openFieldDetail(row) {
  selectedFieldDetailRow.value = row || null
  fieldDetailVisible.value = Boolean(row)
}

async function locateSelectedFieldDetail() {
  const row = selectedFieldDetailRow.value
  if (!row) return
  fieldDetailVisible.value = false
  await nextTick()
  await jumpToField(row)
}

function encodePath(path) {
  return String(path || '')
    .split('/')
    .filter(Boolean)
    .map((x) => encodeURIComponent(x))
    .join('/')
}

function escapeRegex(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function splitUrlSuffix(path) {
  const value = String(path || '')
  const idxQ = value.indexOf('?')
  const idxH = value.indexOf('#')
  if (idxQ < 0 && idxH < 0) return { path: value, suffix: '' }
  let cut = value.length
  if (idxQ >= 0) cut = Math.min(cut, idxQ)
  if (idxH >= 0) cut = Math.min(cut, idxH)
  return {
    path: value.slice(0, cut),
    suffix: value.slice(cut),
  }
}

function collectLocateTexts(rawValue, limit = 80) {
  const picked = []
  const seen = new Set()
  const push = (value) => {
    const text = String(value ?? '').trim()
    if (!text || text === '-' || text.length < 2 || text.length > 120) return
    if (seen.has(text)) return
    seen.add(text)
    picked.push(text)
  }
  const walk = (node) => {
    if (picked.length >= limit) return
    if (node == null) return
    if (typeof node === 'string' || typeof node === 'number' || typeof node === 'boolean') {
      push(node)
      return
    }
    if (Array.isArray(node)) {
      for (const item of node) {
        walk(item)
        if (picked.length >= limit) break
      }
      return
    }
    if (typeof node === 'object') {
      for (const value of Object.values(node)) {
        walk(value)
        if (picked.length >= limit) break
      }
    }
  }
  walk(rawValue)
  return picked
}

function locateCandidatesForRow(row) {
  const candidates = []
  const summary = String(row?.value || '').trim()
  if (summary && summary !== '-') candidates.push(summary)
  const leaves = collectLocateTexts(row?.raw)
  for (const item of leaves) candidates.push(item)
  return [...new Set(candidates)].sort((a, b) => b.length - a.length)
}

function toHistoryResolvedUrl(rawRef, baseFilePath) {
  const { path, suffix } = splitUrlSuffix(rawRef)
  const resolved = resolveRelativePath(baseFilePath, path)
  const mapped = toHistoryAssetUrl(resolved, rawRef)
  if (mapped === rawRef) return mapped
  if (mapped.startsWith('http://') || mapped.startsWith('https://') || mapped.startsWith('data:')) return mapped
  return `${mapped}${suffix}`
}

function renderMarkedPreview(content, extractedRows, baseFilePath = '') {
  const html = markdown.render(String(content || ''))
  if (typeof document === 'undefined') return html
  const pairs = []
  if (Array.isArray(extractedRows)) {
    for (const row of extractedRows) {
      const key = String(row?.key || '').trim()
      if (!key) continue
      for (const value of locateCandidatesForRow(row)) {
        pairs.push({ key, value })
      }
    }
  }
  if (pairs.length === 0) return html

  const uniqueValues = [...new Set(pairs.map((x) => x.value))]
    .filter((x) => x.length >= 2)
    .sort((a, b) => b.length - a.length)
  if (uniqueValues.length === 0) return html

  const fieldByValue = new Map()
  const fieldsByValue = new Map()
  for (const item of pairs) {
    if (!fieldByValue.has(item.value)) fieldByValue.set(item.value, item.key)
    if (!fieldsByValue.has(item.value)) fieldsByValue.set(item.value, new Set())
    fieldsByValue.get(item.value).add(item.key)
  }

  const regex = new RegExp(uniqueValues.map(escapeRegex).join('|'), 'g')
  const root = document.createElement('div')
  root.innerHTML = html
  const imgs = root.querySelectorAll('img[src]')
  for (const img of imgs) {
    const src = img.getAttribute('src')
    if (!src) continue
    img.setAttribute('src', toHistoryResolvedUrl(src, baseFilePath))
  }
  const links = root.querySelectorAll('a[href]')
  for (const link of links) {
    const href = link.getAttribute('href')
    if (!href) continue
    link.setAttribute('href', toHistoryResolvedUrl(href, baseFilePath))
  }

  const nodes = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let current = walker.nextNode()
  while (current) {
    nodes.push(current)
    current = walker.nextNode()
  }

  const skipTags = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'MARK'])
  for (const node of nodes) {
    const parent = node.parentElement
    if (!parent || skipTags.has(parent.tagName)) continue
    const text = node.nodeValue || ''
    regex.lastIndex = 0
    if (!regex.test(text)) continue

    const fragment = document.createDocumentFragment()
    let lastIdx = 0
    regex.lastIndex = 0
    let matched = regex.exec(text)
    while (matched) {
      const match = matched[0]
      const offset = matched.index
      if (offset > lastIdx) {
        fragment.appendChild(document.createTextNode(text.slice(lastIdx, offset)))
      }
      const field = fieldByValue.get(match) || ''
      const fields = fieldsByValue.get(match) || new Set()
      if (shouldMarkWithContext(text, offset, match, field, fields)) {
        const mark = document.createElement('mark')
        mark.className = 'result-hit'
        mark.textContent = match
        mark.setAttribute('data-value', match)
        if (field) mark.setAttribute('data-field', field)
        fragment.appendChild(mark)
      } else {
        fragment.appendChild(document.createTextNode(match))
      }
      lastIdx = offset + match.length
      matched = regex.exec(text)
    }
    if (lastIdx < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(lastIdx)))
    }
    parent.replaceChild(fragment, node)
  }

  return root.innerHTML
}

function normalizeForMatch(text) {
  return String(text || '').replace(/\s+/g, ' ').trim()
}

function normalizeFieldText(text) {
  return String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]/g, '')
}

function buildFieldAliases(field) {
  const raw = String(field || '').trim()
  if (!raw) return []
  const parts = raw.split(/[\/|,，、]/).map((x) => x.trim()).filter(Boolean)
  const all = [raw, ...parts]
  const aliases = []
  const seen = new Set()
  for (const item of all) {
    const normalized = normalizeFieldText(item)
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    aliases.push(normalized)
  }
  return aliases
}

function hasFieldContextAround(text, field, offset, matchLength) {
  const aliases = buildFieldAliases(field)
  if (aliases.length === 0) return false
  const start = Math.max(0, offset - 100)
  const end = Math.min(text.length, offset + matchLength + 28)
  const around = normalizeFieldText(text.slice(start, end))
  return aliases.some((x) => around.includes(x))
}

function isNumericLikeValue(value) {
  return /^[\d\s.,:%\-+/()]+$/.test(String(value || '').trim())
}

function shouldMarkWithContext(text, offset, match, field, fieldsSet) {
  const hasMultiField = fieldsSet && fieldsSet.size > 1
  const numericLike = isNumericLikeValue(match)
  if (!field) return !numericLike && !hasMultiField
  if (hasFieldContextAround(text, field, offset, match.length)) return true
  if (numericLike || hasMultiField) return false
  return true
}

function findMatchedMark(root, key, value) {
  if (!root) return null
  const marks = Array.from(root.querySelectorAll('mark.result-hit'))
  if (marks.length === 0) return null
  const normKey = normalizeForMatch(key)
  const normValue = normalizeForMatch(value)
  const byField = marks.find((el) => normalizeForMatch(el.getAttribute('data-field')) === normKey)
  if (byField) return byField
  const byValueExact = marks.find((el) => normalizeForMatch(el.getAttribute('data-value')) === normValue)
  if (byValueExact) return byValueExact
  return marks.find((el) => normalizeForMatch(el.textContent) === normValue) || null
}

function findFallbackTextTarget(root, value) {
  if (!root) return null
  const target = normalizeForMatch(value)
  if (!target) return null
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node = walker.nextNode()
  while (node) {
    const parent = node.parentElement
    if (!parent || ['SCRIPT', 'STYLE'].includes(parent.tagName)) {
      node = walker.nextNode()
      continue
    }
    const text = normalizeForMatch(node.nodeValue || '')
    if (text.includes(target)) return parent
    node = walker.nextNode()
  }
  return null
}

function findFieldContextTextTarget(root, key, value) {
  if (!root) return null
  const targetKey = normalizeFieldText(key)
  const targetValue = normalizeForMatch(value)
  if (!targetKey || !targetValue) return null
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node = walker.nextNode()
  while (node) {
    const parent = node.parentElement
    if (!parent || ['SCRIPT', 'STYLE'].includes(parent.tagName)) {
      node = walker.nextNode()
      continue
    }
    const raw = String(node.nodeValue || '')
    const norm = normalizeForMatch(raw)
    if (norm.includes(targetValue) && normalizeFieldText(raw).includes(targetKey)) {
      return parent
    }
    node = walker.nextNode()
  }
  return null
}

async function jumpToField(row) {
  const key = String(row?.key || '').trim()
  const candidates = locateCandidatesForRow(row)
  if (!key || candidates.length === 0) {
    pushToast('该字段暂无命中内容，无法定位', 'warning')
    return
  }
  if (resultWorkspaceTab.value !== 'evidence') {
    resultWorkspaceTab.value = 'evidence'
    await nextTick()
  }
  if (hasMarkdownPreview.value && resultEvidenceTab.value !== 'markdown') {
    resultEvidenceTab.value = 'markdown'
    await nextTick()
  }
  if (previewCollapsed.value) {
    previewCollapsed.value = false
    await nextTick()
  }
  await nextTick()
  const root = previewPaneRef.value
  const modalRoot = previewPaneModalRef.value
  const activeRoot = modalRoot || root
  if (!activeRoot) {
    pushToast('预览区域未就绪', 'warning')
    return
  }

  let target = null
  for (const value of candidates) {
    target = findMatchedMark(activeRoot, key, value) || findFieldContextTextTarget(activeRoot, key, value)
    if (!target && !isNumericLikeValue(value)) {
      target = findFallbackTextTarget(activeRoot, value)
    }
    if (target) break
  }
  if (!target) {
    pushToast(`预览中未找到「${key}」的对应位置`, 'warning')
    return
  }

  target.classList.add('jump-target')
  target.scrollIntoView({ behavior: 'smooth', block: 'center' })
  window.setTimeout(() => target.classList.remove('jump-target'), 1600)
}

function resolveRelativePath(baseFilePath, relPath) {
  const rel = String(relPath || '').trim()
  if (!rel || rel.startsWith('http://') || rel.startsWith('https://') || rel.startsWith('data:') || rel.startsWith('/')) {
    return rel
  }
  const baseParts = String(baseFilePath || '')
    .split('/')
    .filter(Boolean)
  if (baseParts.length > 0) baseParts.pop()
  const relParts = rel.split('/').filter((x) => x.length > 0)
  const stack = [...baseParts]
  for (const part of relParts) {
    if (part === '.') continue
    if (part === '..') {
      if (stack.length > 0) stack.pop()
      continue
    }
    stack.push(part)
  }
  return stack.join('/')
}

function toHistoryAssetUrl(targetPath, fallback = '#') {
  const resolved = String(targetPath || '').trim()
  if (!resolved) return fallback
  if (resolved.startsWith('http://') || resolved.startsWith('https://') || resolved.startsWith('data:')) return resolved
  if (!selectedHistoryId.value) return fallback
  return `/api/history/${selectedHistoryId.value}/asset/${encodePath(resolved)}`
}

function renderHistoryMarkdown(content, baseFilePath) {
  const html = markdown.render(String(content || ''))
  return html
    .replace(/(<img\b[^>]*\bsrc=["'])([^"']+)(["'][^>]*>)/gi, (_m, p1, src, p3) => {
      const resolved = resolveRelativePath(baseFilePath, src)
      return `${p1}${toHistoryAssetUrl(resolved, src)}${p3}`
    })
    .replace(/(<a\b[^>]*\bhref=["'])([^"']+)(["'][^>]*>)/gi, (_m, p1, href, p3) => {
      const resolved = resolveRelativePath(baseFilePath, href)
      return `${p1}${toHistoryAssetUrl(resolved, href)}${p3}`
    })
}

function formatTime(text) {
  if (!text) return '-'
  const d = new Date(text)
  if (Number.isNaN(d.getTime())) return String(text)
  return d.toLocaleString('zh-CN', { hour12: false })
}

function taskStatusLabel(status) {
  const text = String(status || '').toLowerCase()
  if (text === 'queued') return '排队中'
  if (text === 'running') return '执行中'
  if (text === 'succeeded') return '已完成'
  if (text === 'failed') return '失败'
  return '未知'
}

function taskStatusTagType(status) {
  const text = String(status || '').toLowerCase()
  if (text === 'succeeded') return 'success'
  if (text === 'failed') return 'danger'
  if (text === 'queued') return 'info'
  return 'warning'
}

async function loadTaskList(silent = false) {
  if (!silent) taskLoading.value = true
  try {
    const resp = await fetch('/api/extract/tasks?limit=80')
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `加载任务失败 ${resp.status}`)
    }
    const data = await resp.json()
    taskItems.value = Array.isArray(data.items) ? data.items : []
  } catch (err) {
    if (!silent) pushToast(err.message || '加载任务失败', 'error')
  } finally {
    if (!silent) taskLoading.value = false
  }
}

function stopTaskPolling() {
  if (taskPollTimer) {
    window.clearInterval(taskPollTimer)
    taskPollTimer = null
  }
}

async function pollTask(taskId, silent = false) {
  if (!taskId) return
  try {
    const resp = await fetch(`/api/extract/tasks/${encodeURIComponent(taskId)}`)
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `查询任务失败 ${resp.status}`)
    }
    const detail = await resp.json()
    activeTaskId.value = detail.id || taskId
    const index = taskItems.value.findIndex((x) => x.id === detail.id)
    if (index >= 0) taskItems.value.splice(index, 1, detail)
    else taskItems.value.unshift(detail)

    const status = String(detail.status || '').toLowerCase()
    if (status === 'succeeded') {
      if (!activeTaskNotifiedDone.value) {
        const historyId = detail?.result?.history?.id
        await loadHistoryList(false)
        if (historyId) await openHistory(historyId)
        else if (!selectedHistoryId.value && historyItems.value[0]?.id) await openHistory(historyItems.value[0].id)
        if (detail?.result?.fallback_used) {
          pushToast('已自动降级到 pipeline（MinerU高精度引擎异常）', 'warning', 6000)
        }
        if (detail?.result?.auto_mode_enabled) pushToast(detail?.result?.auto_mode_message || '自动模式执行完成', 'success', 5000)
        else pushToast('提取完成，可在审核中心查看', 'success')
        await loadPlatformInsightsFromServer(true)
        activeTaskNotifiedDone.value = true
      }
      stopTaskPolling()
      return
    }
    if (status === 'failed') {
      if (!activeTaskNotifiedDone.value) {
        pushToast(detail.error || detail.message || '提取失败', 'error', 5000)
        await loadPlatformInsightsFromServer(true)
        activeTaskNotifiedDone.value = true
      }
      stopTaskPolling()
    }
  } catch (err) {
    if (!silent) pushToast(err.message || '查询任务失败', 'error')
  }
}

async function focusTask(taskId) {
  if (!taskId) return
  activeTaskId.value = String(taskId)
  const current = taskItems.value.find((x) => x.id === activeTaskId.value)
  const status = String(current?.status || '').toLowerCase()
  activeTaskNotifiedDone.value = ['succeeded', 'failed'].includes(status)
  await pollTask(activeTaskId.value, true)
  stopTaskPolling()
  taskPollTimer = window.setInterval(() => {
    pollTask(activeTaskId.value, true)
    loadTaskList(true)
  }, 2200)
}

async function loadHistoryList(autoSelect = true) {
  historyLoading.value = true
  try {
    const resp = await fetch('/api/history?limit=120')
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `加载历史失败 ${resp.status}`)
    }
    const data = await resp.json()
    historyItems.value = Array.isArray(data.items) ? data.items : []
    if (!autoSelect) return
    const stillExists = historyItems.value.some((x) => x.id === selectedHistoryId.value)
    const targetId = stillExists ? selectedHistoryId.value : historyItems.value[0]?.id
    if (targetId) {
      await openHistory(targetId)
    } else {
      selectedHistoryId.value = ''
      historyDetail.value = null
    }
  } catch (err) {
    pushToast(err.message || '加载历史失败', 'error')
  } finally {
    historyLoading.value = false
  }
}

async function deleteHistory(recordId) {
  const id = String(recordId || '').trim()
  if (!id) return
  if (deletingHistoryId.value) return
  const target = historyItems.value.find((x) => x.id === id)
  const name = target?.filename || id
  if (!window.confirm(`确认删除历史记录「${name}」吗？`)) return

  deletingHistoryId.value = id
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `删除历史失败 ${resp.status}`)
    }
    if (selectedHistoryId.value === id) {
      selectedHistoryId.value = ''
      historyDetail.value = null
      selectedHistoryFile.value = null
      historyFileText.value = ''
    }
    await loadHistoryList(true)
    pushToast('历史记录已删除', 'success')
  } catch (err) {
    pushToast(err.message || '删除历史失败', 'error')
  } finally {
    deletingHistoryId.value = ''
  }
}

async function openHistory(recordId) {
  if (!recordId) return
  selectedHistoryId.value = recordId
  selectedHistoryFile.value = null
  historyFileText.value = ''
  historyFileTextTruncated.value = false
  historyFileLoading.value = false
  historyPageMarginsMd.value = ''
  historyPageMarginsPages.value = []
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(recordId)}`)
    if (!resp.ok) throw new Error(`读取历史失败 ${resp.status}`)
    const detail = await resp.json()
    const summary = historyItems.value.find((x) => x?.id === recordId) || null
    if (detail && typeof detail === 'object' && summary && typeof summary === 'object') {
      if (!String(detail.vendor || '').trim() && String(summary.vendor || '').trim()) detail.vendor = summary.vendor
      if (!String(detail.doc_type || '').trim() && String(summary.doc_type || '').trim()) detail.doc_type = summary.doc_type
      if (detail.response && typeof detail.response === 'object') {
        if (!String(detail.response.vendor || '').trim() && String(detail.vendor || '').trim()) detail.response.vendor = detail.vendor
        if (!String(detail.response.doc_type || '').trim() && String(detail.doc_type || '').trim()) detail.response.doc_type = detail.doc_type
      }
    }
    historyDetail.value = detail
    resultEvidenceTab.value = chooseDefaultEvidenceTab({
      files: Array.isArray(detail?.files) ? detail.files : [],
      hasMarkdownPreview: Boolean(String(detail?.response?.preview || '').trim()),
    })
    selectedHistoryFile.value = chooseDefaultEvidenceFile(Array.isArray(detail?.files) ? detail.files : [])
    await Promise.all([
      loadFullMdPreview(recordId, detail?.files),
      loadHistoryPageMargins(recordId, detail?.files),
    ])
  } catch (err) {
    pushToast(err.message || '读取历史失败', 'error')
  }
}

function syncSubmissionDraftIntoHistory(detail, draft) {
  if (!detail || typeof detail !== 'object') return
  if (!detail.response || typeof detail.response !== 'object') detail.response = {}
  detail.response.submission = normalizeSubmissionDraft(draft)
}

function stopCustomsSubmitPolling() {
  if (customsSubmitPollTimer) {
    window.clearInterval(customsSubmitPollTimer)
    customsSubmitPollTimer = null
  }
}

function isSubmissionFieldMissing(fieldPath) {
  const missing = submissionDraft.value?.meta?.required_missing
  return Array.isArray(missing) && missing.includes(fieldPath)
}

function addSubmissionDetailRow() {
  submissionDraft.value = appendDraftDetailRow(submissionDraft.value)
}

function removeSubmissionDetailRow(index) {
  submissionDraft.value = removeDraftDetailRow(submissionDraft.value, index)
}

async function generateSubmissionDraft() {
  if (!selectedHistoryId.value) {
    pushToast('请先选择历史记录', 'warning')
    return
  }
  submissionDraftLoading.value = true
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(selectedHistoryId.value)}/submission-draft`, {
      method: 'POST',
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || `生成填报草稿失败 ${resp.status}`)
    submissionDraft.value = normalizeSubmissionDraft(data.submission)
    syncSubmissionDraftIntoHistory(historyDetail.value, data.submission)
    await loadPlatformInsightsFromServer(true)
    pushToast('已生成业务填报草稿', 'success')
  } catch (err) {
    pushToast(err.message || '生成填报草稿失败', 'error')
  } finally {
    submissionDraftLoading.value = false
  }
}

async function saveSubmissionDraft() {
  if (!selectedHistoryId.value) {
    pushToast('请先选择历史记录', 'warning')
    return false
  }
  submissionDraftSaving.value = true
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(selectedHistoryId.value)}/submission-draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submissionDraft.value),
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || `保存填报草稿失败 ${resp.status}`)
    submissionDraft.value = normalizeSubmissionDraft(data.submission)
    syncSubmissionDraftIntoHistory(historyDetail.value, data.submission)
    await loadPlatformInsightsFromServer(true)
    pushToast('填报草稿已保存', 'success')
    return true
  } catch (err) {
    pushToast(err.message || '保存填报草稿失败', 'error')
    return false
  } finally {
    submissionDraftSaving.value = false
  }
}

async function pollCustomsSubmitTask(taskId, silent = false) {
  if (!taskId) return
  try {
    const resp = await fetch(`/api/customs-submit/tasks/${encodeURIComponent(taskId)}`)
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || `查询目标系统提交任务失败 ${resp.status}`)
    customsSubmitTaskId.value = data.id || taskId
    if (String(data.status || '').toLowerCase() === 'succeeded') {
      customsSubmitting.value = false
      stopCustomsSubmitPolling()
      if (selectedHistoryId.value) await openHistory(selectedHistoryId.value)
      pushToast(data.message || '业务填报成功', 'success', 5000)
      return
    }
    if (String(data.status || '').toLowerCase() === 'failed') {
      customsSubmitting.value = false
      stopCustomsSubmitPolling()
      if (selectedHistoryId.value) await openHistory(selectedHistoryId.value)
      pushToast(data.error || data.message || '业务填报失败', 'error', 5000)
    }
  } catch (err) {
    customsSubmitting.value = false
    stopCustomsSubmitPolling()
    if (!silent) pushToast(err.message || '查询目标系统提交任务失败', 'error')
  }
}

async function submitSubmissionDraft() {
  if (!selectedHistoryId.value) {
    pushToast('请先选择历史记录', 'warning')
    return
  }
  const saved = await saveSubmissionDraft()
  if (!saved) return
  customsSubmitting.value = true
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(selectedHistoryId.value)}/submit-customs`, {
      method: 'POST',
    })
    const data = await resp.json().catch(() => ({}))
    if (!resp.ok) throw new Error(data.detail || `提交目标业务系统失败 ${resp.status}`)
    customsSubmitTaskId.value = data.task_id || ''
    stopCustomsSubmitPolling()
    customsSubmitPollTimer = window.setInterval(() => {
      pollCustomsSubmitTask(customsSubmitTaskId.value, true)
    }, 1800)
    await pollCustomsSubmitTask(customsSubmitTaskId.value, true)
    pushToast('已开始执行业务填报', 'success')
  } catch (err) {
    customsSubmitting.value = false
    pushToast(err.message || '提交目标业务系统失败', 'error')
  }
}

function pickFullMdFile(files) {
  return pickPrimaryMarkdownFile(files)
}

async function loadFullMdPreview(recordId, files) {
  fullMdContent.value = ''
  fullMdPath.value = ''
  fullMdTruncated.value = false
  fullMdLoading.value = false
  const target = pickFullMdFile(files)
  if (!target || !target.is_text || !recordId) return
  fullMdLoading.value = true
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(recordId)}/text/${encodePath(target.path)}`)
    if (!resp.ok) throw new Error(`读取 full.md 失败 ${resp.status}`)
    const data = await resp.json()
    if (selectedHistoryId.value !== recordId) return
    fullMdContent.value = data.content || ''
    fullMdPath.value = target.path
    fullMdTruncated.value = Boolean(data.truncated)
  } catch (err) {
    pushToast(err.message || '读取 full.md 失败', 'warning')
  } finally {
    if (selectedHistoryId.value === recordId) {
      fullMdLoading.value = false
    }
  }
}

function pickContentListFile(files) {
  if (!Array.isArray(files) || files.length === 0) return null
  const normalized = files.filter((x) => x && typeof x.path === 'string' && x.is_text)
  if (normalized.length === 0) return null
  const exactV2 = normalized.find((x) => x.path.toLowerCase().endsWith('/content_list_v2.json') || x.path.toLowerCase() === 'content_list_v2.json')
  if (exactV2) return exactV2
  const withContentList = normalized.find((x) => x.path.toLowerCase().includes('content_list') && x.path.toLowerCase().endsWith('.json'))
  if (withContentList) return withContentList
  return null
}

function collectTextParts(node, out) {
  if (typeof node === 'string') {
    const text = node.trim()
    if (text) out.push(text)
    return
  }
  if (Array.isArray(node)) {
    for (const item of node) collectTextParts(item, out)
    return
  }
  if (node && typeof node === 'object') {
    for (const value of Object.values(node)) {
      collectTextParts(value, out)
    }
  }
}

function normalizeInlineSpace(text) {
  return String(text || '').replace(/\s+/g, ' ').trim()
}

function extractBlockText(block) {
  const parts = []
  collectTextParts(block?.content, parts)
  if (parts.length === 0) collectTextParts(block, parts)
  return normalizeInlineSpace(parts.join(' '))
}

function parsePageMarginsPayload(rawText) {
  if (!rawText) return { appendix: '', pages: [] }
  let data = null
  try {
    data = JSON.parse(rawText)
  } catch {
    return { appendix: '', pages: [] }
  }

  const pages = []
  if (Array.isArray(data) && data.some((x) => Array.isArray(x))) {
    for (const pageNode of data) {
      const blocks = Array.isArray(pageNode) ? pageNode : [pageNode]
      const info = {
        headers: [],
        footers: [],
        anchors: [],
      }
      for (const block of blocks) {
        if (!block || typeof block !== 'object') continue
        const kind = String(block.type || '').trim().toLowerCase()
        const text = extractBlockText(block)
        if (!text) continue
        if (kind === 'page_header') {
          info.headers.push(text)
          continue
        }
        if (kind === 'page_footer') {
          info.footers.push(text)
          continue
        }
        if (kind !== 'image' && kind !== 'table' && info.anchors.length < 4) {
          info.anchors.push(text.slice(0, 80))
        }
      }
      info.headers = [...new Set(info.headers)]
      info.footers = [...new Set(info.footers)]
      if (info.headers.length > 0 || info.footers.length > 0) {
        pages.push(info)
      }
    }
  }

  const items = []
  const walk = (node) => {
    if (!node) return
    if (Array.isArray(node)) {
      for (const item of node) walk(item)
      return
    }
    if (typeof node !== 'object') return
    const kind = String(node.type || '').trim().toLowerCase()
    if (kind === 'page_header' || kind === 'page_footer') {
      const text = extractBlockText(node)
      if (text) items.push(`${kind === 'page_header' ? '页眉' : '页脚'}: ${text}`)
    }
    for (const value of Object.values(node)) walk(value)
  }
  walk(data)
  const deduped = [...new Set(items)]
  return {
    appendix: deduped.length > 0 ? `## 页眉页脚\n\n${deduped.map((x) => `- ${x}`).join('\n')}` : '',
    pages,
  }
}

function findAnchorPos(rawText, anchor, fromIndex = 0) {
  const source = String(rawText || '')
  const text = normalizeInlineSpace(anchor)
  if (!source || !text) return -1
  const candidates = [...new Set([text, text.slice(0, 36), text.slice(0, 18)].map((x) => x.trim()).filter((x) => x.length >= 4))]
  for (const c of candidates) {
    const pos = source.indexOf(c, Math.max(0, fromIndex))
    if (pos >= 0) return pos
  }
  return -1
}

function injectPageMarginsIntoMarkdown(rawMarkdown, pages) {
  const base = String(rawMarkdown || '')
  if (!base || !Array.isArray(pages) || pages.length === 0) return base

  const starts = []
  let cursor = 0
  for (const page of pages) {
    const anchor = Array.isArray(page?.anchors) ? (page.anchors.find((x) => String(x || '').trim().length >= 4) || page.anchors[0] || '') : ''
    const pos = findAnchorPos(base, anchor, cursor)
    starts.push(pos)
    if (pos >= 0) cursor = pos + 1
  }
  if (starts.every((x) => x < 0)) return base

  const buckets = new Map()
  const addInsertion = (pos, order, text) => {
    if (typeof pos !== 'number' || pos < 0) return
    if (!text) return
    if (!buckets.has(pos)) buckets.set(pos, [])
    buckets.get(pos).push({ order, text })
  }

  for (let i = 0; i < pages.length; i += 1) {
    const page = pages[i] || {}
    const pageStart = starts[i] >= 0 ? starts[i] : (i === 0 ? 0 : -1)
    const nextStart = starts.slice(i + 1).find((x) => x >= 0)
    const pageEnd = typeof nextStart === 'number' ? nextStart : base.length
    const headerText = [...new Set(Array.isArray(page.headers) ? page.headers : [])].join(' / ')
    const footerText = [...new Set(Array.isArray(page.footers) ? page.footers : [])].join(' / ')

    if (headerText && !base.includes(`页眉：${headerText}`)) {
      addInsertion(pageStart, 1, `\n\n> 页眉：${headerText}\n`)
    }
    if (footerText && !base.includes(`页脚：${footerText}`)) {
      addInsertion(pageEnd, 0, `\n> 页脚：${footerText}\n`)
    }
  }

  let output = base
  const positions = [...buckets.keys()].sort((a, b) => b - a)
  for (const pos of positions) {
    const chunk = buckets.get(pos)
      .sort((a, b) => a.order - b.order)
      .map((x) => x.text)
      .join('')
    output = `${output.slice(0, pos)}${chunk}${output.slice(pos)}`
  }
  return output
}

async function loadHistoryPageMargins(recordId, files) {
  historyPageMarginsMd.value = ''
  historyPageMarginsPages.value = []
  const target = pickContentListFile(files)
  if (!target || !recordId) return
  try {
    const resp = await fetch(`/api/history/${encodeURIComponent(recordId)}/text/${encodePath(target.path)}`)
    if (!resp.ok) return
    const data = await resp.json()
    if (selectedHistoryId.value !== recordId) return
    const parsed = parsePageMarginsPayload(data?.content || '')
    historyPageMarginsMd.value = parsed.appendix || ''
    historyPageMarginsPages.value = Array.isArray(parsed.pages) ? parsed.pages : []
  } catch {
    // ignore
  }
}

async function openHistoryFile(fileItem) {
  if (!selectedHistoryId.value || !fileItem) return
  selectedHistoryFile.value = fileItem
  const fileType = classifyEvidenceFile(fileItem)
  if (fileType === 'pdf' || fileType === 'image') resultEvidenceTab.value = 'original'
  else if (fileType === 'markdown' || fileType === 'text') resultEvidenceTab.value = 'assets'
  historyFileText.value = ''
  historyFileTextTruncated.value = false
  historyFileLoading.value = false
  if (!fileItem.is_text) return
  historyFileLoading.value = true
  try {
    const resp = await fetch(`/api/history/${selectedHistoryId.value}/text/${encodePath(fileItem.path)}`)
    if (!resp.ok) throw new Error(`读取文本失败 ${resp.status}`)
    const data = await resp.json()
    historyFileText.value = data.content || ''
    historyFileTextTruncated.value = Boolean(data.truncated)
  } catch (err) {
    pushToast(err.message || '读取文件失败', 'error')
  } finally {
    historyFileLoading.value = false
  }
}

function downloadHistoryZip() {
  if (!selectedHistoryId.value) {
    pushToast('请先选择历史记录', 'warning')
    return
  }
  const a = document.createElement('a')
  a.href = `/api/history/${selectedHistoryId.value}/download`
  a.download = `${selectedHistoryId.value}.zip`
  a.click()
}

function inferFieldsForLegacyBackend(promptText) {
  const text = String(promptText || '').trim()
  if (!text) return ''
  const start = text.indexOf('{')
  const end = text.lastIndexOf('}')
  if (start >= 0 && end > start) {
    const maybeJson = text.slice(start, end + 1)
    try {
      const obj = JSON.parse(maybeJson)
      if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
        const keys = Object.keys(obj).map((k) => String(k).trim()).filter(Boolean)
        if (keys.length > 0) return keys.join('\n')
      }
    } catch {
      // ignore parse failures and fallback
    }
  }
  return ''
}

function openExtractConfirmDialog() {
  uploadWizardStep.value = 2
  uploadWizardVisible.value = false
  extractConfirmVisible.value = true
}

async function confirmExtractLaunch() {
  if (!extractionLaunchReview.value.ready) {
    pushToast('请先补齐提取前检查项', 'warning')
    return
  }
  extractConfirmVisible.value = false
  uploadWizardVisible.value = false
  await nextTick()
  await submitForm()
}

async function submitForm() {
  if (!file.value) {
    pushToast('请先选择文件', 'warning')
    return
  }
  if (!String(selectedDocType.value || '').trim()) {
    pushToast('请先选择当前文档类型', 'warning')
    return
  }
  if (!form.value.llm_prompt.trim()) {
    pushToast('请填写大模型提取提示词', 'warning')
    return
  }

  submitting.value = true
  try {
    const fd = new FormData()
    const legacyFields = inferFieldsForLegacyBackend(form.value.llm_prompt)
    fd.append('file', file.value)
    const requestFields = buildExtractRequestFields({
      ...form.value,
      vendor: String(selectedVendor.value || activeTemplate.value?.vendor || '').trim(),
      doc_type: String(selectedDocType.value || '').trim(),
      llm_prompt: ensureSublistPromptInstruction(form.value.llm_prompt),
    })
    for (const [key, value] of requestFields) {
      fd.append(key, value)
    }
    if (legacyFields.trim()) fd.append('fields', legacyFields)

    const resp = await fetch('/api/extract/submit', {
      method: 'POST',
      body: fd,
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.detail || `请求失败 ${resp.status}`)
    }
    const data = await resp.json()
    if (!data.task_id) throw new Error('任务提交成功但未返回 task_id')
    activeTaskId.value = data.task_id
    activeTaskNotifiedDone.value = false
    currentNav.value = 'result'
    previewCollapsed.value = false
    await loadTaskList(true)
    await pollTask(activeTaskId.value, true)
    stopTaskPolling()
    taskPollTimer = window.setInterval(() => {
      pollTask(activeTaskId.value, true)
      loadTaskList(true)
    }, 2200)
    pushToast('任务已提交，正在后台提取，请在审核中心查看进度', 'success')
  } catch (err) {
    pushToast(err.message || '提取失败', 'error', 5000)
  } finally {
    submitting.value = false
  }
}

function handleWindowResize() {
  viewportWidth.value = window.innerWidth
  viewportHeight.value = window.innerHeight
}

onMounted(async () => {
  handleWindowResize()
  window.addEventListener('resize', handleWindowResize, { passive: true })
  await Promise.all([
    loadHistoryList(true),
    loadTaskList(true),
    loadLlmSettingsFromServer(),
    loadTemplatesFromServer(false),
    loadPlatformInsightsFromServer(true),
  ])
  autoModeReady.value = true
  const firstRunning = taskItems.value.find((x) => ['queued', 'running'].includes(String(x?.status || '').toLowerCase()))
  if (firstRunning?.id) {
    activeTaskId.value = firstRunning.id
    taskPollTimer = window.setInterval(() => {
      pollTask(activeTaskId.value, true)
      loadTaskList(true)
    }, 2200)
  }
})

onBeforeUnmount(() => {
  stopTaskPolling()
  stopCustomsSubmitPolling()
  window.removeEventListener('resize', handleWindowResize)
})
</script>

<template>
  <el-container class="ep-shell">
    <el-aside width="248px" class="ep-aside">
      <div class="ep-brand">
        <div class="brand-mark">N</div>
        <h1>NovaIDP</h1>
      </div>

      <el-menu class="ep-nav" :default-active="currentNav" @select="(key) => { currentNav = String(key) }">
        <el-menu-item v-for="item in NAV_ITEMS" :key="item.key" :index="item.key">
          <div class="nav-content">
            <span class="nav-index"><el-icon><component :is="item.icon" /></el-icon></span>
            <span class="nav-copy">
              <strong>{{ item.label }}</strong>
            </span>
          </div>
        </el-menu-item>
      </el-menu>

      <div class="environment-card">
        <span>当前环境</span>
        <strong><i />生产环境</strong>
        <el-icon><ArrowDown /></el-icon>
      </div>

      <button type="button" class="collapse-menu-button">
        <span>‹</span>
        收起菜单
      </button>
    </el-aside>

    <el-container class="ep-main">
      <header class="app-global-header">
        <div class="global-search">
          <el-icon><Search /></el-icon>
          <span>全局搜索（文档、模板、任务、字段等）</span>
          <kbd>⌘ K</kbd>
        </div>
        <div class="global-header-actions workspace-actions">
          <button type="button" class="workspace-switcher">
            <el-icon><Grid /></el-icon>
            默认工作区
            <el-icon><ArrowDown /></el-icon>
          </button>
          <button type="button" class="notification-badge" aria-label="通知">
            <el-icon><Bell /></el-icon>
            <span>12</span>
          </button>
          <span class="workspace-avatar" aria-label="当前用户">
            <el-icon><UserFilled /></el-icon>
            <strong>张伟</strong>
            <small>管理员</small>
            <el-icon><ArrowDown /></el-icon>
          </span>
        </div>
      </header>

      <el-main class="ep-content">
        <div class="page-title-bar">
          <div>
            <h2>{{ currentNavItem.label }}</h2>
            <p>{{ currentNavItem.desc }}</p>
          </div>
          <div class="page-title-actions">
            <el-button v-if="currentNav !== 'overview'" plain @click="currentNav = 'overview'">返回总览</el-button>
            <el-button circle aria-label="刷新当前工作区" @click="refreshCurrentWorkspace">
              <el-icon><RefreshRight /></el-icon>
            </el-button>
          </div>
        </div>

        <el-dialog
          v-model="platformInsightsDialogVisible"
          title="运营概览"
          class="platform-insights-dialog"
          width="min(1040px, 94vw)"
          top="5vh"
          append-to-body
        >
          <div v-if="platformInsightsError" class="platform-warning">
            {{ platformInsightsError }}，页面已回退到本地任务与历史数据。
          </div>

          <div class="platform-insights-grid" v-loading="platformInsightsLoading">
            <div
              v-for="item in platformInsightCards"
              :key="item.label"
              class="platform-metric-card"
              :class="`is-${item.tone}`"
            >
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
              <small>{{ item.hint }}</small>
            </div>
          </div>

          <div class="platform-dialog-layout">
            <div class="platform-dialog-main">
              <div class="platform-panel">
                <div class="ep-card-head spread">
                  <span>端到端处理流</span>
                  <el-tag :type="platformInsights.automation.enabled ? 'success' : 'info'">
                    {{ platformInsights.automation.enabled ? '自动模式' : '人工审核' }}
                  </el-tag>
                </div>
                <div class="platform-flow">
                  <div
                    v-for="step in platformFlow"
                    :key="step.label"
                    class="platform-flow-step"
                    :class="`is-${step.tone}`"
                  >
                    <span>{{ step.label }}</span>
                    <strong>{{ step.value }}</strong>
                    <small>{{ step.hint }}</small>
                  </div>
                </div>
              </div>

              <div class="platform-panel">
                <div class="ep-card-head spread">
                  <span>最近资料包</span>
                  <el-button text @click="platformInsightsDialogVisible = false; currentNav = 'result'">进入审核</el-button>
                </div>
                <el-table
                  v-if="platformInsights.history.recent.length > 0"
                  :data="platformInsights.history.recent"
                  size="small"
                  border
                  stripe
                >
                  <el-table-column prop="filename" label="文件" min-width="180" show-overflow-tooltip />
                  <el-table-column prop="doc_type" label="类型" width="95" />
                  <el-table-column label="复核" min-width="130">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.review_label.includes('缺失') || row.review_label.includes('复核') ? 'warning' : 'success'">
                        {{ row.review_label }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="时间" width="160">
                    <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                  </el-table-column>
                </el-table>
                <el-empty v-else description="暂无资料包记录" />
              </div>
            </div>

            <aside class="platform-dialog-side">
              <div class="platform-panel">
                <div class="ep-card-head spread">
                  <span>模板治理</span>
                  <el-button text @click="platformInsightsDialogVisible = false; currentNav = 'template'">维护</el-button>
                </div>
                <div class="platform-template-stats">
                  <div v-for="item in platformTemplateCoverage" :key="item.label">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                  </div>
                </div>
                <div class="platform-doc-types">
                  <el-tag
                    v-for="docType in platformInsights.templates.doc_types"
                    :key="docType"
                    type="info"
                  >
                    {{ docType }}
                  </el-tag>
                  <span v-if="platformInsights.templates.doc_types.length === 0">等待模板配置</span>
                </div>
              </div>

              <div class="platform-panel">
                <div class="ep-card-head">产品化建议</div>
                <div class="recommendation-list">
                  <div
                    v-for="(item, idx) in platformInsights.recommendations"
                    :key="`${idx}_${item}`"
                    class="recommendation-item"
                  >
                    <span>{{ idx + 1 }}</span>
                    <p>{{ item }}</p>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </el-dialog>

        <section v-show="currentNav === 'overview'" class="ep-section dashboard-overview">
          <div class="overview-meta-row">
            <span>数据更新于 2 分钟前</span>
            <el-button text :icon="RefreshRight" :loading="platformInsightsLoading" @click="refreshCurrentWorkspace">刷新</el-button>
          </div>

          <div class="overview-kpi-grid">
            <div
              v-for="item in dashboardKpis"
              :key="item.label"
              class="overview-kpi-card"
              :class="`is-${item.tone}`"
            >
              <span class="overview-kpi-icon"><el-icon><component :is="item.icon" /></el-icon></span>
              <div>
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <small>{{ item.hint }}</small>
              </div>
            </div>
          </div>

          <div class="overview-main-grid">
            <div class="overview-main-stack">
              <section class="design-panel process-overview-panel">
                <div class="design-panel-head">
                  <strong>处理流程概览</strong>
                </div>
                <div class="process-flow-track">
                  <div v-for="step in platformFlow" :key="step.label" class="process-node">
                    <span><el-icon><component :is="step.label === '接收资料' ? Upload : step.label === '解析抽取' ? DataAnalysis : step.label === '人审复核' ? UserFilled : Download" /></el-icon></span>
                    <strong>{{ step.label }}</strong>
                    <small>{{ step.hint }}</small>
                  </div>
                </div>
              </section>

              <section class="design-panel recent-task-panel">
                <div class="design-panel-head">
                  <strong>近期任务</strong>
                  <el-button text @click="currentNav = 'result'">查看全部</el-button>
                </div>
                <el-table
                  v-if="platformInsights.history.recent.length > 0"
                  :data="platformInsights.history.recent.slice(0, 6)"
                  size="small"
                  border
                >
                  <el-table-column prop="filename" label="文件名" min-width="240" show-overflow-tooltip />
                  <el-table-column prop="doc_type" label="文档类型" width="110" />
                  <el-table-column label="状态" width="110">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.review_label.includes('缺失') || row.review_label.includes('复核') ? 'warning' : 'success'">
                        {{ row.review_label }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="提交时间" width="170">
                    <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
                  </el-table-column>
                </el-table>
                <div v-else class="focus-empty">暂无近期任务</div>
              </section>
            </div>

            <aside class="overview-side-stack">
              <section class="design-panel quick-actions-panel">
                <div class="design-panel-head">
                  <strong>快捷操作</strong>
                </div>
                <button
                  v-for="item in dashboardQuickActions"
                  :key="item.label"
                  type="button"
                  class="quick-action-item"
                  :class="`is-${item.tone}`"
                  @click="currentNav = item.target"
                >
                  <span><el-icon><component :is="item.icon" /></el-icon></span>
                  <div>
                    <strong>{{ item.label }}</strong>
                    <small>{{ item.desc }}</small>
                  </div>
                  <i>›</i>
                </button>
              </section>

              <section class="design-panel service-status-panel">
                <div class="design-panel-head">
                  <strong>引擎与服务状态</strong>
                  <el-button text @click="currentNav = 'settings'">查看详情</el-button>
                </div>
                <div class="service-status-list">
                  <div v-for="item in dashboardServiceStatus" :key="item.name">
                    <el-icon><component :is="item.icon" /></el-icon>
                    <span>{{ item.name }}</span>
                    <el-tag size="small" type="success">{{ item.tag }}</el-tag>
                    <strong>{{ item.state }}</strong>
                  </div>
                </div>
              </section>

              <section class="design-panel doc-distribution-panel">
                <div class="design-panel-head">
                  <strong>文档类型分布（近 7 天）</strong>
                </div>
                <div class="donut-summary">
                  <div class="donut-ring"><strong>{{ platformInsights.history.total || historyItems.length }}</strong><span>总文档数</span></div>
                  <div class="doc-distribution-list">
                    <div v-for="item in docTypeDistribution" :key="item.name">
                      <span>{{ item.name }}</span>
                      <strong>{{ item.value }}%</strong>
                    </div>
                  </div>
                </div>
              </section>
            </aside>
          </div>
        </section>

        <section v-show="currentNav === 'template'" class="ep-section template-center-shell">
          <div class="section-hero">
            <div>
              <p class="section-kicker">Template Center</p>
              <h3>模板中心</h3>
              <p>先维护跨来源可复用的通用模板，再为特殊客户、厂商或业务来源创建专属模板覆盖规则。</p>
            </div>
          </div>

          <div class="template-summary-grid">
            <div class="template-summary-card">
              <span><el-icon><Grid /></el-icon></span>
              <strong>全部模板</strong>
              <b>{{ templates.length }}</b>
            </div>
            <div class="template-summary-card">
              <span><el-icon><UserFilled /></el-icon></span>
              <strong>通用模板</strong>
              <b>{{ templateStats.common }}</b>
            </div>
            <div class="template-summary-card">
              <span><el-icon><Document /></el-icon></span>
              <strong>来源专属</strong>
              <b>{{ templateStats.vendor }}</b>
            </div>
            <div class="template-summary-card">
              <span><el-icon><CircleCheck /></el-icon></span>
              <strong>当前字段</strong>
              <b>{{ activeTemplateFieldCount }}</b>
            </div>
          </div>

          <el-card class="ep-card template-board" shadow="hover">
            <div class="template-toolbar">
              <el-radio-group v-model="templateScopeFilter" class="template-scope-tabs">
                <el-radio-button label="all">全部</el-radio-button>
                <el-radio-button label="common">通用模板</el-radio-button>
                <el-radio-button label="vendor">来源专属</el-radio-button>
              </el-radio-group>
              <div class="template-toolbar-actions">
                <el-button type="primary" round :icon="Plus" :disabled="templatesLoading" @click="openCreateTemplateEditor">新增模板</el-button>
                <el-button round :icon="RefreshRight" :loading="templatesLoading" @click="refreshTemplateBoard">刷新列表</el-button>
                <el-button text class="toolbar-link" :disabled="templatesLoading" @click="resetTemplateStore">重置默认</el-button>
              </div>
            </div>

            <div class="table-intro">
              <span>当前启用：{{ activeTemplateName }}</span>
              <div class="ep-inline-actions">
                <el-tag type="success">字段 {{ activeTemplateFieldCount }}</el-tag>
                <el-tag type="info">通用 {{ templateStats.common }}</el-tag>
                <el-tag type="warning">专属 {{ templateStats.vendor }}</el-tag>
                <el-tag>显示 {{ templateStats.visible }}</el-tag>
              </div>
            </div>

            <el-table
              :data="templateBoardRows"
              size="small"
              v-loading="templatesLoading"
              height="520"
              border
              stripe
              :row-class-name="templateRowClass"
              @row-click="activateTemplateRow"
            >
              <el-table-column label="范围" width="112">
                <template #default="{ row }">
                  <el-tag size="small" :type="templateScopeTagType(row)">{{ row.scopeLabel }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="vendor" label="模板名称" min-width="240">
                <template #default="{ row }">
                  <div class="template-name-cell">
                    <strong>{{ row.displayName }}</strong>
                    <small v-if="row.scope === 'common'">未命中来源专属时自动使用</small>
                    <small v-else>优先匹配该来源资料</small>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="doc_type" label="模板类型" width="120" />
              <el-table-column label="字段数" width="100">
                <template #default="{ row }">{{ parsePromptFields(row.llm_prompt).length }}</template>
              </el-table-column>
              <el-table-column label="规则数" width="100">
                <template #default="{ row }">{{ parseRegionRulesSafe(row.region_rules).length }}</template>
              </el-table-column>
              <el-table-column label="操作" min-width="240" fixed="right">
                <template #default="{ row }">
                  <div class="table-actions action-links">
                    <el-button text type="primary" :disabled="templatesLoading" @click.stop="openEditTemplateEditor(row)">编辑</el-button>
                    <el-button text type="danger" :disabled="templatesLoading" @click.stop="deleteTemplate(row.vendor, row.doc_type)">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-dialog
            v-model="templateEditorVisible"
            :title="templateEditorTitle"
            class="template-editor-dialog"
            width="min(1260px, 96vw)"
            top="3vh"
            append-to-body
            destroy-on-close
            @closed="onTemplateEditorClosed"
          >
            <div class="template-editor-hero">
              <div>
                <p class="section-kicker">Template Editor</p>
                <h4>{{ templateEditorTitle }}</h4>
                <p>先维护字段列表自动生成提示词，再在样例上框选 region_rules。</p>
              </div>
              <div class="section-hero-metrics">
                <span class="metric-chip">字段 {{ templateFieldItems.length }}</span>
                <span class="metric-chip">规则 {{ parsedRegionRules.length }}</span>
              </div>
            </div>

            <el-form label-position="top" class="ep-form-tight template-editor-meta">
              <el-row :gutter="14">
                <el-col :xs="24" :lg="8">
                  <el-form-item label="模板范围">
                    <el-radio-group v-model="templateDraft.scope" class="template-scope-editor" @change="onTemplateScopeChange">
                      <el-radio-button label="common">通用模板</el-radio-button>
                      <el-radio-button label="vendor">来源专属</el-radio-button>
                    </el-radio-group>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="8">
                  <el-form-item label="来源名称">
                    <el-input
                      v-model.trim="templateDraft.vendor"
                      :disabled="templateDraft.scope === 'common'"
                      :placeholder="templateDraft.scope === 'common' ? '通用模板不绑定来源' : '输入客户、厂商或业务来源名称'"
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="8">
                  <el-form-item label="文档类型">
                    <el-select v-model="templateDraft.doc_type" class="w-full">
                      <el-option v-for="t in DOC_TYPES" :key="t" :label="t" :value="t" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="14">
                <el-col :xs="24" :lg="12">
                  <el-form-item label="model_version">
                    <el-select v-model="form.backend" class="w-full">
                      <el-option label="vlm" value="vlm" />
                      <el-option label="pipeline" value="pipeline" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="6">
                  <el-form-item label="parse_method">
                    <el-select v-model="form.parse_method" class="w-full">
                      <el-option v-for="item in PARSE_METHODS" :key="item" :label="item" :value="item" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="6">
                  <el-form-item label="lang_list">
                    <el-input v-model.trim="form.lang_list" placeholder="如：en 或 en,ch" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>

            <el-row :gutter="14" class="ep-row-gap template-editor-grid">
              <el-col :xs="24" :xl="9">
                <el-card class="template-editor-panel" shadow="never">
                  <template #header>
                    <div class="ep-card-head">字段维护</div>
                  </template>
                  <el-form label-position="top" class="ep-form-tight">
                    <el-form-item label="模板提取字段">
                      <div class="ep-inline-edit template-field-add">
                        <el-input
                          v-model.trim="fieldDraft"
                          placeholder="新增字段，例如：到货单号"
                          @keydown.enter.prevent="addFieldItem"
                        />
                        <el-button type="primary" @click="addFieldItem">添加</el-button>
                      </div>
                    </el-form-item>
                  </el-form>

                  <el-table
                    :data="templateFieldItems.map((name, idx) => ({ idx, name }))"
                    size="small"
                    border
                    empty-text="暂无字段"
                    class="field-table"
                    height="330"
                  >
                    <el-table-column label="#" type="index" width="54" />
                    <el-table-column label="字段名" min-width="170">
                      <template #default="{ row }">
                        <el-input
                          :model-value="row.name"
                          size="small"
                          @update:model-value="(val) => onFieldItemInput(row.idx, val)"
                        />
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="72">
                      <template #default="{ row }">
                        <el-button text type="danger" @click="removeFieldItem(row.idx)">删除</el-button>
                      </template>
                    </el-table-column>
                  </el-table>

                  <el-form label-position="top" class="top-gap">
                    <el-form-item label="自动生成提示词（只读）">
                      <el-input :model-value="form.llm_prompt" type="textarea" :rows="8" readonly />
                    </el-form-item>
                  </el-form>
                </el-card>
              </el-col>

              <el-col :xs="24" :xl="15">
                <el-card class="template-editor-panel" shadow="never">
                  <template #header>
                    <div class="ep-card-head">样例框选与规则</div>
                  </template>
                  <el-form label-position="top" class="ep-form-tight">
                    <el-form-item label="样例框选 region_rules（可选）">
                      <input
                        ref="sampleFileInput"
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff"
                        class="hidden-input"
                        @change="onSampleFileChange"
                      />
                      <div class="ep-inline-actions top-gap-xs wrap sample-toolbar">
                        <el-button type="primary" plain @click="triggerSampleUpload">上传样例文件</el-button>
                        <el-tag type="info">{{ sampleFileName || '未选择样例' }}</el-tag>
                        <template v-if="sampleDocKind === 'pdf'">
                          <el-button :disabled="samplePdfPage <= 1" @click="samplePdfPage -= 1">上一页</el-button>
                          <el-tag type="success">第 {{ samplePdfPage }} / {{ samplePdfPages }} 页</el-tag>
                          <el-button :disabled="samplePdfPage >= samplePdfPages" @click="samplePdfPage += 1">下一页</el-button>
                        </template>
                      </div>
                    </el-form-item>
                  </el-form>

                  <div
                    class="sample-stage"
                    @mousedown.prevent="onRulePointerDown"
                    @mousemove.prevent="onRulePointerMove"
                    @mouseup.prevent="onRulePointerUp"
                    @mouseleave.prevent="onRulePointerUp"
                  >
                    <canvas ref="sampleCanvas" class="sample-canvas" />
                    <div class="sample-overlay">
                      <div
                        v-for="(rule, idx) in visibleSampleRules"
                        :key="`${rule.field}_${idx}`"
                        class="sample-rect"
                        :style="ruleStyle(rule)"
                        :title="`${rule.field} [${rule.bbox.join(', ')}]`"
                        @dblclick.stop="removeRuleAt(idx)"
                      >
                        <span>{{ rule.field }}</span>
                      </div>
                      <div v-if="draftRule" class="sample-rect draft" :style="draftRuleStyle()" />
                    </div>
                  </div>

                  <div class="ep-inline-edit top-gap sample-rule-actions">
                    <el-input v-model.trim="sampleRuleField" placeholder="字段名，例如：料号" />
                    <el-button type="primary" @click="addRuleFromSelection">添加框选规则</el-button>
                    <el-button text @click="loadRegionRuleExample">加载示例</el-button>
                    <el-button text @click="form.region_rules = ''">清空规则</el-button>
                  </div>

                  <el-form label-position="top" class="top-gap">
                    <el-form-item label="region_rules JSON（自动生成，可手工微调）">
                      <el-input
                        v-model="form.region_rules"
                        type="textarea"
                        :rows="10"
                        placeholder='[{"field":"客户名称","page_idx":0,"bbox":[0,0,900,320]}]'
                      />
                    </el-form-item>
                  </el-form>
                </el-card>
              </el-col>
            </el-row>
            <template #footer>
              <div class="template-editor-footer">
                <el-button :disabled="templatesLoading" @click="templateEditorVisible = false">取消</el-button>
                <el-button type="primary" :loading="templatesLoading" @click="saveTemplateEditor">
                  {{ templateEditorMode === 'edit' ? '保存修改' : '创建模板' }}
                </el-button>
              </div>
            </template>
          </el-dialog>
        </section>

        <section v-show="currentNav === 'extract'" class="ep-section processing-workbench">
          <div class="workbench-config-panel design-panel">
            <div class="design-panel-head">
              <strong>任务配置</strong>
            </div>
            <div class="workbench-config-grid">
              <label>
                <span>来源 / 业务线</span>
                <el-select v-model="selectedVendor" class="w-full" clearable placeholder="通用业务线">
                  <el-option v-for="vendor in vendorOptions" :key="vendor" :label="vendor" :value="vendor" />
                </el-select>
              </label>
              <label>
                <span>文档类型</span>
                <el-select v-model="selectedDocType" class="w-full" placeholder="通用文档">
                  <el-option v-for="t in docTypeOptionsForSelectedVendor" :key="t" :label="t" :value="t" />
                </el-select>
              </label>
              <label>
                <span>OCR 引擎</span>
                <el-select v-model="form.backend" class="w-full">
                  <el-option label="MinerU" value="vlm" />
                  <el-option label="Pipeline" value="pipeline" />
                </el-select>
              </label>
              <label>
                <span>处理优先级</span>
                <el-select model-value="standard" class="w-full">
                  <el-option label="P2 标准" value="standard" />
                  <el-option label="P1 加急" value="urgent" />
                </el-select>
              </label>
            </div>
          </div>

          <div class="focus-workspace">
            <div class="workbench-upload-panel design-panel">
              <div class="design-panel-head">
                <strong>上传文档</strong>
              </div>
              <el-upload
                class="design-upload-zone"
                drag
                action="#"
                :auto-upload="false"
                :show-file-list="false"
                :accept="EXTRACT_UPLOAD_ACCEPT"
                :on-change="onExtractUploadChange"
              >
                <div class="upload-cloud"><el-icon><UploadFilled /></el-icon></div>
                <strong>将文件拖拽到此处，或点击上传</strong>
                <span>支持 PDF、图片、Word、PPT、Excel 文件；单个文件最大 200MB</span>
                <el-button type="primary" @click.stop="openUploadWizard(file ? 2 : 1)">选择文件</el-button>
              </el-upload>
              <div v-if="file" class="upload-file-meta">
                <el-tag type="info">{{ file.name }} ({{ humanFileSize(file.size) }})</el-tag>
                <el-button text type="danger" @click="removeFile">移除</el-button>
              </div>
            </div>

            <div class="focus-status-row">
              <span>状态 <strong>{{ focusReadyLabel }}</strong></span>
              <span>模板 <strong>{{ activeTemplateName }}</strong></span>
              <span>字段 <strong>{{ activeTemplateFieldCount }}</strong></span>
              <span>模型 <strong>{{ form.backend || '-' }}</strong></span>
            </div>

            <div class="focus-workspace-grid">
              <div class="focus-main-stack">
                <div class="focus-action-panel">
                  <div class="focus-action-copy">
                    <span>本次处理</span>
                    <strong>{{ file ? file.name : '等待上传资料' }}</strong>
                    <small>{{ file ? `${humanFileSize(file.size)} · ${selectedDocType || '未选择类型'}` : `${activeTemplateName} · ${workspaceModeLabel}` }}</small>
                  </div>
                  <div class="focus-action-buttons">
                    <el-button type="primary" :icon="UploadFilled" @click="openUploadWizard(file ? 2 : 0)">上传/配置</el-button>
                    <el-button :disabled="!file" :loading="submitting" @click="openExtractConfirmDialog">开始提取</el-button>
                    <el-button @click="currentNav = 'result'">进入审核</el-button>
                  </div>
                </div>

                <el-card class="ep-card focus-card" shadow="never">
                  <template #header>
                    <div class="ep-card-head spread">
                      <span>任务队列</span>
                      <el-button text :loading="taskLoading" @click="loadTaskList()">刷新</el-button>
                    </div>
                  </template>
                  <div v-if="focusQueueItems.length > 0" class="focus-task-list">
                    <button
                      v-for="task in focusQueueItems"
                      :key="task.id"
                      type="button"
                      class="focus-task-item"
                      @click="focusTask(task.id); currentNav = 'result'"
                    >
                      <div>
                        <strong>{{ task.filename || '未命名文件' }}</strong>
                        <span>{{ task.message || formatTime(task.updated_at) }}</span>
                      </div>
                      <el-tag size="small" :type="taskStatusTagType(task.status)">{{ taskStatusLabel(task.status) }}</el-tag>
                    </button>
                  </div>
                  <div v-else class="focus-empty">暂无后台任务</div>
                </el-card>
              </div>

              <aside class="focus-side-panel">
                <div class="focus-side-block">
                  <div class="focus-side-head">
                    <span>模板</span>
                    <el-button text @click="openTemplatePicker">切换</el-button>
                  </div>
                  <strong>{{ activeTemplateName }}</strong>
                  <small>{{ selectedDocType || '未选择文档类型' }} · {{ activeTemplateFieldCount }} 字段</small>
                </div>

                <div class="focus-side-block">
                  <div class="focus-side-head">
                    <span>最近记录</span>
                    <el-button text @click="currentNav = 'result'">查看</el-button>
                  </div>
                  <div v-if="focusRecentHistory.length > 0" class="focus-history-list">
                    <button
                      v-for="item in focusRecentHistory"
                      :key="item.id"
                      type="button"
                      @click="openHistory(item.id); currentNav = 'result'"
                    >
                      <strong>{{ item.filename || '未命名文件' }}</strong>
                      <span>{{ formatTime(item.created_at) }}</span>
                    </button>
                  </div>
                  <div v-else class="focus-empty">暂无历史记录</div>
                </div>
              </aside>
            </div>
          </div>

          <el-dialog
            v-model="uploadWizardVisible"
            title="上传资料"
            class="upload-wizard-dialog"
            width="min(1040px, 94vw)"
            top="4vh"
            append-to-body
          >
            <el-steps :active="uploadWizardStep" align-center finish-status="success" class="upload-wizard-steps">
              <el-step
                v-for="step in uploadWizardSteps"
                :key="step.title"
                :title="step.title"
                :description="step.desc"
              />
            </el-steps>

            <el-form label-position="top" class="upload-wizard-form" @submit.prevent="openExtractConfirmDialog">
              <div class="upload-wizard-body">
                <div class="upload-wizard-config">
                  <div class="ep-card-head">提取参数</div>
                  <el-form-item label="当前来源">
                    <el-select v-model="selectedVendor" class="w-full" clearable placeholder="可留空使用通用模板">
                      <el-option v-for="vendor in vendorOptions" :key="vendor" :label="vendor" :value="vendor" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="当前文档类型">
                    <el-select
                      v-model="selectedDocType"
                      class="w-full"
                      placeholder="选择文档类型"
                    >
                      <el-option v-for="t in docTypeOptionsForSelectedVendor" :key="t" :label="t" :value="t" />
                    </el-select>
                  </el-form-item>
                  <div class="fixed-config-list">
                    <el-tag type="info">model_version: {{ form.backend || '-' }}</el-tag>
                    <el-tag type="info">parse_method: {{ form.parse_method || '-' }}</el-tag>
                    <el-tag type="info">lang_list: {{ form.lang_list || '-' }}</el-tag>
                  </div>
                  <el-button type="primary" plain class="w-full" @click="openTemplatePicker">选择模板</el-button>
                  <el-button plain class="w-full top-gap-xs" @click="uploadWizardVisible = false; currentNav = 'template'">前往模板</el-button>
                </div>

                <div class="upload-wizard-content">
                  <el-tabs v-model="extractWorkspaceTab" class="workspace-tabs extract-workspace-tabs">
                    <el-tab-pane label="文件上传" name="upload">
                      <el-form-item label="文件上传">
                        <p class="field-hint">支持 PDF、图片、Office 与 Excel（.xlsx）。</p>
                        <el-upload
                          class="extract-uploader"
                          drag
                          action="#"
                          :auto-upload="false"
                          :show-file-list="false"
                          :accept="EXTRACT_UPLOAD_ACCEPT"
                          :on-change="onExtractUploadChange"
                        >
                          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                          <div class="el-upload__text">拖拽到此处，或 <em>点击上传</em></div>
                        </el-upload>
                        <div v-if="file" class="upload-file-meta">
                          <el-tag type="info">{{ file.name }} ({{ humanFileSize(file.size) }})</el-tag>
                          <el-button text type="danger" @click="removeFile">移除</el-button>
                        </div>
                      </el-form-item>
                    </el-tab-pane>
                    <el-tab-pane label="提示词" name="prompt">
                      <el-form-item label="大模型提取提示词">
                        <el-input
                          v-model="form.llm_prompt"
                          type="textarea"
                          :rows="12"
                          placeholder="例如：请从文档 Markdown 文本中提取编号、日期、主体、金额，并返回 JSON 对象。"
                        />
                      </el-form-item>
                    </el-tab-pane>
                  </el-tabs>
                </div>
              </div>
            </el-form>

            <template #footer>
              <div class="upload-wizard-footer">
                <el-button @click="uploadWizardVisible = false">取消</el-button>
                <el-button
                  :disabled="uploadWizardStep <= 0"
                  @click="uploadWizardStep = Math.max(0, uploadWizardStep - 1)"
                >
                  上一步
                </el-button>
                <el-button
                  v-if="uploadWizardStep < uploadWizardSteps.length - 1"
                  type="primary"
                  @click="uploadWizardStep = Math.min(uploadWizardSteps.length - 1, uploadWizardStep + 1)"
                >
                  下一步
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  :loading="submitting"
                  @click="openExtractConfirmDialog"
                >
                  {{ submitting ? '提交中...' : '开始提取' }}
                </el-button>
              </div>
            </template>
          </el-dialog>

          <el-dialog
            v-model="templatePickerVisible"
            title="选择识别模板"
            class="layer-dialog template-picker-dialog"
            width="min(920px, 94vw)"
            top="4vh"
            append-to-body
          >
            <div class="layer-dialog-intro">
              <div>
                <p class="section-kicker">Template Picker</p>
                <h4>选择本次文档要使用的模板</h4>
                <p>优先选择和业务来源、文档类型一致的模板。选择后会同步提示词、字段和区域规则。</p>
              </div>
              <el-tag type="info">模板 {{ templates.length }}</el-tag>
            </div>

            <el-input
              v-model="templatePickerQuery"
              class="template-picker-search"
              clearable
              placeholder="搜索来源、文档类型或提示词"
            />

            <div v-if="templatePickerItems.length > 0" class="template-picker-grid">
              <div
                v-for="tpl in templatePickerItems"
                :key="tpl.id || `${tpl.vendor}_${tpl.doc_type}`"
                class="template-picker-card"
                :class="{ active: tpl.active }"
                role="button"
                tabindex="0"
                @click="selectTemplateFromPicker(tpl)"
                @keydown.enter.prevent="selectTemplateFromPicker(tpl)"
                @keydown.space.prevent="selectTemplateFromPicker(tpl)"
              >
                <span class="template-picker-state">{{ tpl.active ? '当前模板' : '可选择' }}</span>
                <el-tag size="small" :type="templateScopeTagType(tpl)">{{ tpl.scopeLabel }}</el-tag>
                <strong>{{ tpl.name }}</strong>
                <p>{{ tpl.fieldCount > 0 ? `包含 ${tpl.fieldCount} 个提取字段` : '该模板暂未维护字段' }}</p>
                <div class="template-picker-meta">
                  <el-tag size="small" type="success">字段 {{ tpl.fieldCount }}</el-tag>
                  <el-tag size="small" type="info">规则 {{ tpl.ruleCount }}</el-tag>
                  <el-button text type="primary" @click.stop="editTemplateFromPicker(tpl)">编辑</el-button>
                </div>
              </div>
            </div>
            <el-empty v-else description="没有匹配的模板" />

            <template #footer>
              <div class="ep-inline-actions">
                <el-button @click="templatePickerVisible = false">关闭</el-button>
                <el-button type="primary" plain @click="templatePickerVisible = false; currentNav = 'template'">前往模板中心</el-button>
              </div>
            </template>
          </el-dialog>

          <el-dialog
            v-model="extractConfirmVisible"
            title="开始提取前确认"
            class="layer-dialog extract-confirm-dialog"
            width="min(760px, 94vw)"
            top="6vh"
            append-to-body
          >
            <div class="launch-review-head">
              <div>
                <p class="section-kicker">Launch Review</p>
                <h4>{{ extractionLaunchReview.ready ? '检查通过，可以开始提取' : '还有检查项需要处理' }}</h4>
                <p>{{ extractionLaunchReview.modeLabel }} · {{ extractionLaunchReview.ready ? '提交后会创建后台任务' : `剩余 ${extractionLaunchReview.blockerCount} 项未完成` }}</p>
              </div>
              <el-tag :type="extractionLaunchReview.ready ? 'success' : 'danger'">
                {{ extractionLaunchReview.ready ? 'Ready' : 'Blocked' }}
              </el-tag>
            </div>
            <div class="launch-review-list">
              <div
                v-for="item in extractionLaunchReview.items"
                :key="item.key"
                class="launch-review-item"
                :class="item.status"
              >
                <span class="launch-review-mark">{{ item.status === 'success' ? '✓' : item.status === 'error' ? '!' : 'i' }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.description }}</p>
                </div>
              </div>
            </div>
            <template #footer>
              <div class="ep-inline-actions">
                <el-button @click="extractConfirmVisible = false">取消</el-button>
                <el-button v-if="!extractionLaunchReview.ready" plain @click="extractConfirmVisible = false; openTemplatePicker()">选择模板</el-button>
                <el-button
                  type="primary"
                  :disabled="!extractionLaunchReview.ready"
                  :loading="submitting"
                  @click="confirmExtractLaunch"
                >
                  {{ extractionLaunchReview.primaryLabel }}
                </el-button>
              </div>
            </template>
          </el-dialog>
        </section>

        <section v-show="currentNav === 'result'" class="ep-section result-section review-center-shell">
          <div class="section-hero">
            <div>
              <p class="section-kicker">Result Center</p>
              <h3>审核中心</h3>
              <p>围绕当前记录查看系统判断、核对原始证据，并决定是否进入业务填报。</p>
            </div>
            <div class="section-hero-actions review-action-strip">
              <el-button :loading="taskLoading" @click="loadTaskList()">刷新任务</el-button>
              <el-button @click="loadHistoryList(true)">刷新历史</el-button>
              <el-button :disabled="!activeResult" :icon="Download" @click="downloadResult">下载 JSON</el-button>
              <el-button type="primary" :icon="EditPen" :disabled="!activeResult">人工修正</el-button>
            </div>
          </div>

          <el-row :gutter="14" class="ep-row-gap result-shell">
            <el-col :xs="24" :lg="6" :xl="5" class="result-left">
              <el-card class="ep-card history-card result-history-card" shadow="hover">
                <template #header>
                  <div class="ep-card-head spread">
                    <span>任务与历史</span>
                    <el-tag type="info">{{ historyItems.length }} 条</el-tag>
                  </div>
                </template>

                <div class="history-action-grid top-gap-xs">
                  <el-button :loading="taskLoading" @click="loadTaskList()">刷新任务</el-button>
                  <el-button @click="loadHistoryList(true)">刷新历史</el-button>
                  <el-button :disabled="!activeResult" @click="downloadResult">下载 JSON</el-button>
                </div>

                <div v-if="taskItems.length > 0" class="task-list-wrap top-gap">
                  <p class="field-hint">后台任务</p>
                  <div class="task-list">
                    <button
                      v-for="task in taskItems"
                      :key="task.id"
                      type="button"
                      class="task-item"
                      :class="{ active: task.id === activeTaskId }"
                      @click="focusTask(task.id)"
                    >
                      <div class="task-item-head">
                        <strong>{{ task.filename || '未命名文件' }}</strong>
                        <el-tag size="small" :type="taskStatusTagType(task.status)">{{ taskStatusLabel(task.status) }}</el-tag>
                      </div>
                      <el-progress
                        :stroke-width="6"
                        :percentage="Math.max(0, Math.min(100, Number(task.progress || 0)))"
                        :status="String(task.status || '').toLowerCase() === 'failed' ? 'exception' : (String(task.status || '').toLowerCase() === 'succeeded' ? 'success' : '')"
                      />
                      <span>{{ task.message || '-' }}</span>
                      <span>{{ formatTime(task.updated_at) }}</span>
                    </button>
                  </div>
                </div>

                <el-skeleton v-if="historyLoading" :rows="6" animated class="top-gap" />
                <el-empty v-else-if="historyItems.length === 0" description="暂无历史记录" class="top-gap" />
                <el-scrollbar v-else :height="historyScrollHeight" class="top-gap history-card-scroll">
                  <div class="history-list">
                    <button
                      v-for="item in historyItems"
                      :key="item.id"
                      type="button"
                      class="history-item"
                      :class="{ active: item.id === selectedHistoryId }"
                      @click="openHistory(item.id)"
                    >
                      <div class="history-item-head">
                        <strong>{{ item.filename || '未命名文件' }}</strong>
                        <span
                          class="history-item-delete"
                          :class="{ disabled: deletingHistoryId === item.id }"
                          @click.stop="deleteHistory(item.id)"
                        >
                          {{ deletingHistoryId === item.id ? '删除中...' : '删除' }}
                        </span>
                      </div>
                      <span>{{ formatTime(item.created_at) }}</span>
                      <span>命中 {{ item.hit_count }}/{{ item.target_count }} · {{ item.model_version || '-' }}</span>
                    </button>
                  </div>
                </el-scrollbar>
              </el-card>
            </el-col>

            <el-col :xs="24" :lg="18" :xl="19" class="result-right">
              <el-card class="ep-card result-main-card" shadow="hover">
                <template #header>
                  <div class="ep-card-head spread">
                    <span>识别结果</span>
                    <div class="ep-inline-actions">
                      <!-- <el-tag type="success">命中率 {{ hitRateText }}</el-tag> -->
                    </div>
                  </div>
                </template>

                <el-empty v-if="!activeResult" description="请先上传文件或选择历史记录" />
                <template v-else>
                  <div class="result-main-layout">
                    <div class="result-main-primary">
                  <div class="case-summary-band">
                    <div class="case-summary-copy">
                      <p class="case-summary-kicker">Active Case</p>
                      <h4>{{ activeCaseSummaryTitle }}</h4>
                      <p>{{ activeCaseNarrative }}</p>
                    </div>
                    <div class="case-summary-metrics">
                      <span class="case-pill">来源 {{ activeResultVendor }}</span>
                      <span class="case-pill">类型 {{ activeResultDocType }}</span>
                      <span class="case-pill">模板 {{ activeResultTemplateName }}</span>
                      <span class="case-pill">模型 {{ activeResult.model_version || activeResult.backend || '-' }}</span>
                      <span class="case-pill">记录 {{ historyDetail?.created_at ? formatTime(historyDetail.created_at) : '-' }}</span>
                      <span class="case-pill" :class="{ success: submissionDraftSummary.submitStatus === 'succeeded', warning: submissionDraftSummary.hasReviewWarnings }">
                        {{ workspaceReviewLabel }}
                      </span>
                    </div>
                  </div>

                  <el-descriptions :column="resultDescColumns" border size="small" class="result-desc">
                    <el-descriptions-item label="来源">{{ activeResultVendor }}</el-descriptions-item>
                    <el-descriptions-item label="类型">{{ activeResultDocType }}</el-descriptions-item>
                    <el-descriptions-item label="模型">{{ activeResult.model_version || activeResult.backend || '-' }}</el-descriptions-item>
                    <el-descriptions-item label="方法">{{ activeResult.parse_method || '-' }}</el-descriptions-item>
                    <el-descriptions-item label="LLM">{{ activeResult.llm_model || '-' }}</el-descriptions-item>
                    <el-descriptions-item label="区域规则">{{ activeResult.region_rules_count || 0 }}</el-descriptions-item>
                    <el-descriptions-item label="自动模式">{{ activeAutoModeEnabled ? '已开启' : '已关闭' }}</el-descriptions-item>
                    <el-descriptions-item label="记录时间">{{ historyDetail?.created_at ? formatTime(historyDetail.created_at) : '-' }}</el-descriptions-item>
                  </el-descriptions>

                  <el-alert
                    v-if="activeAutoModeView.enabled && activeAutoModeView.status !== 'idle'"
                    class="top-gap"
                    :title="activeAutoModeView.title"
                    :description="activeAutoModeView.description"
                    :type="activeAutoModeView.type"
                    :closable="false"
                    show-icon
                  />

                  <div class="result-workspace-grid top-gap">
                    <div class="workspace-primary">
                      <el-tabs v-model="resultWorkspaceTab" class="workspace-tabs result-workspace-tabs">
                        <el-tab-pane label="字段结果" name="fields">
                      <el-card shadow="never" class="workspace-panel">
                        <template #header>
                          <div class="ep-card-head spread">
                            <span>提取发现</span>
                            <div class="ep-inline-actions">
                              <el-tag type="success">命中 {{ hitCount }}</el-tag>
                              <el-tag type="info">字段 {{ rows.length }}</el-tag>
                            </div>
                          </div>
                        </template>
                        <el-empty v-if="visibleRows.length === 0" description="无已命中字段" />
                        <div v-else class="result-field-grid findings-grid">
                          <div
                            v-for="row in visibleRows"
                            :key="row.key"
                            class="result-field-item"
                          >
                            <div
                              class="result-field-jump"
                              role="button"
                              tabindex="0"
                              @click="jumpToField(row)"
                              @keydown.enter.prevent="jumpToField(row)"
                              @keydown.space.prevent="jumpToField(row)"
                            >
                              <div class="result-field-item-head">
                                <span class="result-field-item-label">字段</span>
                                <span class="result-field-actions">
                                  <el-tag :type="hasDetectedValue(row.raw) ? 'success' : 'info'" size="small">{{ hasDetectedValue(row.raw) ? '已命中' : '未识别' }}</el-tag>
                                  <el-button text type="primary" @click.stop="openFieldDetail(row)">详情</el-button>
                                </span>
                              </div>
                              <div class="result-key-cell">{{ row.key }}</div>
                            </div>
                            <div class="result-value-block">
                              <span class="result-field-item-label">值</span>
                              <div class="result-value-cell">{{ row.value || '-' }}</div>
                            </div>
                          </div>
                        </div>
                      </el-card>
                        </el-tab-pane>

                        <el-tab-pane label="商品明细" name="goods">
                      <el-card v-if="sublistBlocks.length > 0" shadow="never" class="workspace-panel">
                        <template #header>
                          <div class="ep-card-head spread">
                            <span>商品明细</span>
                            <div class="ep-inline-actions">
                              <el-tag type="success">命中 {{ sublistRowCount }}</el-tag>
                              <el-tag type="warning">缺失 0</el-tag>
                              <el-button text type="primary" @click="downloadResult">
                                <el-icon><Download /></el-icon>
                                导出
                              </el-button>
                            </div>
                          </div>
                        </template>
                        <div v-for="block in sublistBlocks" :key="block.field" class="top-gap-xs">
                          <p class="field-hint">{{ block.field }}</p>
                          <el-table :data="block.rows" border stripe size="small" class="top-gap-xs">
                            <el-table-column type="index" label="#" width="56" />
                            <el-table-column
                              v-for="col in block.columns"
                              :key="`${block.field}_${col}`"
                              :label="col"
                              min-width="140"
                            >
                              <template #default="{ row }">{{ row[col] || '-' }}</template>
                            </el-table-column>
                          </el-table>
                        </div>
                      </el-card>
                          <el-empty v-else description="当前记录没有商品明细" />
                        </el-tab-pane>

                        <el-tab-pane label="证据面板" name="evidence">
                      <el-card shadow="never" class="workspace-panel">
                        <template #header>
                          <div class="ep-card-head spread">
                            <span>证据面板</span>
                            <div class="ep-inline-actions">
                              <el-button v-if="resultEvidenceTab === 'markdown'" circle aria-label="弹窗预览" @click="previewModalVisible = true">
                                <el-icon><FullScreen /></el-icon>
                              </el-button>
                              <el-button v-if="resultEvidenceTab === 'markdown'" text @click="previewCollapsed = !previewCollapsed">{{ previewCollapsed ? '展开' : '收起' }}</el-button>
                              <el-button v-if="selectedHistoryId" text @click="downloadHistoryZip">下载产物包</el-button>
                            </div>
                          </div>
                        </template>

                        <div class="evidence-tabs" role="tablist" aria-label="证据类型">
                          <button
                            v-for="tab in evidenceTabOptions"
                            :key="tab.key"
                            type="button"
                            class="evidence-tab"
                            :class="{ active: resultEvidenceTab === tab.key }"
                            @click="resultEvidenceTab = tab.key"
                          >
                            {{ tab.label }}
                          </button>
                        </div>

                        <template v-if="resultEvidenceTab === 'original'">
                          <div v-if="primaryOriginalHistoryFile" class="evidence-panel">
                            <div class="evidence-panel-head">
                              <div>
                                <strong>{{ originalPreviewFile?.path }}</strong>
                                <span>{{ originalPreviewType === 'pdf' ? '原始 PDF' : '原始图片' }}</span>
                              </div>
                              <el-button v-if="originalPreviewUrl" text tag="a" :href="originalPreviewUrl" target="_blank">新窗口打开</el-button>
                            </div>
                            <iframe
                              v-if="originalPreviewType === 'pdf'"
                              :src="originalPreviewUrl"
                              class="asset-frame"
                              title="原始 PDF 预览"
                            />
                            <div v-else-if="originalPreviewType === 'image'" class="asset-image-wrap asset-image-stage">
                              <img :src="originalPreviewUrl" class="asset-image asset-image-large" alt="原始文件预览" />
                            </div>
                            <div v-else class="asset-download-tip">
                              <p>当前原始文件不支持内嵌预览。</p>
                            </div>
                          </div>
                          <el-empty v-else description="当前记录没有可预览的原始文件" />
                        </template>

                        <template v-else-if="resultEvidenceTab === 'markdown'">
                          <div v-show="!previewCollapsed" ref="previewPaneRef" class="preview-markdown evidence-surface" v-html="previewHtml" />
                        </template>

                        <template v-else>
                          <div v-if="evidenceAssetFiles.length > 0" class="evidence-panel">
                            <div class="asset-list">
                              <el-tag
                                v-for="fileItem in evidenceAssetFiles"
                                :key="fileItem.path"
                                class="asset-tag"
                                effect="plain"
                                :type="evidenceTagType(fileItem)"
                                @click="openHistoryFile(fileItem)"
                              >
                                {{ evidenceTagLabel(fileItem) }} · {{ fileItem.path }}
                              </el-tag>
                            </div>

                            <div v-if="selectedHistoryFile" class="asset-preview-wrap">
                              <div class="evidence-panel-head">
                                <div>
                                  <strong>{{ selectedHistoryFile.path }}</strong>
                                  <span>{{ evidenceTagLabel(selectedHistoryFile) }}</span>
                                </div>
                                <el-button v-if="historyAssetUrl" text tag="a" :href="historyAssetUrl" target="_blank">新窗口打开</el-button>
                              </div>
                              <iframe
                                v-if="selectedHistoryFileType === 'pdf'"
                                :src="historyAssetUrl"
                                class="asset-frame asset-preview"
                                title="文件预览"
                              />
                              <div v-else-if="selectedHistoryFileType === 'image'" class="asset-image-wrap asset-image-stage">
                                <img :src="historyAssetUrl" class="asset-image asset-image-large" alt="产物图片预览" />
                              </div>
                              <div v-else-if="selectedHistoryFileIsMarkdown" class="preview-markdown evidence-surface" v-html="historyFileHtml" />
                              <pre v-else-if="historyFileLoading" class="preview-plain">文件读取中...</pre>
                              <pre v-else-if="selectedHistoryFileType === 'text'" class="preview-plain">{{ historyFileText || '暂无文件内容' }}</pre>
                              <div v-else class="asset-download-tip">
                                <p>该文件暂不支持内嵌预览。</p>
                                <el-button v-if="historyAssetUrl" type="primary" plain tag="a" :href="historyAssetUrl" target="_blank">打开文件</el-button>
                              </div>
                            </div>
                          </div>
                          <el-empty v-else description="当前记录没有额外产物文件" />
                        </template>
                      </el-card>
                        </el-tab-pane>
                                          </el-tabs>
                                        </div>
                                      </div>
                    </div>

                    <div class="workspace-secondary">
                      <el-card shadow="never" class="workspace-panel submission-panel">
                        <template #header>
                          <div class="ep-card-head spread">
                            <span>业务填报工作区</span>
                            <div class="ep-inline-actions">
                              <el-tag :type="submissionDraftSummary.hasReviewWarnings ? 'warning' : 'success'">
                                缺失 {{ submissionDraftSummary.missingCount }}
                              </el-tag>
                              <el-tag v-if="submissionDraftSummary.reviewCount > 0" type="warning">复核 {{ submissionDraftSummary.reviewCount }}</el-tag>
                              <el-tag v-if="submissionPacketMeta.packet_id" type="info">资料包 {{ submissionPacketMeta.packet_id }}</el-tag>
                              <el-tag type="info">明细 {{ submissionDraftSummary.detailCount }}</el-tag>
                              <el-tag v-if="activeSubmissionResult?.declaration_no" type="success">单号 {{ activeSubmissionResult.declaration_no }}</el-tag>
                            </div>
                          </div>
                        </template>

                        <div class="submission-intro">
                          <p>这里负责把识别结果整理成可提交草稿，并保留最后一次目标系统返回结果。</p>
                        </div>

                        <div class="ep-inline-actions submission-actions">
                          <el-button :loading="submissionDraftLoading" :disabled="!selectedHistoryId" @click="generateSubmissionDraft">
                            {{ submissionDraftLoading ? '生成中...' : '生成填报草稿' }}
                          </el-button>
                          <el-button :loading="submissionDraftSaving" :disabled="!selectedHistoryId" @click="saveSubmissionDraft">
                            {{ submissionDraftSaving ? '保存中...' : '保存草稿' }}
                          </el-button>
                          <el-button
                            type="primary"
                            :loading="customsSubmitting"
                            :disabled="!selectedHistoryId"
                            @click="submitSubmissionDraft"
                          >
                            {{ customsSubmitting ? '提交中...' : '执行填报' }}
                          </el-button>
                        </div>

                        <el-alert
                          class="top-gap"
                          :title="submissionDraftSummary.submitMessage || '先确认字段，再手动触发服务端自动填报。'"
                          :type="submissionDraftSummary.hasReviewWarnings ? 'warning' : 'info'"
                          :closable="false"
                          show-icon
                        />

                        <div v-if="submissionPacketReviewItems.length > 0" class="submission-review-list top-gap">
                          <div
                            v-for="item in submissionPacketReviewItems"
                            :key="item.key"
                            class="submission-review-item"
                          >
                            <el-tag size="small" type="warning">{{ item.type }}</el-tag>
                            <strong>{{ item.title }}</strong>
                            <span>{{ item.description }}</span>
                          </div>
                        </div>

                        <el-row :gutter="12" class="top-gap">
                          <el-col
                            v-for="field in visibleCustomsHeaderFields"
                            :key="field"
                            :xs="24"
                            :sm="12"
                          >
                            <el-form-item :label="field" :required="isSubmissionFieldMissing(field)">
                              <el-input
                                v-model="submissionDraft.header[field]"
                                :class="{ 'is-error': isSubmissionFieldMissing(field) }"
                                :placeholder="`填写 ${field}`"
                              />
                            </el-form-item>
                          </el-col>
                        </el-row>
                        <div v-if="customsHeaderFields.length > 6" class="submission-more-toggle">
                          <el-button text type="primary" @click="submissionExtraFieldsVisible = !submissionExtraFieldsVisible">
                            {{ submissionExtraFieldsVisible ? '收起更多字段' : `展开更多字段（${hiddenCustomsHeaderFieldCount}）` }}
                          </el-button>
                        </div>

                        <div class="ep-card-head top-gap">
                          <span>明细行</span>
                        </div>
                        <div class="ep-inline-actions top-gap-xs">
                          <el-button @click="addSubmissionDetailRow">新增明细行</el-button>
                        </div>

                        <el-empty v-if="submissionDraft.details.length === 0" class="top-gap-xs" description="暂无明细行" />
                        <div v-else class="top-gap">
                          <el-card
                            v-for="(detailRow, idx) in submissionDraft.details"
                            :key="`submit_detail_${idx}`"
                            shadow="never"
                            class="top-gap-xs submission-detail-card"
                          >
                            <template #header>
                              <div class="ep-card-head spread">
                                <span>明细 {{ idx + 1 }}</span>
                                <el-button type="danger" text @click="removeSubmissionDetailRow(idx)">删除</el-button>
                              </div>
                            </template>
                            <el-row :gutter="12">
                              <el-col
                                v-for="field in customsDetailFields"
                                :key="`${idx}_${field}`"
                                :xs="24"
                                :sm="12"
                              >
                                <el-form-item :label="field" :required="isSubmissionFieldMissing(`details[${idx}].${field}`)">
                                  <el-input
                                    v-model="detailRow[field]"
                                    :class="{ 'is-error': isSubmissionFieldMissing(`details[${idx}].${field}`) }"
                                    :placeholder="`填写 ${field}`"
                                  />
                                </el-form-item>
                              </el-col>
                            </el-row>
                          </el-card>
                        </div>
                      </el-card>
                    </div>
                  </div>
                </template>
              </el-card>
            </el-col>
          </el-row>

          <el-dialog
            v-model="previewModalVisible"
            title="Markdown / 文本预览"
            width="min(1280px, 94vw)"
            top="4vh"
            append-to-body
          >
            <div ref="previewPaneModalRef" class="preview-markdown preview-markdown-modal" v-html="previewHtml" />
          </el-dialog>

          <el-dialog
            v-model="fieldDetailVisible"
            :title="`字段详情：${selectedFieldDetail.title}`"
            class="layer-dialog field-detail-dialog"
            width="min(860px, 94vw)"
            top="6vh"
            append-to-body
          >
            <div class="field-detail-shell">
              <div class="field-detail-main">
                <div class="field-detail-head">
                  <div>
                    <p class="section-kicker">Field Evidence</p>
                    <h4>{{ selectedFieldDetail.title }}</h4>
                  </div>
                  <el-tag :type="selectedFieldDetail.statusType">{{ selectedFieldDetail.statusLabel }}</el-tag>
                </div>
                <div class="field-detail-block">
                  <span>展示值</span>
                  <p>{{ selectedFieldDetail.valueText }}</p>
                </div>
                <div class="field-detail-block">
                  <span>{{ selectedFieldDetail.isStructured ? '结构化原值' : '原始值' }}</span>
                  <pre>{{ selectedFieldDetail.rawText || '-' }}</pre>
                </div>
              </div>
              <aside class="field-detail-aside">
                <strong>证据定位</strong>
                <p>点击定位会跳到证据面板，并高亮原文中匹配的字段值。</p>
                <div v-if="selectedFieldLocateTexts.length > 0" class="field-detail-chips">
                  <span v-for="text in selectedFieldLocateTexts.slice(0, 6)" :key="text">{{ text }}</span>
                </div>
                <el-empty v-else description="暂无可定位文本" />
              </aside>
            </div>
            <template #footer>
              <div class="ep-inline-actions">
                <el-button @click="fieldDetailVisible = false">关闭</el-button>
                <el-button type="primary" :disabled="!selectedFieldDetailRow" @click="locateSelectedFieldDetail">在证据中定位</el-button>
              </div>
            </template>
          </el-dialog>
        </section>

        <section v-show="currentNav === 'evidence'" class="ep-section evidence-center-shell">
          <div class="design-panel placeholder-workspace">
            <div>
              <p class="section-kicker">Evidence Center</p>
              <h3>证据中心</h3>
              <p>集中管理原始文件、Markdown、截图证据和字段定位。当前资料的证据入口仍在审核中心内。</p>
            </div>
            <el-button type="primary" @click="currentNav = 'result'">进入审核中心</el-button>
          </div>
        </section>

        <section v-show="currentNav === 'automation'" class="ep-section automation-center-shell">
          <div class="design-panel placeholder-workspace">
            <div>
              <p class="section-kicker">Automation Tasks</p>
              <h3>自动化任务</h3>
              <p>展示后台队列、自动提取、自动填报与调度状态。当前可在总览和工作台查看实时队列。</p>
            </div>
            <el-button type="primary" @click="currentNav = 'overview'">查看总览</el-button>
          </div>
        </section>

        <section v-show="currentNav === 'settings'" class="ep-section settings-console">
          <div class="section-hero">
            <div>
              <p class="section-kicker">System Settings</p>
              <h3>平台设置</h3>
              <p>这里维护长期配置与系统运行姿态，不承载任务期的临时决策。</p>
            </div>
            <div class="section-hero-metrics">
              <span class="metric-chip">启用配置: {{ activeLlmConfigName }}</span>
              <span class="metric-chip">LLM: {{ llmProviderLabel(llmProvider) }}</span>
              <span class="metric-chip">Model: {{ form.llm_model || '-' }}</span>
            </div>
          </div>

          <div class="settings-tab-strip">
            <button
              v-for="item in settingsTabs"
              :key="item"
              type="button"
              :class="{ active: item === 'LLM 配置' }"
            >
              {{ item }}
            </button>
          </div>

          <el-row :gutter="14" class="ep-row-gap">
            <el-col :xs="24" :xl="14">
              <el-card class="ep-card" shadow="hover">
                <template #header>
                  <div class="ep-card-head">LLM 接入设置</div>
                </template>
                <div class="settings-card-intro">
                  <p>管理模型供应商、地址和 API Key。这里定义的是系统基础能力，而不是单次任务行为。</p>
                </div>
                <el-row :gutter="12">
                  <el-col :xs="24" :lg="14">
                    <el-form label-position="top" class="ep-form-tight">
                      <el-form-item label="当前启用配置">
                        <el-select
                          v-model="activeLlmConfigId"
                          class="w-full"
                          filterable
                          :disabled="llmSettingsLoading"
                          @change="onActiveLlmConfigChange"
                        >
                          <el-option
                            v-for="cfg in llmConfigs"
                            :key="cfg.id"
                            :label="`${cfg.name}（${llmProviderLabel(cfg.provider)}）`"
                            :value="cfg.id"
                          />
                        </el-select>
                      </el-form-item>
                    </el-form>
                  </el-col>
                  <el-col :xs="24" :lg="10">
                    <div class="ep-inline-actions top-gap">
                      <el-button :disabled="llmSettingsLoading" @click="openCreateLlmConfig">新增配置</el-button>
                    </div>
                  </el-col>
                </el-row>

                <div class="fixed-config-list top-gap">
                  <el-tag type="success">提供商: {{ activeLlmConfigSummary.provider }}</el-tag>
                  <el-tag type="info">模型: {{ activeLlmConfigSummary.model }}</el-tag>
                  <el-tag type="info">Base URL: {{ activeLlmConfigSummary.baseUrl }}</el-tag>
                </div>

                <el-form label-position="top" class="ep-form-tight">
                  <el-row :gutter="12">
                    <el-col :xs="24" :lg="8">
                      <el-form-item label="提供商">
                        <el-select v-model="llmProvider" class="w-full" :disabled="llmSettingsLoading" @change="(v) => applyLlmProviderPreset(v)">
                          <el-option v-for="item in LLM_PROVIDER_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :xs="24" :lg="16">
                      <el-form-item label="LLM Base URL">
                        <el-input v-model.trim="form.llm_base_url" :disabled="llmSettingsLoading" placeholder="如：https://api.deepseek.com/v1" />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <div class="ep-inline-actions top-gap-xs">
                    <el-button plain :disabled="llmSettingsLoading" @click="applyLlmProviderPreset('deepseek')">DeepSeek 预设</el-button>
                    <el-button plain :disabled="llmSettingsLoading" @click="applyLlmProviderPreset('gemini')">Gemini 预设</el-button>
                    <el-button plain :disabled="llmSettingsLoading" @click="applyLlmProviderPreset('bailian')">百炼预设</el-button>
                  </div>
                  <el-row :gutter="12">
                    <el-col :xs="24" :lg="12">
                      <el-form-item label="LLM Model">
                        <el-input v-model.trim="form.llm_model" :disabled="llmSettingsLoading" placeholder="如：deepseek-chat / gemini-3-flash-preview" />
                      </el-form-item>
                    </el-col>
                    <el-col :xs="24" :lg="12">
                      <el-form-item label="LLM API Key">
                        <el-input
                          v-model.trim="form.llm_api_key"
                          type="password"
                          :disabled="llmSettingsLoading"
                          autocomplete="new-password"
                          @copy.prevent="blockSensitiveCopy"
                          @cut.prevent="blockSensitiveCopy"
                          placeholder="输入 API Key（保存在后端配置文件）"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </el-form>
                <div class="ep-inline-actions">
                  <el-button :disabled="llmSettingsLoading || !activeLlmConfig" @click="openEditLlmConfig(activeLlmConfig)">编辑当前配置</el-button>
                  <el-button type="danger" :disabled="llmSettingsLoading || !activeLlmConfig" @click="deleteLlmConfig(activeLlmConfigId)">删除当前配置</el-button>
                  <el-button :disabled="llmSettingsLoading" @click="resetLlmSettings">恢复默认</el-button>
                  <el-button type="primary" :loading="llmSettingsLoading" @click="saveLlmSettings">保存设置</el-button>
                </div>

                <el-table :data="llmConfigs" size="small" border stripe class="top-gap">
                  <el-table-column prop="name" label="配置名" min-width="170" />
                  <el-table-column label="提供商" width="110">
                    <template #default="{ row }">{{ llmProviderLabel(row.provider) }}</template>
                  </el-table-column>
                  <el-table-column prop="llm_model" label="模型" min-width="130" />
                  <el-table-column label="操作" width="210">
                    <template #default="{ row }">
                      <div class="table-actions action-links">
                        <el-tag v-if="row.id === activeLlmConfigId" type="success">已启用</el-tag>
                        <el-button v-else text type="primary" :disabled="llmSettingsLoading" @click="activateLlmConfig(row.id)">启用</el-button>
                        <el-button text :disabled="llmSettingsLoading" @click="openEditLlmConfig(row)">编辑</el-button>
                        <el-button text type="danger" :disabled="llmSettingsLoading || llmConfigs.length <= 1" @click="deleteLlmConfig(row.id)">删除</el-button>
                      </div>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>

            <el-col :xs="24" :xl="10">
              <el-card class="ep-card auto-mode-card" shadow="hover">
                <template #header>
                  <div class="ep-card-head">自动模式</div>
                </template>
                <div class="auto-mode-panel">
                  <div class="auto-mode-panel-head">
                    <div>
                      <p class="auto-mode-kicker">Automation Control</p>
                      <h4>自动模式</h4>
                    </div>
                    <el-tag :type="autoModeEnabled ? 'success' : 'info'" effect="dark">
                      {{ autoModeEnabled ? '已开启' : '已关闭' }}
                    </el-tag>
                  </div>

                  <div class="auto-mode-panel-body">
                    <div class="auto-mode-copy">
                      <p class="auto-mode-title">上传后自动执行提取、字段映射和业务填报</p>
                      <p class="auto-mode-desc">开启后，新任务会在后台自动串行执行 OCR 提取、LLM 填报草稿生成和自动提交。即使草稿存在缺字段，也会继续尝试提交，并把目标系统返回结果写回审核中心。</p>
                      <div class="auto-mode-flow">
                        <span>提取</span>
                        <i />
                        <span>字段映射</span>
                        <i />
                        <span>自动填报</span>
                      </div>
                    </div>

                    <div class="auto-mode-toggle-card">
                      <span class="auto-mode-toggle-label">后台自动串行执行</span>
                      <el-switch v-model="autoModeEnabled" :disabled="llmSettingsLoading" size="large" />
                      <span class="auto-mode-toggle-tip">{{ autoModeEnabled ? '当前新任务将直接进入自动流水线' : '当前仍使用人工触发填报流程' }}</span>
                    </div>

                    <div class="auto-mode-toggle-card">
                      <span class="auto-mode-toggle-label">目标系统提交模式</span>
                      <el-select v-model="customsSubmitMode" class="w-full" :disabled="llmSettingsLoading">
                        <el-option label="HTTP" value="http" />
                        <el-option label="Playwright" value="playwright" />
                      </el-select>
                      <span class="auto-mode-toggle-tip">手工提交和自动模式会共用同一个目标系统提交引擎。</span>
                    </div>
                  </div>
                </div>
              </el-card>

              <el-card class="ep-card" shadow="hover">
                <template #header>
                  <div class="ep-card-head">配置说明</div>
                </template>
                <el-alert
                  title="DeepSeek、Gemini 与百炼可通过上方提供商预设快速切换，也可改为自定义兼容 OpenAI 的地址。"
                  type="info"
                  :closable="false"
                  show-icon
                />
                <el-alert
                  class="top-gap"
                  title="自动模式是系统级总开关，建议在大模型配置稳定后再开启。"
                  type="warning"
                  :closable="false"
                  show-icon
                />
                <!-- <el-alert
                  class="top-gap"
                  title="LLM 设置保存在后端 output/settings/llm_settings.json，不会写入模板。MinerU 参数仍在模板中心维护。"
                  type="warning"
                  :closable="false"
                  show-icon
                /> -->
              </el-card>
            </el-col>
          </el-row>

          <el-dialog
            v-model="llmConfigDialogVisible"
            :title="llmConfigDialogTitle"
            width="min(760px, 94vw)"
            append-to-body
          >
            <el-form label-position="top" class="ep-form-tight">
              <el-row :gutter="12">
                <el-col :xs="24" :lg="10">
                  <el-form-item label="配置名">
                    <el-input v-model.trim="llmConfigDraft.name" placeholder="例如：DeepSeek 生产环境" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="6">
                  <el-form-item label="提供商">
                    <el-select v-model="llmConfigDraft.provider" class="w-full" @change="onLlmDraftProviderChange">
                      <el-option v-for="item in LLM_PROVIDER_OPTIONS" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="8">
                  <el-form-item label="模型">
                    <el-input v-model.trim="llmConfigDraft.llm_model" placeholder="如：deepseek-chat" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="12">
                <el-col :xs="24" :lg="14">
                  <el-form-item label="Base URL">
                    <el-input v-model.trim="llmConfigDraft.llm_base_url" placeholder="如：https://api.deepseek.com/v1" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :lg="10">
                  <el-form-item label="API Key">
                    <el-input
                      v-model.trim="llmConfigDraft.llm_api_key"
                      type="password"
                      autocomplete="new-password"
                      @copy.prevent="blockSensitiveCopy"
                      @cut.prevent="blockSensitiveCopy"
                      placeholder="输入 API Key"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
            <template #footer>
              <div class="ep-inline-actions">
                <el-button @click="llmConfigDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="saveLlmConfigDraft">保存并启用</el-button>
              </div>
            </template>
          </el-dialog>
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>
