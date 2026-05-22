import { describe, expect, it } from 'vitest'
import {
  classifyEvidenceFile,
  chooseDefaultEvidenceTab,
  pickPrimaryMarkdownFile,
  pickPrimaryOriginalFile,
  resolveOriginalPreviewFile,
} from './historyEvidence'

describe('pickPrimaryOriginalFile', () => {
  it('prefers the user uploaded source pdf over corrected preview pdf', () => {
    const picked = pickPrimaryOriginalFile([
      { path: 'abc_origin.pdf', mime: 'application/pdf' },
      { path: 'preview/final_selected.pdf', mime: 'application/pdf' },
      { path: 'images/page-1.jpg', is_image: true },
    ])

    expect(picked?.path).toBe('abc_origin.pdf')
  })

  it('prefers the source pdf over derived assets', () => {
    const picked = pickPrimaryOriginalFile([
      { path: 'images/page-1.jpg', is_image: true },
      { path: 'abc_origin.pdf', mime: 'application/pdf' },
      { path: 'full.md', is_text: true },
    ])

    expect(picked?.path).toBe('abc_origin.pdf')
  })
})

describe('chooseDefaultEvidenceTab', () => {
  it('opens original preview first when a source pdf exists', () => {
    const tab = chooseDefaultEvidenceTab({
      files: [{ path: 'abc_origin.pdf', mime: 'application/pdf' }],
      hasMarkdownPreview: true,
    })

    expect(tab).toBe('original')
  })

  it('falls back to markdown when no previewable original file exists', () => {
    const tab = chooseDefaultEvidenceTab({
      files: [{ path: 'layout.json', is_text: true }],
      hasMarkdownPreview: true,
    })

    expect(tab).toBe('markdown')
  })
})

describe('resolveOriginalPreviewFile', () => {
  it('keeps showing the primary original pdf instead of a selected derived png', () => {
    const resolved = resolveOriginalPreviewFile(
      { path: 'images/page-1.png', is_image: true },
      { path: 'abc_origin.pdf', mime: 'application/pdf' },
    )

    expect(resolved?.path).toBe('abc_origin.pdf')
  })
})

describe('classifyEvidenceFile', () => {
  it('marks office documents as download-only', () => {
    expect(classifyEvidenceFile({ path: 'notice.docx' })).toBe('download')
  })
})

describe('pickPrimaryMarkdownFile', () => {
  it('prefers full.md when present', () => {
    const picked = pickPrimaryMarkdownFile([
      { path: 'opendataloader/input.md', is_text: true },
      { path: 'full.md', is_text: true },
    ])

    expect(picked?.path).toBe('full.md')
  })

  it('falls back to opendataloader markdown when full.md is absent', () => {
    const picked = pickPrimaryMarkdownFile([
      { path: 'opendataloader/input.json', is_text: true },
      { path: 'opendataloader/input.md', is_text: true },
      { path: 'opendataloader/input.txt', is_text: true },
    ])

    expect(picked?.path).toBe('opendataloader/input.md')
  })
})
