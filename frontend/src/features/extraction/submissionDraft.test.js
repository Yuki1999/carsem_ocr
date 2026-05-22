import { describe, expect, it } from 'vitest'
import {
  appendDraftDetailRow,
  buildDraftSummary,
  createEmptySubmissionDraft,
  normalizeSubmissionDraft,
  removeDraftDetailRow,
  updateDraftDetailField,
  updateDraftHeaderField,
} from './submissionDraft'

describe('buildDraftSummary', () => {
  it('counts missing required fields', () => {
    const summary = buildDraftSummary({
      header: { Mawb: '-1', CustomerName: '嘉盛' },
      details: [{ ItemCode: 'A1', ItemOrigin: '-1', ItemQuantity: '10', ItemGoodQuantity: '10', ItemPrice: '20', ItemUnitPrice: '2' }],
      meta: { required_missing: ['details[0].ItemOrigin', 'details[0].ItemPrice'] },
    })

    expect(summary.missingCount).toBe(2)
  })

  it('counts packet review items', () => {
    const summary = buildDraftSummary({
      meta: {
        packet: {
          field_reviews: [{ field: 'CustomerName', review_required: true }],
          detail_reviews: [
            { detail_index: 0, quantity_check: 'matched', review_required: false },
            { detail_index: 1, quantity_check: 'mismatch', review_required: true },
          ],
        },
      },
    })

    expect(summary.reviewCount).toBe(2)
  })

  it('exposes warning state for missing or review items', () => {
    expect(buildDraftSummary({ meta: { required_missing: ['CustomerName'] } }).hasReviewWarnings).toBe(true)
    expect(buildDraftSummary({ meta: { packet: { detail_reviews: [{ review_required: true }] } } }).hasReviewWarnings).toBe(true)
    expect(buildDraftSummary({ meta: { required_missing: [], packet: { detail_reviews: [] } } }).hasReviewWarnings).toBe(false)
  })
})

describe('draft edits', () => {
  it('updates a header field immutably', () => {
    const draft = createEmptySubmissionDraft()
    const next = updateDraftHeaderField(draft, 'Mawb', 'MBL001')

    expect(next.header.Mawb).toBe('MBL001')
    expect(draft.header.Mawb).toBe('-1')
  })

  it('updates the correct detail row', () => {
    const draft = appendDraftDetailRow(appendDraftDetailRow(createEmptySubmissionDraft()))
    const next = updateDraftDetailField(draft, 1, 'ItemCode', 'A-2')

    expect(next.details[1].ItemCode).toBe('A-2')
    expect(next.details[0].ItemCode).toBe('-1')
  })

  it('removes the target detail row', () => {
    const first = updateDraftDetailField(appendDraftDetailRow(createEmptySubmissionDraft()), 0, 'ItemCode', 'A-1')
    const second = updateDraftDetailField(appendDraftDetailRow(first), 1, 'ItemCode', 'A-2')
    const next = removeDraftDetailRow(second, 0)

    expect(next.details).toHaveLength(2)
    expect(next.details[0].ItemCode).toBe('A-2')
    expect(next.details[1].ItemCode).toBe('-1')
  })

  it('defaults header and detail fields to -1', () => {
    const draft = createEmptySubmissionDraft()

    expect(draft.header.Mawb).toBe('-1')
    expect(draft.header.Hawb).toBe('-1')
    expect(appendDraftDetailRow(draft).details[0].ItemCode).toBe('-1')
  })

  it('normalizes legacy MainBLNo and SubBLNo fields into Mawb and Hawb', () => {
    const normalized = normalizeSubmissionDraft({
      header: { MainBLNo: 'MBL001', SubBLNo: 'HBL001', CustomerName: '嘉盛' },
      details: [],
      meta: {},
    })

    expect(normalized.header.Mawb).toBe('MBL001')
    expect(normalized.header.Hawb).toBe('HBL001')
  })

  it('preserves packet metadata for manual review', () => {
    const normalized = normalizeSubmissionDraft({
      meta: {
        packet: {
          packet_id: 'DS12650253',
          header_candidates: {
            CustomerName: {
              recommended: '推荐客户',
              candidates: [{ source: 'invoice', value: '推荐客户' }],
              review_required: true,
            },
          },
          detail_reviews: [{ detail_index: 0, quantity_check: 'mismatch', review_required: true }],
        },
      },
    })

    expect(normalized.meta.packet.packet_id).toBe('DS12650253')
    expect(normalized.meta.packet.header_candidates.CustomerName.recommended).toBe('推荐客户')
    expect(normalized.meta.packet.detail_reviews[0].quantity_check).toBe('mismatch')
  })
})
