import { describe, expect, it } from 'vitest'

import { shouldPersistAutoModeChange } from './autoModePersistence'
import { loadLlmSettings, buildLlmSettingsPayloadForTest } from '../settings/llmSettings'

describe('shouldPersistAutoModeChange', () => {
  it('persists when the toggle value changes after settings are ready', () => {
    expect(shouldPersistAutoModeChange({
      previousValue: false,
      nextValue: true,
      loading: false,
      hasActiveConfig: true,
      initialized: true,
    })).toBe(true)
  })

  it('does not persist during initial load', () => {
    expect(shouldPersistAutoModeChange({
      previousValue: false,
      nextValue: true,
      loading: true,
      hasActiveConfig: true,
      initialized: false,
    })).toBe(false)
  })

  it('does not persist when the value did not change', () => {
    expect(shouldPersistAutoModeChange({
      previousValue: true,
      nextValue: true,
      loading: false,
      hasActiveConfig: true,
      initialized: true,
    })).toBe(false)
  })

  it('preserves customs submit mode through load and save helpers', () => {
    const settings = loadLlmSettings({
      active_id: 'cfg-1',
      auto_mode_enabled: true,
      customs_submit_mode: 'playwright',
      items: [
        {
          id: 'cfg-1',
          name: 'Gemini 默认',
          provider: 'gemini',
          llm_base_url: 'https://example.com/v1',
          llm_model: 'demo-model',
          llm_api_key: 'secret',
        },
      ],
    })

    const payload = buildLlmSettingsPayloadForTest({
      items: settings.items,
      active_id: settings.active_id,
      auto_mode_enabled: settings.auto_mode_enabled,
      customs_submit_mode: settings.customs_submit_mode,
    })

    expect(settings.customs_submit_mode).toBe('playwright')
    expect(payload.customs_submit_mode).toBe('playwright')
  })

  it('falls back to http when loading removed local agent mode', () => {
    const settings = loadLlmSettings({
      active_id: 'cfg-1',
      auto_mode_enabled: true,
      customs_submit_mode: 'local_agent',
      local_agent_id: 'sz-ops-01',
      items: [
        {
          id: 'cfg-1',
          name: 'Gemini 默认',
          provider: 'gemini',
          llm_base_url: 'https://example.com/v1',
          llm_model: 'demo-model',
          llm_api_key: 'secret',
        },
      ],
    })

    const payload = buildLlmSettingsPayloadForTest({
      items: settings.items,
      active_id: settings.active_id,
      auto_mode_enabled: settings.auto_mode_enabled,
      customs_submit_mode: settings.customs_submit_mode,
    })

    expect(settings.customs_submit_mode).toBe('http')
    expect(payload.customs_submit_mode).toBe('http')
    expect(Object.hasOwn(payload, 'local_agent_id')).toBe(false)
  })

  it('recognizes bailian settings as a first-class provider', () => {
    const settings = loadLlmSettings({
      active_id: 'cfg-1',
      items: [
        {
          id: 'cfg-1',
          name: '百炼 Qwen',
          llm_base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
          llm_model: 'qwen3.5-plus',
          llm_api_key: 'secret',
        },
      ],
    })

    expect(settings.items[0].provider).toBe('bailian')
    expect(settings.items[0].llm_base_url).toBe('https://dashscope.aliyuncs.com/compatible-mode/v1')
    expect(settings.items[0].llm_model).toBe('qwen3.5-plus')
  })
})
