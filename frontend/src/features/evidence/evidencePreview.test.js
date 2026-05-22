import { describe, expect, it } from 'vitest'

import { choosePreferredMarkdownPreview, isImageOnlyMarkdown } from './evidencePreview'

describe('isImageOnlyMarkdown', () => {
  it('detects markdown made only of image references', () => {
    expect(isImageOnlyMarkdown('![a](1.png)\n\n![b](2.png)')).toBe(true)
  })

  it('returns false when markdown contains text content', () => {
    expect(isImageOnlyMarkdown('![a](1.png)\n\nInvoice No: 123')).toBe(false)
  })
})

describe('choosePreferredMarkdownPreview', () => {
  it('prefers fallback text for opendataloader image-only markdown', () => {
    const picked = choosePreferredMarkdownPreview({
      ocrEngine: 'opendataloader',
      markdownContent: '![a](1.png)\n\n![b](2.png)',
      fallbackText: 'OCR text content',
    })

    expect(picked).toBe('OCR text content')
  })

  it('keeps markdown when it contains textual content', () => {
    const picked = choosePreferredMarkdownPreview({
      ocrEngine: 'opendataloader',
      markdownContent: 'Invoice No: 123',
      fallbackText: 'OCR text content',
    })

    expect(picked).toBe('Invoice No: 123')
  })
})
