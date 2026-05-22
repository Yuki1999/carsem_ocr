import { describe, expect, it } from 'vitest'

import {
  DOC_TYPES,
  FIXED_WORKSPACE_OCR_ENGINE,
  buildDocTypeOptionsForVendor,
  buildVendorOptions,
  chooseTemplateSelection,
  createInitialWorkspaceSelection,
  createTemplateDraftDefaults,
  normalizeVendorKey,
  resolveDocTypeForVendor,
} from './workspaceConfig'

describe('workspaceConfig helpers', () => {
  it('includes customs declaration as a selectable document type', () => {
    expect(DOC_TYPES).toContain('报关单')
  })

  it('does not inject a default vendor placeholder', () => {
    expect(buildVendorOptions([])).toEqual([])
    expect(buildVendorOptions([{ vendor: 'B' }, { vendor: 'A' }, { vendor: 'A' }])).toEqual(['A', 'B'])
    expect(buildVendorOptions([{ vendor: '通用模板' }, { vendor: 'A' }])).toEqual(['A'])
  })

  it('starts extraction workspace with no vendor selected and fixed qwen engine', () => {
    expect(createInitialWorkspaceSelection(['到货单', '发票'])).toEqual({
      vendor: '',
      docType: '',
      ocrEngine: FIXED_WORKSPACE_OCR_ENGINE,
    })
  })

  it('starts template draft as a common template', () => {
    expect(createTemplateDraftDefaults(['到货单', '发票'])).toEqual({
      vendor: '通用模板',
      scope: 'common',
      doc_type: '到货单',
    })
  })

  it('does not auto-select the first template when no vendor is selected', () => {
    expect(chooseTemplateSelection({
      templates: [
        { vendor: 'A', doc_type: '到货单' },
        { vendor: 'B', doc_type: '发票' },
      ],
      previousVendor: '',
      previousDocType: '发票',
      keepCurrentSelection: true,
      fallbackDocType: '到货单',
    })).toEqual({
      vendor: '',
      docType: '',
      matchedTemplate: null,
    })
  })

  it('limits doc type options to the selected vendor templates', () => {
    expect(buildDocTypeOptionsForVendor([
      { vendor: 'A', doc_type: '到货单' },
      { vendor: 'A', doc_type: '发票' },
      { vendor: 'B', doc_type: '物流通知书' },
    ], 'A')).toEqual(['到货单', '发票'])
    expect(buildDocTypeOptionsForVendor([
      { vendor: 'A', doc_type: '到货单' },
    ], '')).toEqual([])
  })

  it('uses common templates as document type fallbacks', () => {
    const items = [
      { vendor: '通用模板', doc_type: '发票' },
      { vendor: 'A', doc_type: '送货单' },
      { vendor: 'B', doc_type: '物流通知书' },
    ]

    expect(buildDocTypeOptionsForVendor(items, '')).toEqual(['发票'])
    expect(buildDocTypeOptionsForVendor(items, 'A')).toEqual(['发票', '送货单'])
  })

  it('falls back to common templates when a vendor has no dedicated template', () => {
    const commonInvoice = { vendor: '通用模板', doc_type: '发票' }
    const picked = chooseTemplateSelection({
      templates: [commonInvoice, { vendor: 'A', doc_type: '送货单' }],
      previousVendor: 'A',
      previousDocType: '发票',
      keepCurrentSelection: true,
    })

    expect(picked).toEqual({
      vendor: 'A',
      docType: '发票',
      matchedTemplate: commonInvoice,
    })
  })

  it('prefers vendor-specific templates over common templates for the same document type', () => {
    const commonInvoice = { vendor: '通用模板', doc_type: '发票' }
    const vendorInvoice = { vendor: 'A', doc_type: '发票' }
    const picked = chooseTemplateSelection({
      templates: [commonInvoice, vendorInvoice],
      previousVendor: 'A',
      previousDocType: '发票',
      keepCurrentSelection: true,
    })

    expect(picked.matchedTemplate).toBe(vendorInvoice)
    expect(picked.vendor).toBe('A')
    expect(picked.docType).toBe('发票')
  })

  it('matches ST vendor alias to STMicroelectronics templates', () => {
    expect(normalizeVendorKey('ST')).toBe('stmicroelectronics')
    expect(buildDocTypeOptionsForVendor([
      { vendor: 'STMicroelectronics', doc_type: '物流通知书' },
    ], 'ST')).toEqual(['物流通知书'])
    const picked = chooseTemplateSelection({
      templates: [{ vendor: 'STMicroelectronics', doc_type: '物流通知书' }],
      previousVendor: 'ST',
      previousDocType: '物流通知书',
      keepCurrentSelection: true,
    })
    expect(picked.matchedTemplate?.vendor).toBe('STMicroelectronics')
  })

  it('resolves doc type to the selected vendor available template types', () => {
    expect(resolveDocTypeForVendor([
      { vendor: 'STMicroelectronics', doc_type: '物流通知书' },
    ], 'ST', '到货单')).toBe('物流通知书')
    expect(resolveDocTypeForVendor([
      { vendor: 'STMicroelectronics', doc_type: '物流通知书' },
    ], 'ST', '物流通知书')).toBe('物流通知书')
    expect(resolveDocTypeForVendor([
      { vendor: 'STMicroelectronics', doc_type: '物流通知书' },
    ], 'ASE', '到货单')).toBe('')
  })
})
