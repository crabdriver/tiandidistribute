import { describe, expect, it } from 'vitest'

import { compactHistoryPayload, compactPublishResult, truncateLogText } from './publishResultMemory'
import type { HistoryPayload, PublishResult } from './types'

describe('publish result memory helpers', () => {
  it('truncates oversized log text with a marker', () => {
    const text = 'x'.repeat(2200)
    const truncated = truncateLogText(text, 120)

    if (!truncated) {
      throw new Error('expected truncated text')
    }
    expect(truncated.length).toBeLessThanOrEqual(120)
    expect(truncated.endsWith('...[truncated]')).toBe(true)
  })

  it('drops streamed events and compacts per-platform stdout and stderr', () => {
    const result: PublishResult = {
      publish_job: {
        job_id: 'job-1',
        article_ids: ['a1'],
        platforms: ['wechat'],
        status: 'completed',
        current_step: 'done',
        success_count: 1,
        failure_count: 0,
        skip_count: 0,
        recoverable: true,
        error_summary: '',
        scheduled_publish_at: null,
      },
      events: [
        { type: 'job_started', job_id: 'job-1' },
        { type: 'job_finished', job_id: 'job-1' },
      ],
      results: [
        {
          article_id: 'a1',
          platform: 'wechat',
          status: 'draft_only',
          returncode: 0,
          retryable: false,
          stdout: 's'.repeat(3000),
          stderr: 'e'.repeat(3000),
          current_url: '',
          page_state: '',
          smoke_step: '',
          summary: 'ok',
        },
      ],
    }

    const compacted = compactPublishResult(result, 160)
    const compactedItem = compacted.results[0] as Record<string, unknown>

    expect(compacted.publish_job).toEqual(result.publish_job)
    expect(compacted.events).toEqual([])
    expect(typeof compactedItem.stdout).toBe('string')
    expect(typeof compactedItem.stderr).toBe('string')
    expect((compactedItem.stdout as string).length).toBeLessThanOrEqual(160)
    expect((compactedItem.stderr as string).length).toBeLessThanOrEqual(160)
    expect(compactedItem.summary).toBe('ok')
  })

  it('compacts history last_result without touching other history fields', () => {
    const payload: HistoryPayload = {
      records: [],
      session: { ok: true },
      last_plan: null,
      last_result: {
        publish_job: {
          job_id: 'job-2',
          article_ids: ['a2'],
          platforms: ['wechat'],
          status: 'completed',
          current_step: 'done',
          success_count: 1,
          failure_count: 0,
          skip_count: 0,
          recoverable: true,
          error_summary: '',
          scheduled_publish_at: null,
        },
        events: [{ type: 'job_finished', job_id: 'job-2' }],
        results: [{ stdout: 'x'.repeat(400), stderr: 'y'.repeat(400) }],
      },
      recovery: {
        status: 'recoverable',
        issues: [],
        missing_staged_articles: [],
        can_restore_plan: true,
        can_restore_failures: false,
      },
    }

    const compacted = compactHistoryPayload(payload, 80)
    const compactedResult = compacted.last_result!
    const compactedHistoryItem = compactedResult.results[0] as Record<string, unknown>

    expect(compacted.session).toEqual(payload.session)
    expect(compacted.records).toEqual(payload.records)
    expect(compactedResult.events).toEqual([])
    expect((compactedHistoryItem.stdout as string).length).toBeLessThanOrEqual(80)
    expect((compactedHistoryItem.stderr as string).length).toBeLessThanOrEqual(80)
  })
})
