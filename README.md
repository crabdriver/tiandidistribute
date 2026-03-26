# TiandiDistribute

面向内容创作者的 Markdown 多平台发布工具。

你只需要专注写 Markdown，TiandiDistribute 负责把内容整理成适合微信、知乎、头条号、简书、一点号的发布形态，并尽量复用已经登录的浏览器工作台，减少重复登录、重复排版和重复复制粘贴。

[English](README_EN.md)

## 为什么用它

- 一次写作，多平台分发
- 微信有完整主题系统、画廊预览和本地 dry-run
- AI 封面默认优先启用，配置好后会先尝试生成，再回退到本地封面
- 浏览器平台复用同一个远程调试 Chrome，会话更稳定
- 评论自动回复可独立运行，不强绑定主发布流程
- 仓库已做公开化整理，不包含真实密钥、个人路径和本机调度配置

## 当前支持

- `publish.py`: 多平台统一入口
- `wechat_publisher.py`: 微信主发布链路
- `zhihu_publisher.py`: 知乎发布
- `toutiao_publisher.py`: 头条号发布
- `jianshu_publisher.py`: 简书发布
- `yidian_publisher.py`: 一点号发布
- `scripts/format.py`: 微信排版、主题画廊、预览输出
- `scripts/publish.py`: 基于排版结果推送微信草稿
- `scripts/generate.py`: AI 生图
- `reply_comments.py`: 微信评论自动回复入口
- `themes/`: 主题库
- `templates/`: 预览模板
- `live_cdp.mjs`: CDP 浏览器桥接

## 项目结构

- `publish.py`: 统一发布入口，适合日常主流程
- `wechat_publisher.py`: 微信专用发布器，支持 dry-run、主题、AI 封面、重复标题跳过
- `scripts/`: 独立工具链
- `themes/`: 微信样式主题
- `templates/`: 本地预览与主题画廊模板
- `markdown_utils.py`: Markdown 公共处理逻辑

## 安装

```bash
python3 -m pip install -r requirements.txt
```

还需要：

- 本机安装 Chrome 或 Chromium
- 浏览器平台使用前启用远程调试

## 配置

### 1. 微信主流程配置

```bash
cp secrets.env.example secrets.env
```

```env
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret
WECHAT_AUTHOR=your_author_name
```

### 2. AI 与工具链配置

```bash
cp config.example.json config.json
```

需要按实际情况填写：

- `settings.base_url`: AI 生图接口地址
- `settings.model`: AI 生图模型
- `secrets.api_key`: AI 生图密钥
- `ai.url`: 评论回复模型接口地址
- `ai.api_key`: 评论回复密钥
- `ai.model`: 评论回复模型
- `vault_root`: 可选的素材根目录

### 3. AI 封面默认策略

默认策略是：

1. 优先尝试 AI 封面
2. AI 不可用时，回退到 `covers/cover_*.png`

如果你不想使用 AI 封面，可以在 `config.json` 里把：

```json
"cover": {
  "prefer_ai_first": false
}
```

## 快速开始

### 微信本地预览

```bash
python3 wechat_publisher.py "./my_articles/example.md" --dry-run --theme chinese
```

### 发布单篇到多个平台

```bash
python3 publish.py "./my_articles/example.md" --platform all --mode draft
```

### 批量发布目录

```bash
python3 publish.py "./my_articles" --platform all --mode publish --continue-on-error
```

### 指定微信主题模式

固定主题：

```bash
python3 publish.py "./my_articles" --platform wechat --mode draft --wechat-theme-mode fixed --wechat-theme chinese
```

随机主题：

```bash
python3 publish.py "./my_articles" --platform wechat --mode draft --wechat-theme-mode random
```

交互选择：

```bash
python3 publish.py "./my_articles" --platform wechat --mode draft --wechat-theme-mode prompt
```

### 打开主题画廊

```bash
python3 scripts/format.py --input "./my_articles/example.md" --gallery
```

### 从排版结果推送微信草稿

```bash
python3 scripts/publish.py --input "./my_articles/example.md" --theme newspaper --cover "./covers/cover_01.png"
```

### 评论自动回复

```bash
python3 reply_comments.py --dry-run
```

## 浏览器平台工作流

推荐做法：

1. 打开同一个启用远程调试的 Chrome 实例
2. 在这个实例里登录知乎、头条号、简书、一点号
3. 先用 `--mode draft` 试跑
4. 再切 `--mode publish`

主入口默认会：

- 自动连接浏览器
- 自动补开缺失平台标签页
- 自动预热工作台标签页
- 复用固定 workbench
- 在正式执行前做预检

## 常用 CDP 命令

```bash
node live_cdp.mjs list
node live_cdp.mjs warmall
node live_cdp.mjs eval <target> "document.title"
node live_cdp.mjs pastehtml <target> "<p>Hello</p>"
node live_cdp.mjs snap <target>
node live_cdp.mjs stop
```

## 适合谁

- 习惯用 Markdown 写作的内容创作者
- 想把公众号排版做得更稳定的人
- 需要跨平台分发但不想手工复制粘贴的人
- 想把内容工作流脚本化、自动化的人

## 免责声明

本项目仅用于内容工作流自动化与技术研究。不同平台的审核、风控、登录和接口规则可能随时变化，请自行评估和承担使用风险。
