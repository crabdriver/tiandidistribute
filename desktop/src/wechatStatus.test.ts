import { describe, expect, it } from 'vitest'

import { buildWechatBlockingMessage, describeWechatStatus } from './wechatStatus'

describe('wechat status helpers', () => {
  it('formats ready and pending status labels', () => {
    expect(
      describeWechatStatus({
        env_file_exists: false,
        appid_ready: false,
        secret_ready: false,
        covers_ready: false,
        cover_count: 0,
        ai_cover_ready: false,
      }),
    ).toBe('微信配置未完成')

    expect(
      describeWechatStatus({
        env_file_exists: true,
        appid_ready: true,
        secret_ready: true,
        covers_ready: false,
        cover_count: 0,
        ai_cover_ready: false,
      }),
    ).toBe('微信配置已就绪')
  })

  it('builds blocking message only when wechat is selected but credentials are missing', () => {
    expect(
      buildWechatBlockingMessage(
        ['wechat', 'zhihu'],
        {
          env_file_exists: false,
          appid_ready: false,
          secret_ready: true,
          covers_ready: false,
          cover_count: 0,
          ai_cover_ready: false,
        },
      ),
    ).toContain('先在设置里填写微信 AppID 和 Secret')

    expect(
      buildWechatBlockingMessage(
        ['zhihu'],
        {
          env_file_exists: false,
          appid_ready: false,
          secret_ready: false,
          covers_ready: false,
          cover_count: 0,
          ai_cover_ready: false,
        },
      ),
    ).toBe('')
  })
})
