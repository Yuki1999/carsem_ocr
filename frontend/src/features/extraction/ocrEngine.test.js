import { describe, expect, it } from 'vitest'

import {
  DEFAULT_OCR_ENGINE,
  EXTRACT_UPLOAD_ACCEPT,
  buildExtractRequestFields,
  normalizeOcrEngine,
  normalizeTemplateOcrEngine,
} from './ocrEngine'

describe('ocrEngine helpers', () => {
  it('defaults to mineru', () => {
    expect(DEFAULT_OCR_ENGINE).toBe('mineru')
    expect(normalizeOcrEngine('')).toBe('mineru')
    expect(normalizeOcrEngine('MinerU')).toBe('mineru')
  })

  it('preserves opendataloader in template normalization', () => {
    expect(normalizeTemplateOcrEngine({ ocr_engine: 'opendataloader' })).toBe('opendataloader')
    expect(normalizeTemplateOcrEngine({ ocr_engine: 'qwen_vision' })).toBe('qwen_vision')
    expect(normalizeTemplateOcrEngine({})).toBe('mineru')
  })

  it('includes selected ocr_engine in request fields', () => {
    const pairs = buildExtractRequestFields({
      vendor: 'Vendor A',
      doc_type: '发票',
      llm_prompt: '提取发票号',
      llm_base_url: 'https://example.com/v1',
      llm_model: 'demo-model',
      llm_api_key: 'secret',
      region_rules: '',
      backend: 'vlm',
      parse_method: 'auto',
      lang_list: 'en',
      ocr_engine: 'qwen_vision',
    })

    expect(pairs).toContainEqual(['ocr_engine', 'qwen_vision'])
    expect(pairs).toContainEqual(['backend', 'vlm'])
  })

  it('normalizes qwen_vision', () => {
    expect(normalizeOcrEngine('qwen_vision')).toBe('qwen_vision')
  })

  it('accepts xlsx files in the extraction uploader', () => {
    expect(EXTRACT_UPLOAD_ACCEPT.split(',')).toContain('.xlsx')
  })
})
