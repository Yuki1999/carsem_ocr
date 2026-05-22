function hasText(value) {
  return String(value ?? '').trim().length > 0
}

function isMissingTemplateName(templateName) {
  const name = String(templateName || '').trim()
  return !name || name === '未选择模板'
}

function stringifyRawValue(value) {
  if (value == null) return ''
  if (typeof value === 'string') return value.trim()
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function hasDetectedValue(value, displayValue = '') {
  if (Array.isArray(value)) return value.length > 0
  if (value && typeof value === 'object') return Object.keys(value).length > 0
  if (hasText(value)) return true
  return hasText(displayValue)
}

export function buildExtractionLaunchReview(options = {}) {
  const fileName = String(options.fileName || '').trim()
  const templateName = String(options.templateName || '').trim()
  const promptText = String(options.promptText || '').trim()
  const fieldCount = Number(options.fieldCount || 0)
  const autoModeEnabled = Boolean(options.autoModeEnabled)

  const fileReady = hasText(fileName)
  const templateReady = !isMissingTemplateName(templateName) && fieldCount > 0
  const promptReady = hasText(promptText)
  const items = [
    {
      key: 'file',
      title: '上传文件',
      status: fileReady ? 'success' : 'error',
      description: fileReady ? fileName : '需要先选择要识别的文件',
    },
    {
      key: 'template',
      title: '识别模板',
      status: templateReady ? 'success' : 'error',
      description: templateReady ? `${templateName}，${fieldCount} 个字段` : '需要选择包含字段的模板',
    },
    {
      key: 'prompt',
      title: '提取提示词',
      status: promptReady ? 'success' : 'error',
      description: promptReady ? '已准备输出结构和字段说明' : '需要填写大模型提取提示词',
    },
    {
      key: 'mode',
      title: '运行模式',
      status: autoModeEnabled ? 'warning' : 'info',
      description: autoModeEnabled ? '自动模式会继续生成草稿并尝试填报' : '人工模式会停在结果中心等待复核',
    },
  ]
  const blockerCount = items.filter((item) => ['file', 'template', 'prompt'].includes(item.key) && item.status !== 'success').length
  return {
    ready: blockerCount === 0,
    blockerCount,
    primaryLabel: blockerCount === 0 ? '确认并开始' : '补齐后开始',
    modeLabel: autoModeEnabled ? '自动流水线' : '人工接管',
    items,
  }
}

export function buildFieldDetailView(row = {}) {
  const title = String(row.key || '字段详情').trim() || '字段详情'
  const raw = row.raw
  const valueText = String(row.value || stringifyRawValue(raw) || '-')
  const rawText = stringifyRawValue(raw) || valueText
  const isStructured = Boolean(raw && typeof raw === 'object')
  const detected = hasDetectedValue(raw, valueText)
  return {
    title,
    statusLabel: detected ? '已命中' : '未识别',
    statusType: detected ? 'success' : 'info',
    valueText,
    rawText,
    isStructured,
  }
}
