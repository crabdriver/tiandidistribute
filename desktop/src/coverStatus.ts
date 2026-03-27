import type { CoverPool } from './types'

export function describeCoverPoolStatus(coverPool: CoverPool | null | undefined): string {
  if (coverPool?.ok) {
    return `已就绪 · ${coverPool.count} 张`
  }

  if (coverPool?.cover_dir) {
    return `封面池不可用，请把默认封面放到 ${coverPool.cover_dir}（例如 cover_01.png）`
  }

  return '封面池不可用，请准备本地默认封面后再试。'
}
