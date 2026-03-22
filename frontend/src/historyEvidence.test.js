import { describe, expect, it } from 'vitest'
import {
  classifyEvidenceFile,
  chooseDefaultEvidenceTab,
  pickPrimaryOriginalFile,
} from './historyEvidence'

describe('pickPrimaryOriginalFile', () => {
  it('prefers the corrected preview pdf over source pdf', () => {
    const picked = pickPrimaryOriginalFile([
      { path: 'abc_origin.pdf', mime: 'application/pdf' },
      { path: 'preview/final_selected.pdf', mime: 'application/pdf' },
      { path: 'images/page-1.jpg', is_image: true },
    ])

    expect(picked?.path).toBe('preview/final_selected.pdf')
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

describe('classifyEvidenceFile', () => {
  it('marks office documents as download-only', () => {
    expect(classifyEvidenceFile({ path: 'notice.docx' })).toBe('download')
  })
})
