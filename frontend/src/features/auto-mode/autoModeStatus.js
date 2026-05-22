const STAGE_LABELS = {
  running_prepare: '正在准备任务',
  running_extract: '正在提取文档',
  running_mineru: '正在提取文档',
  preprocess_osd: '正在自动校正方向',
  running_rotate_retry: '正在尝试旋转重试',
  saving_history: '正在保存识别结果',
  running_submission_mapping: '正在生成填报草稿',
  running_customs_submit: '正在提交目标业务系统',
  done: '已完成',
  failed: '已失败',
}

function resolveStageLabel(stage) {
  return STAGE_LABELS[String(stage || '').trim()] || String(stage || '').trim() || '-'
}

export function buildAutoModeStatusView({ taskDetail, submissionMeta } = {}) {
  const task = taskDetail || {}
  const taskResult = task.result || {}
  const meta = submissionMeta || {}
  const enabled = Boolean(taskResult.auto_mode_enabled || meta.auto_mode_enabled)
  const status = String(taskResult.auto_mode_status || meta.submit_status || 'idle')
  const message = String(taskResult.auto_mode_message || meta.submit_message || '')
  const stageLabel = resolveStageLabel(task.stage)
  const progressText = Number.isFinite(Number(task.progress)) ? `${Math.max(0, Math.min(100, Number(task.progress)))}%` : '0%'
  const submitStatus = String(meta.submit_status || status || 'idle')
  const submitMessage = String(meta.submit_message || message || '')
  const submitEngine = String(meta.submit_engine || taskResult.submit_engine || '').trim()
  let title = message || `自动模式状态：${status}`
  let type = 'info'
  if (status === 'succeeded') {
    title = message || '自动填报完成'
    type = 'success'
  } else if (status === 'failed') {
    title = message || '自动填报失败'
    type = 'error'
  } else if (status === 'running') {
    title = '自动模式运行中'
  }

  const description = [
    `阶段：${stageLabel}`,
    `进度：${progressText}`,
    `填报状态：${submitStatus}`,
    `填报信息：${submitMessage || '-'}`,
    `提交模式：${submitEngine || '-'}`,
  ].join(' · ')

  return {
    enabled,
    status,
    title,
    type,
    description,
  }
}
