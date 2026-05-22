function toNumber(value, fallback = 0) {
  const num = Number(value)
  return Number.isFinite(num) && num >= 0 ? num : fallback
}

function toText(value, fallback = '') {
  const text = String(value ?? '').trim()
  return text || fallback
}

function normalizeRecentHistory(items) {
  if (!Array.isArray(items)) return []
  return items
    .filter((item) => item && typeof item === 'object')
    .slice(0, 8)
    .map((item) => ({
      id: toText(item.id),
      filename: toText(item.filename, '未命名资料'),
      vendor: toText(item.vendor, '-'),
      doc_type: toText(item.doc_type, '-'),
      created_at: toText(item.created_at),
      status: toText(item.status, 'idle'),
      review_label: toText(item.review_label, '未生成草稿'),
    }))
}

function buildRecommendations({ queue, templates, review, automation }) {
  const recommendations = []
  if (review.missing_fields > 0 || review.review_items > 0) {
    recommendations.push(`存在待复核资料：缺失 ${review.missing_fields} 项，复核 ${review.review_items} 项。`)
  }
  if (templates.vendor < templates.common) {
    recommendations.push('来源专属模板覆盖偏少，建议优先为高频客户沉淀专属模板。')
  }
  if (queue.failed > 0) {
    recommendations.push(`有 ${queue.failed} 个任务失败，建议先处理异常资料。`)
  }
  if (!automation.enabled) {
    recommendations.push('自动化流水线未开启，客户试点阶段建议先人工审核后再逐步开启。')
  }
  return recommendations.length > 0 ? recommendations : ['平台状态稳定，可继续扩大样本并沉淀模板规则。']
}

export function normalizePlatformInsights(payload = {}) {
  const queue = payload.queue && typeof payload.queue === 'object' ? payload.queue : {}
  const history = payload.history && typeof payload.history === 'object' ? payload.history : {}
  const templates = payload.templates && typeof payload.templates === 'object' ? payload.templates : {}
  const review = payload.review && typeof payload.review === 'object' ? payload.review : {}
  const automation = payload.automation && typeof payload.automation === 'object' ? payload.automation : {}
  const normalized = {
    generated_at: toText(payload.generated_at),
    queue: {
      queued: toNumber(queue.queued),
      running: toNumber(queue.running),
      failed: toNumber(queue.failed),
      succeeded: toNumber(queue.succeeded),
    },
    history: {
      total: toNumber(history.total),
      recent: normalizeRecentHistory(history.recent),
    },
    templates: {
      total: toNumber(templates.total),
      common: toNumber(templates.common),
      vendor: toNumber(templates.vendor),
      doc_types: Array.isArray(templates.doc_types)
        ? templates.doc_types.map((item) => toText(item)).filter(Boolean)
        : [],
    },
    review: {
      drafts_checked: toNumber(review.drafts_checked),
      drafts_with_warnings: toNumber(review.drafts_with_warnings),
      missing_fields: toNumber(review.missing_fields),
      review_items: toNumber(review.review_items),
    },
    automation: {
      enabled: Boolean(automation.enabled),
      submit_mode: toText(automation.submit_mode, 'http'),
      active_model: toText(automation.active_model, '-'),
    },
    recommendations: Array.isArray(payload.recommendations)
      ? payload.recommendations.map((item) => toText(item)).filter(Boolean).slice(0, 4)
      : [],
  }
  if (normalized.recommendations.length === 0) {
    normalized.recommendations = buildRecommendations(normalized).slice(0, 4)
  }
  return normalized
}

export function buildFallbackPlatformInsights({
  taskItems = [],
  historyItems = [],
  templateStats = {},
  submissionSummary = {},
  autoModeEnabled = false,
  customsSubmitMode = 'http',
  activeModel = '',
} = {}) {
  const queue = { queued: 0, running: 0, failed: 0, succeeded: 0 }
  for (const task of Array.isArray(taskItems) ? taskItems : []) {
    const status = toText(task?.status).toLowerCase()
    if (status in queue) queue[status] += 1
  }
  const missing = toNumber(submissionSummary.missingCount)
  const reviewItems = toNumber(submissionSummary.reviewCount)
  const templates = {
    total: toNumber(templateStats.common) + toNumber(templateStats.vendor),
    common: toNumber(templateStats.common),
    vendor: toNumber(templateStats.vendor),
    doc_types: [],
  }
  const review = {
    drafts_checked: toNumber(submissionSummary.detailCount) > 0 ? 1 : 0,
    drafts_with_warnings: missing + reviewItems > 0 ? 1 : 0,
    missing_fields: missing,
    review_items: reviewItems,
  }
  return normalizePlatformInsights({
    queue,
    history: {
      total: Array.isArray(historyItems) ? historyItems.length : 0,
      recent: normalizeRecentHistory(historyItems).map((item, index) => ({
        ...item,
        review_label: index === 0 && (missing + reviewItems > 0) ? `缺失 ${missing} / 复核 ${reviewItems}` : item.review_label,
      })),
    },
    templates,
    review,
    automation: {
      enabled: Boolean(autoModeEnabled),
      submit_mode: customsSubmitMode,
      active_model: activeModel,
    },
  })
}

export function buildInsightCards(insights) {
  const data = normalizePlatformInsights(insights)
  const activeQueue = data.queue.queued + data.queue.running
  const reviewLoad = data.review.missing_fields + data.review.review_items
  return [
    {
      label: '业务队列',
      value: activeQueue > 0 ? `${activeQueue} 个运行中` : `${data.queue.succeeded} 个已完成`,
      hint: data.queue.failed > 0 ? `${data.queue.failed} 个异常待处理` : '后台任务运行状态',
      tone: data.queue.failed > 0 ? 'warning' : (activeQueue > 0 ? 'info' : 'neutral'),
    },
    {
      label: '处理历史',
      value: `${data.history.total} 条历史`,
      hint: data.history.recent[0]?.filename || '暂无处理记录',
      tone: 'neutral',
    },
    {
      label: '模板覆盖',
      value: `${data.templates.common} 通用 / ${data.templates.vendor} 专属`,
      hint: data.templates.doc_types.length > 0 ? data.templates.doc_types.join('、') : '等待模板配置',
      tone: data.templates.vendor >= data.templates.common ? 'success' : 'info',
    },
    {
      label: '人审负载',
      value: reviewLoad > 0 ? `${reviewLoad} 项需复核` : '低风险',
      hint: `${data.review.drafts_checked} 份草稿已检查`,
      tone: reviewLoad > 0 ? 'warning' : 'success',
    },
    {
      label: '自动化',
      value: data.automation.enabled ? '自动流水线' : '人工接管',
      hint: `${data.automation.submit_mode} · ${data.automation.active_model}`,
      tone: data.automation.enabled ? 'success' : 'info',
    },
  ]
}
