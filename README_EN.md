# TiandiDistribute

TiandiDistribute is a Markdown-first publishing toolkit for creators who want one clean workflow for multiple Chinese content platforms.

Write once in Markdown, then preview, style, and distribute the same article to WeChat, Zhihu, Toutiao, Jianshu, and Yidian with a much smaller amount of manual copy-paste.

[中文说明](README.md)

## Why It Is Useful

- One Markdown source for multiple platforms
- A full WeChat theme system with local preview and gallery mode
- AI cover generation is enabled by default when configured
- Browser platforms reuse the same logged-in Chrome workbench
- Comment auto-reply stays as an independent tool instead of polluting the main publishing flow
- The repository has been cleaned for public release: no real keys, no personal paths, no local scheduler setup

## Included Tools

- `publish.py`: unified multi-platform entry
- `wechat_publisher.py`: WeChat-focused publishing flow
- `zhihu_publisher.py`
- `toutiao_publisher.py`
- `jianshu_publisher.py`
- `yidian_publisher.py`
- `scripts/format.py`: formatting, preview, and theme gallery
- `scripts/publish.py`: publish formatted output to WeChat drafts
- `scripts/generate.py`: AI image generation
- `reply_comments.py`: WeChat comment auto-reply entry
- `themes/`: theme library
- `templates/`: preview templates
- `live_cdp.mjs`: CDP browser bridge

## Install

```bash
python3 -m pip install -r requirements.txt
```

You also need Chrome or Chromium for browser-platform publishing.

## Configuration

### 1. Main WeChat publishing flow

```bash
cp secrets.env.example secrets.env
```

Fill:

```env
WECHAT_APPID=your_appid
WECHAT_SECRET=your_secret
WECHAT_AUTHOR=your_author_name
```

### 2. AI and formatting toolchain

```bash
cp config.example.json config.json
```

Fill the real values for:

- `settings.base_url`
- `settings.model`
- `secrets.api_key`
- `ai.url`
- `ai.api_key`
- `ai.model`

### 3. AI cover default behavior

Default strategy:

1. Try AI cover generation first
2. Fallback to local `covers/cover_*.png`

If you want to disable AI-first behavior:

```json
"cover": {
  "prefer_ai_first": false
}
```

## Quick Start

Preview a WeChat article locally:

```bash
python3 wechat_publisher.py "./my_articles/example.md" --dry-run --theme chinese
```

Publish one file to all platforms:

```bash
python3 publish.py "./my_articles/example.md" --platform all --mode draft
```

Batch publish a directory:

```bash
python3 publish.py "./my_articles" --platform all --mode publish --continue-on-error
```

Open the theme gallery:

```bash
python3 scripts/format.py --input "./my_articles/example.md" --gallery
```

Publish through the formatting pipeline:

```bash
python3 scripts/publish.py --input "./my_articles/example.md" --theme newspaper --cover "./covers/cover_01.png"
```

Dry-run comment replies:

```bash
python3 reply_comments.py --dry-run
```

## Browser Workflow

Recommended workflow:

1. Open one remote-debugging-enabled Chrome instance
2. Log in to Zhihu, Toutiao, Jianshu, and Yidian in that same instance
3. Start with `--mode draft`
4. Then switch to `--mode publish`

The main entry tries to:

- connect to the existing browser session
- open missing platform tabs
- warm up the workbench tabs
- reuse the same bound targets
- run preflight checks before publishing

## Useful CDP Commands

```bash
node live_cdp.mjs list
node live_cdp.mjs warmall
node live_cdp.mjs eval <target> "document.title"
node live_cdp.mjs pastehtml <target> "<p>Hello</p>"
node live_cdp.mjs snap <target>
node live_cdp.mjs stop
```

## Who It Is For

- creators who write in Markdown first
- people who care about stable WeChat formatting
- teams or individuals who publish the same content to multiple platforms
- builders who want a scriptable content workflow instead of a manual one

## Disclaimer

This project is for publishing workflow automation and technical experimentation. Platform rules, review policies, and login behavior may change at any time. Use it at your own risk.
