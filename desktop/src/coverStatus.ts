import type { CoverPool } from './types'

export function describeCoverPoolStatus(coverPool: CoverPool | null | undefined): string {
  if (coverPool?.ok) {
    return `已就绪 · ${coverPool.count} 张`
  }
  return '未就绪 (请添加封面图)'
}
