import { describe, expect, it } from 'vitest'

import { importSources, planPublishJob, readWechatSettings, runPublishJobStream, saveWechatSettings } from './bridge'

describe('desktop mock bridge', () => {
  it('imports pasted content in browser mock mode', async () => {
    const payload = await importSources({
      importMode: 'paste',
      pastedText: '测试标题\n\n测试正文',
    })

    expect(payload.job.article_count).toBe(1)
    expect(payload.job.drafts[0].title).toBe('测试标题')
  })

  it('plans and runs a mock publish job', async () => {
    const imported = await importSources({
      importMode: 'paste',
      pastedText: '标题A\n\n正文A',
    })
    const plan = await planPublishJob({
      drafts: imported.job.drafts,
      platforms: ['wechat', 'zhihu'],
      mode: 'draft',
      continueOnError: false,
      templateMode: 'default',
      manualThemeByArticle: {},
      manualCoverByArticlePlatform: {},
      coverMode: 'auto',
      aiDeclarationMode: 'auto',
      scheduledPublishAt: null,
    })

    const seen: string[] = []
    const result = await runPublishJobStream(plan, (event) => {
      seen.push(event.type)
    })

    expect(plan.publish_job.platforms).toEqual(['wechat', 'zhihu'])
    expect(seen).toContain('platform_finished')
    expect(result.publish_job.status).toBe('completed')
  })

  it('keeps continue_on_error in publish planning payload', async () => {
    const imported = await importSources({
      importMode: 'paste',
      pastedText: '标题B\n\n正文B',
    })
    const plan = await planPublishJob({
      drafts: imported.job.drafts,
      platforms: ['wechat'],
      mode: 'draft',
      continueOnError: true,
      templateMode: 'default',
      manualThemeByArticle: {},
      manualCoverByArticlePlatform: {},
      coverMode: 'force_off',
      aiDeclarationMode: 'force_off',
      scheduledPublishAt: null,
    })

    expect(plan.continue_on_error).toBe(true)
    expect(plan.cover_mode).toBe('force_off')
    expect(plan.ai_declaration_mode).toBe('force_off')
  })

  it('keeps scheduled_publish_at in publish planning payload', async () => {
    const imported = await importSources({
      importMode: 'paste',
      pastedText: '标题C\n\n正文C',
    })
    const plan = await planPublishJob({
      drafts: imported.job.drafts,
      platforms: ['toutiao'],
      mode: 'publish',
      continueOnError: false,
      templateMode: 'default',
      manualThemeByArticle: {},
      manualCoverByArticlePlatform: {},
      coverMode: 'auto',
      aiDeclarationMode: 'auto',
      scheduledPublishAt: '2026-03-30T09:30',
    })

    expect(plan.scheduled_publish_at).toBe('2026-03-30T09:30')
    expect(plan.publish_job.scheduled_publish_at).toBe('2026-03-30T09:30')
    expect(plan.context_map[0].scheduled_publish_at).toBe('2026-03-30T09:30')
  })

  it('reads and saves wechat settings in browser mock mode', async () => {
    const before = await readWechatSettings()
    const after = await saveWechatSettings({
      appId: 'wx_demo',
      secret: 'secret_demo',
      author: 'wizard',
    })

    expect(before.app_id).toBe('')
    expect(before.status.appid_ready).toBe(false)
    expect(after.app_id).toBe('wx_demo')
    expect(after.secret).toBe('secret_demo')
    expect(after.status.appid_ready).toBe(true)
  })
})
