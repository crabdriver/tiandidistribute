import type { Platform, WechatConfigStatus } from './types'

export function describeWechatStatus(status: WechatConfigStatus): string {
  if (status.appid_ready && status.secret_ready) {
    return '微信配置已就绪'
  }
  return '微信配置未完成'
}

export function buildWechatBlockingMessage(
  platforms: Platform[],
  status: WechatConfigStatus,
): string {
  if (!platforms.includes('wechat')) {
    return ''
  }
  if (status.appid_ready && status.secret_ready) {
    return ''
  }
  return '已勾选微信平台，请先在设置里填写微信 AppID 和 Secret。'
}
