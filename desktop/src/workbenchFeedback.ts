import type { BridgeResources, Platform } from './types'

export function buildResourceHints(resources: BridgeResources | null, platforms: Platform[]): string[] {
  if (!resources) {
    return []
  }

  const hints: string[] = []
  if (platforms.includes('wechat')) {
    const status = resources.wechat.status
    if (!status.appid_ready || !status.secret_ready) {
      hints.push('微信发布前请先在设置里填写 AppID 和 Secret。')
    }
  }

  const needsCoverPool = platforms.some((platform) => platform !== 'wechat')
  if (needsCoverPool && !resources.cover_pool.ok) {
    hints.push(`非微信平台封面池未就绪，请把默认封面放到 ${resources.cover_pool.cover_dir}。`)
  }

  return hints
}

export function describePublishResult(result: Record<string, unknown>): string {
  const summary = String(result.summary ?? result.stderr ?? result.stdout ?? '').trim()
  const status = String(result.status ?? 'unknown')
  const retryable = Boolean(result.retryable)
  const suffix = retryable ? ' · 可重试' : ''
  return summary ? `${status} · ${summary}${suffix}` : `${status}${suffix}`
}
