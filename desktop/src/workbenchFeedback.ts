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
  if (browserPlatforms.length > 0 && resources.browser.managed_session.enabled && resources.browser.session_state.mode !== 'managed') {
    hints.push('当前浏览器会话仍在回退系统 Chrome，尚未稳定使用 Ordo 托管浏览器。')
  }
  const loginRequired = browserPlatforms.filter((platform) => resources.browser.login_required_platforms.includes(platform))
  if (loginRequired.length > 0) {
    hints.push('浏览器平台发布前请先确认对应平台账号已登录。')
    hints.push('浏览器平台发布前请先把页面停留在对应平台的写作编辑器，而不是首页、登录页或内容管理页。')
  }
  if (resources.browser.session_state.expiring_platforms.length > 0) {
    hints.push('浏览器会话已过久未校验，建议重新打开托管浏览器确认登录状态。')
  }
  if (resources.browser.session_state.relogin_required_platforms.length > 0) {
    hints.push(`${platformLabels(resources.browser.session_state.relogin_required_platforms)}当前检测到需要重新登录。`)
  }

  const needsCoverPool = platforms.some((platform) => platform !== 'wechat')
  if (needsCoverPool && !resources.cover_pool.ok) {
    hints.push(`非微信平台封面池未就绪，请把默认封面放到 ${resources.cover_pool.cover_dir}。`)
  }
  if (resources.config_warning) {
    hints.push(resources.config_warning)
  }

  return hints
}

export function describeBrowserSessionSummary(
  resources: BridgeResources | null,
): { text: string; tone: 'ready' | 'pending' | 'danger' } {
  if (!resources) {
    return { text: '浏览器会话未加载', tone: 'pending' }
  }
  const managed = resources.browser.managed_session
  const session = resources.browser.session_state
  if (session.relogin_required_platforms.length > 0) {
    return {
      text: `浏览器会话需重登：${platformLabels(session.relogin_required_platforms)}`,
      tone: 'danger',
    }
  }
  if (session.expiring_platforms.length > 0) {
    return {
      text: `浏览器会话临近失效：${platformLabels(session.expiring_platforms)}`,
      tone: 'pending',
    }
  }
  if (managed.enabled && session.mode === 'managed') {
    return {
      text: `浏览器会话已托管 · 端口 ${managed.debug_port}`,
      tone: 'ready',
    }
  }
  if (managed.enabled) {
    return {
      text: '浏览器会话已回退到系统 Chrome',
      tone: 'pending',
    }
  }
  return {
    text: '浏览器会话使用系统 Chrome',
    tone: 'pending',
  }
}

export function describePublishResult(result: Record<string, unknown>): string {
  const errorType = String(result.error_type ?? '')
  const summary = String(result.summary ?? result.stderr ?? result.stdout ?? '').trim()
  const status = String(result.status ?? 'unknown')
  const retryable = Boolean(result.retryable)
  const suffix = retryable ? ' · 可重试' : ''
  const detail = describeFailureDetail(errorType, summary, result)
  return detail ? `${status} · ${detail}${suffix}` : `${status}${suffix}`
}

function describeFailureDetail(errorType: string, summary: string, result: Record<string, unknown>): string {
  const context = buildFailureContext(result)
  if (errorType === 'login_required') {
    const label = BROWSER_LABELS[(result.platform as Platform | undefined) ?? 'zhihu'] ?? '对应平台'
    return `${label}需要重新登录后再试。${summary ? ` ${summary}` : ''}${context ? ` ${context}` : ''}`.trim()
  }
  if (errorType === 'platform_changed') {
    return `页面结构可能已变更，请检查平台编辑器或更新脚本。${summary ? ` ${summary}` : ''}${context ? ` ${context}` : ''}`.trim()
  }
  if (errorType === 'environment_error') {
    return `本机发布环境未就绪。${summary ? ` ${summary}` : ''}${context ? ` ${context}` : ''}`.trim()
  }
  return `${summary}${context ? ` ${context}` : ''}`.trim()
}

function buildFailureContext(result: Record<string, unknown>): string {
  const currentUrl = String(result.current_url ?? '').trim()
  const pageState = String(result.page_state ?? '').trim()
  const smokeStep = String(result.smoke_step ?? '').trim()
  const parts: string[] = []
  if (currentUrl) {
    parts.push(`当前页面：${currentUrl}`)
  }
  if (smokeStep) {
    parts.push(`阶段：${smokeStep}`)
  }
  if (pageState) {
    parts.push(`页面状态：${pageState}`)
  }
  return parts.join('；')
}

function platformLabels(platforms: Platform[]): string {
  return platforms.map((platform) => BROWSER_LABELS[platform] ?? platform).join(' / ')
}
