import type { Platform, PublishPlan, PublishResult } from './types'

const SUCCESS_STATUSES = new Set(['published', 'scheduled', 'draft_only', 'success_unknown', 'skipped_existing'])

function isFailedResult(result: Record<string, unknown>): boolean {
  if (Number(result.returncode ?? 0) !== 0) {
    return true
  }
  const status = String(result.status ?? '')
  return status !== '' && !SUCCESS_STATUSES.has(status)
}

function failedPairs(result: PublishResult): Array<{ articleId: string; platform: Platform }> {
  return result.results.flatMap((raw) => {
    const articleId = String(raw.article_id ?? '')
    const platform = raw.platform as Platform | undefined
    if (!articleId || !platform || !isFailedResult(raw)) {
      return []
    }
    return [{ articleId, platform }]
  })
}

export function listFailedResults(result: PublishResult | null | undefined) {
  if (!result) {
    return []
  }
  return result.results.flatMap((raw) => {
    const articleId = String(raw.article_id ?? '')
    const platform = raw.platform as Platform | undefined
    if (!articleId || !platform || !isFailedResult(raw)) {
      return []
    }
    return [
      {
        article_id: articleId,
        platform,
        retryable: Boolean(raw.retryable),
        summary: String(raw.summary ?? raw.stderr ?? raw.stdout ?? ''),
      },
    ]
  })
}

export function hasFailedResults(result: PublishResult | null | undefined): boolean {
  if (!result || result.publish_job.failure_count <= 0) {
    return false
  }
  return result.results.some((raw) => isFailedResult(raw))
}

export function hasRetryableFailures(result: PublishResult | null | undefined): boolean {
  if (!result || result.publish_job.failure_count <= 0) {
    return false
  }
  return result.results.some((raw) => isFailedResult(raw) && Boolean(raw.retryable))
}

export function buildRetryPlanFromFailures(plan: PublishPlan, result: PublishResult): PublishPlan {
  const pairs = failedPairs(result)
  const pairKeys = new Set(pairs.map((item) => `${item.articleId}:${item.platform}`))
  const failedArticleIds = plan.publish_job.article_ids.filter((articleId) =>
    pairs.some((item) => item.articleId === articleId),
  )
  const failedPlatforms = plan.publish_job.platforms.filter((platform) =>
    pairs.some((item) => item.platform === platform),
  )

  return {
    ...plan,
    publish_job: {
      ...plan.publish_job,
      job_id: `${plan.publish_job.job_id}-retry`,
      article_ids: failedArticleIds,
      platforms: failedPlatforms,
      status: 'pending',
      current_step: '',
      success_count: 0,
      failure_count: 0,
      skip_count: 0,
      recoverable: true,
      error_summary: '',
    },
    drafts: plan.drafts.filter((draft) => failedArticleIds.includes(draft.article_id)),
    cover_assignments: plan.cover_assignments.filter((assignment) =>
      pairKeys.has(`${assignment.article_id}:${assignment.platform}`),
    ),
    staged_articles: plan.staged_articles.filter((item) => failedArticleIds.includes(item.article_id)),
    context_map: plan.context_map.filter((item) => pairKeys.has(`${item.article_id}:${item.platform}`)),
  }
}
