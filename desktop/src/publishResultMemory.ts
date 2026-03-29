import type { HistoryPayload, PublishResult } from './types'

const DEFAULT_LOG_LIMIT = 1600
const TRUNCATED_MARKER = '...[truncated]'

export function truncateLogText(value: string | undefined, limit = DEFAULT_LOG_LIMIT): string | undefined {
  if (typeof value !== 'string' || value.length <= limit) {
    return value
  }
  return `${value.slice(0, Math.max(0, limit - TRUNCATED_MARKER.length))}${TRUNCATED_MARKER}`
}

function readStringField(item: Record<string, unknown>, key: string): string | undefined {
  const value = item[key]
  return typeof value === 'string' ? value : undefined
}

export function compactPublishResult(result: PublishResult, limit = DEFAULT_LOG_LIMIT): PublishResult {
  return {
    ...result,
    events: [],
    results: result.results.map((item): Record<string, unknown> => ({
      ...item,
      stdout: truncateLogText(readStringField(item, 'stdout'), limit),
      stderr: truncateLogText(readStringField(item, 'stderr'), limit),
    })),
  }
}

export function compactHistoryPayload(payload: HistoryPayload, limit = DEFAULT_LOG_LIMIT): HistoryPayload {
  return {
    ...payload,
    last_result: payload.last_result ? compactPublishResult(payload.last_result, limit) : null,
  }
}
