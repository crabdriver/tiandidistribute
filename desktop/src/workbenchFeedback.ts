import type { BridgeResources, Platform } from './types'

const BROWSER_LABELS: Record<Platform, string> = {
  wechat: '微信',
  zhihu: '知乎',
  toutiao: '头条号',
  jianshu: '简书',
  yidian: '一点号',
}

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

  const browserPlatforms = platforms.filter((platform) => resources.browser.browser_platforms.includes(platform))
  if (browserPlatforms.length > 0 && resources.browser.remote_debugging_required) {
    hints.push('浏览器平台发布前请先开启 Chrome 远程调试。')
  }
  const loginRequired = browserPlatforms.filter((platform) => resources.browser.login_required_platforms.includes(platform))
  if (loginRequired.length > 0) {
    hints.push('浏览器平台发布前请先确认对应平台账号已登录。')
  }

  const needsCoverPool = platforms.some((platform) => platform !== 'wechat')
  if (needsCoverPool && !resources.cover_pool.ok) {
    hints.push(`非微信平台封面池未就绪，请把默认封面放到 ${resources.cover_pool.cover_dir}。`)
  }

  return hints
}

export function describePublishResult(result: Record<string, unknown>): string {
  const errorType = String(result.error_type ?? '')
  const summary = String(result.summary ?? result.stderr ?? result.stdout ?? '').trim()
  const status = String(result.status ?? 'unknown')
  const retryable = Boolean(result.retryable)
  const suffix = retryable ? ' · 可重试' : ''
  const detail = describeFailureDetail(errorType, summary, result.platform)
  return detail ? `${status} · ${detail}${suffix}` : `${status}${suffix}`
}

function describeFailureDetail(errorType: string, summary: string, platform: unknown): string {
  if (errorType === 'login_required') {
    const label = BROWSER_LABELS[(platform as Platform | undefined) ?? 'zhihu'] ?? '对应平台'
    return `${label}需要重新登录后再试。${summary ? ` ${summary}` : ''}`.trim()
  }
  if (errorType === 'platform_changed') {
    return `页面结构可能已变更，请检查平台编辑器或更新脚本。${summary ? ` ${summary}` : ''}`.trim()
  }
  if (errorType === 'environment_error') {
    return `本机发布环境未就绪。${summary ? ` ${summary}` : ''}`.trim()
  }
  return summary
}
