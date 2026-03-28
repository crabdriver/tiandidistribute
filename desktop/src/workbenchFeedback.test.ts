import { describe, expect, it } from 'vitest'

import type { BridgeResources } from './types'
import { buildResourceHints, describeBrowserSessionSummary, describePublishResult } from './workbenchFeedback'

const resources: BridgeResources = {
  theme_pool: {
    themes_dir: 'themes',
    theme_ids: ['chinese'],
    count: 1,
    entries: [{ theme_id: 'chinese', display_name: 'Chinese' }],
  },
  cover_pool: {
    ok: false,
    cover_dir: '/tmp/covers',
    paths: [],
    count: 0,
    error: '封面目录为空',
  },
  config_warning: 'config.json 解析失败：Expecting property name enclosed in double quotes',
  wechat: {
    settings: { app_id: '', secret: '', author: '' },
    status: {
      env_file_exists: false,
      appid_ready: false,
      secret_ready: false,
      covers_ready: false,
      cover_count: 0,
      ai_cover_ready: false,
    },
  },
  browser: {
    browser_platforms: ['zhihu', 'toutiao', 'jianshu', 'yidian'],
    remote_debugging_required: true,
    login_required_platforms: ['zhihu', 'toutiao', 'jianshu', 'yidian'],
    managed_session: {
      enabled: true,
      remind_after_days: 5,
      profile_dir: '/tmp/ordo-profile',
      debug_port: 9333,
    },
    session_state: {
      mode: 'managed',
      last_checked_at: null,
      updated_at: null,
      platforms: {},
      expiring_platforms: [],
      relogin_required_platforms: [],
    },
  },
  runtime: {
    repo_root: '/mock/tiandidistribute',
    python_executable: 'python3',
  },
  defaults: {
    template_mode: 'default',
    cover_repeat_window: 8,
  },
}

describe('workbench feedback helpers', () => {
  it('builds actionable resource hints for selected platforms', () => {
    expect(buildResourceHints(resources, ['wechat', 'zhihu'])).toEqual([
      '微信发布前请先在设置里填写 AppID 和 Secret。',
      '浏览器平台发布前请先开启 Chrome 远程调试。',
      '浏览器平台发布前请先确认对应平台账号已登录。',
      '浏览器平台发布前请先把页面停留在对应平台的写作编辑器，而不是首页、登录页或内容管理页。',
      '非微信平台封面池未就绪，请把默认封面放到 /tmp/covers。',
      'config.json 解析失败：Expecting property name enclosed in double quotes',
    ])
  })

  it('builds browser session hints and summary for expiring or fallback state', () => {
    const variant: BridgeResources = {
      ...resources,
      browser: {
        ...resources.browser,
        session_state: {
          mode: 'fallback_system_browser',
          last_checked_at: '2026-03-28T12:00:00',
          updated_at: '2026-03-28T12:00:00',
          platforms: {
            zhihu: { status: 'expiring_soon' },
            toutiao: { status: 'expired_or_relogin_required' },
          },
          expiring_platforms: ['zhihu'],
          relogin_required_platforms: ['toutiao'],
        },
      },
    }

    expect(buildResourceHints(variant, ['zhihu', 'toutiao'])).toContain(
      '当前浏览器会话仍在回退系统 Chrome，尚未稳定使用 Ordo 托管浏览器。',
    )
    expect(buildResourceHints(variant, ['zhihu', 'toutiao'])).toContain(
      '浏览器会话已过久未校验，建议重新打开托管浏览器确认登录状态。',
    )
    expect(buildResourceHints(variant, ['zhihu', 'toutiao'])).toContain('头条号当前检测到需要重新登录。')
    expect(describeBrowserSessionSummary(variant)).toEqual({
      text: '浏览器会话需重登：头条号',
      tone: 'danger',
    })
  })

  it('formats publish result details for display', () => {
    expect(
      describePublishResult({
        platform: 'zhihu',
        status: 'failed',
        summary: 'network timeout',
        retryable: true,
      }),
    ).toContain('network timeout')
  })

  it('formats login and platform-changed failures with clearer guidance', () => {
    expect(
      describePublishResult({
        platform: 'zhihu',
        status: 'failed',
        summary: '需要登录后继续',
        error_type: 'login_required',
        retryable: false,
      }),
    ).toContain('需要重新登录')

    expect(
      describePublishResult({
        platform: 'toutiao',
        status: 'failed',
        summary: 'selector not found',
        error_type: 'platform_changed',
        retryable: false,
        current_url: 'https://mp.toutiao.com/profile_v4/graphic/publish',
        page_state: 'editor_ready',
        smoke_step: 'attempt_ai_declaration',
      }),
    ).toContain('页面结构可能已变更')

    expect(
      describePublishResult({
        platform: 'toutiao',
        status: 'failed',
        summary: 'selector not found',
        error_type: 'platform_changed',
        retryable: false,
        current_url: 'https://mp.toutiao.com/profile_v4/graphic/publish',
        page_state: 'editor_ready',
        smoke_step: 'attempt_ai_declaration',
      }),
    ).toContain('当前页面')
  })
})
