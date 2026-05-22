import { describe, expect, it } from 'vitest'

import { buildAutoModeStatusView } from './autoModeStatus'

describe('buildAutoModeStatusView', () => {
  it('includes task stage progress and customs submission result for active auto mode', () => {
    const view = buildAutoModeStatusView({
      taskDetail: {
        stage: 'running_customs_submit',
        progress: 97,
        message: '正在自动填报报关系统',
        result: {
          auto_mode_enabled: true,
          auto_mode_status: 'running',
          auto_mode_message: '正在自动填报报关系统',
        },
      },
      submissionMeta: {
        submit_status: 'running',
        submit_message: '正在自动填报报关系统',
      },
    })

    expect(view.enabled).toBe(true)
    expect(view.title).toBe('自动模式运行中')
    expect(view.type).toBe('info')
    expect(view.description).toContain('阶段：正在提交进口报关系统')
    expect(view.description).toContain('进度：97%')
    expect(view.description).toContain('填报状态：running')
    expect(view.description).toContain('填报信息：正在自动填报报关系统')
  })

  it('prefers final success message when auto mode has completed', () => {
    const view = buildAutoModeStatusView({
      taskDetail: {
        stage: 'done',
        progress: 100,
        message: '提取完成',
        result: {
          auto_mode_enabled: true,
          auto_mode_status: 'succeeded',
          auto_mode_message: '自动填报完成',
        },
      },
      submissionMeta: {
        submit_status: 'succeeded',
        submit_message: '自动填报完成',
      },
    })

    expect(view.title).toBe('自动填报完成')
    expect(view.type).toBe('success')
    expect(view.description).toContain('阶段：已完成')
    expect(view.description).toContain('填报状态：succeeded')
  })

  it('includes the submit engine when metadata provides it', () => {
    const view = buildAutoModeStatusView({
      taskDetail: {
        stage: 'done',
        progress: 100,
        result: {
          auto_mode_enabled: true,
          auto_mode_status: 'succeeded',
          auto_mode_message: '自动填报完成',
        },
      },
      submissionMeta: {
        submit_status: 'succeeded',
        submit_message: '自动填报完成',
        submit_engine: 'playwright',
      },
    })

    expect(view.description).toContain('提交模式：playwright')
  })

  it('shows friendly label for rotation retry stage', () => {
    const view = buildAutoModeStatusView({
      taskDetail: {
        stage: 'running_rotate_retry',
        progress: 60,
        result: {
          auto_mode_enabled: true,
          auto_mode_status: 'running',
        },
      },
      submissionMeta: {
        submit_status: 'idle',
      },
    })

    expect(view.description).toContain('阶段：正在尝试旋转重试')
    expect(view.description).toContain('进度：60%')
  })
})
