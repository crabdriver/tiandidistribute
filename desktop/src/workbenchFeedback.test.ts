import { describe, expect, it } from 'vitest'

import type { BridgeResources } from './types'
import { buildResourceHints, describePublishResult } from './workbenchFeedback'

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
  defaults: {
    template_mode: 'default',
    cover_repeat_window: 8,
  },
}

describe('workbench feedback helpers', () => {
  it('builds actionable resource hints for selected platforms', () => {
    expect(buildResourceHints(resources, ['wechat', 'zhihu'])).toEqual([
      '微信发布前请先在设置里填写 AppID 和 Secret。',
      '非微信平台封面池未就绪，请把默认封面放到 /tmp/covers。',
    ])
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
})
