import { describe, expect, it } from 'vitest'

import type { PublishPlan, PublishResult } from './types'
import { buildRetryPlanFromFailures, hasRetryableFailures, listFailedResults } from './recovery'

const basePlan: PublishPlan = {
  publish_job: {
    job_id: 'job-1',
    article_ids: ['a1', 'a2'],
    platforms: ['wechat', 'zhihu'],
    status: 'failed',
    current_step: 'done',
    success_count: 1,
    failure_count: 1,
    skip_count: 0,
    recoverable: true,
    error_summary: 'failed once',
  },
  mode: 'draft',
  continue_on_error: false,
  drafts: [
    {
      article_id: 'a1',
      title: 'A1',
      body_markdown: 'body a1',
      source_path: null,
      source_kind: 'paste',
      image_paths: [],
      word_count: 10,
      template_mode: 'default',
      theme_name: null,
      is_config_complete: true,
    },
    {
      article_id: 'a2',
      title: 'A2',
      body_markdown: 'body a2',
      source_path: null,
      source_kind: 'paste',
      image_paths: [],
      word_count: 10,
      template_mode: 'default',
      theme_name: null,
      is_config_complete: true,
    },
  ],
  template_assignments: [],
  cover_assignments: [],
  staged_articles: [
    { article_id: 'a1', markdown_path: '/tmp/a1.md' },
    { article_id: 'a2', markdown_path: '/tmp/a2.md' },
  ],
  context_map: [
    {
      article_id: 'a1',
      platform: 'wechat',
      markdown_path: '/tmp/a1.md',
      theme_name: null,
      template_mode: 'default',
      cover_path: null,
    },
    {
      article_id: 'a1',
      platform: 'zhihu',
      markdown_path: '/tmp/a1.md',
      theme_name: null,
      template_mode: 'default',
      cover_path: null,
    },
    {
      article_id: 'a2',
      platform: 'wechat',
      markdown_path: '/tmp/a2.md',
      theme_name: null,
      template_mode: 'default',
      cover_path: null,
    },
  ],
  resources: {
    theme_pool: { themes_dir: 'themes', theme_ids: [], count: 0, entries: [] },
    cover_pool: { ok: true, cover_dir: 'covers', paths: [], count: 0, error: null },
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
    defaults: { template_mode: 'default', cover_repeat_window: 8 },
  },
}

const failedResult: PublishResult = {
  publish_job: {
    ...basePlan.publish_job,
    failure_count: 1,
    recoverable: true,
  },
  events: [],
  results: [
    {
      article_id: 'a1',
      platform: 'wechat',
      status: 'draft_only',
      returncode: 0,
      retryable: false,
    },
    {
      article_id: 'a1',
      platform: 'zhihu',
      status: 'failed',
      returncode: 1,
      retryable: true,
      summary: 'network timeout',
    },
  ],
}

describe('publish recovery helpers', () => {
  it('detects retryable failed results', () => {
    expect(hasRetryableFailures(failedResult)).toBe(true)
  })

  it('builds a retry plan containing only failed article-platform pairs', () => {
    const retryPlan = buildRetryPlanFromFailures(basePlan, failedResult)

    expect(retryPlan.publish_job.article_ids).toEqual(['a1'])
    expect(retryPlan.publish_job.platforms).toEqual(['zhihu'])
    expect(retryPlan.context_map).toHaveLength(1)
    expect(retryPlan.context_map[0].platform).toBe('zhihu')
    expect(retryPlan.drafts).toHaveLength(1)
    expect(retryPlan.drafts[0].article_id).toBe('a1')
  })

  it('lists failed results for review in the workbench', () => {
    expect(listFailedResults(failedResult)).toEqual([
      {
        article_id: 'a1',
        platform: 'zhihu',
        retryable: true,
        summary: 'network timeout',
      },
    ])
  })
})
