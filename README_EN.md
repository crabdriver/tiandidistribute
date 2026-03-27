# ordo

`ordo` is a local multi-platform publishing engine for Chinese-language creators. It treats Markdown as the single source of truth, then prepares and distributes the same article to WeChat, Zhihu, Toutiao, Jianshu, Yidian, and similar platforms with far less repeated login, formatting, and copy-paste work.

The current repository already includes a runnable desktop workbench MVP on top of the local CLI and engine workflow, and the official direction remains to harden that core into a native desktop application for `macOS` and `Windows`.

The current automation boundary is explicit: `ordo` assumes the user already has valid platform login sessions, and the system handles article loading, content transformation, editor injection, draft or publish actions, result recording, and failure recovery. It does not promise automatic login, CAPTCHA handling, or anti-risk bypass behavior.

Compatibility note: some internal paths and cache directories still use `.tiandidistribute/` for backward compatibility with the existing workflow and stored state, while the public project name is now `ordo`.

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
- `tiandi_engine/`: core local publishing engine package for tasks, config, state, results, adapters, and runner
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

## Project Structure

- `publish.py`: public CLI entry, now routed through the shared `tiandi_engine` runner
- `tiandi_engine/`: engine core for task models, config, state recovery, platform adapters, and orchestration
- `wechat_publisher.py`: compatibility CLI entry for the WeChat publishing flow
- `scripts/`: standalone tools for formatting, WeChat draft publishing, image generation, and auxiliary workflows
- `themes/`: WeChat theme library
- `templates/`: local preview and gallery templates
- `markdown_utils.py`: shared Markdown transformation utilities

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

### Desktop Workbench MVP

The desktop workbench lives in `desktop/` and uses a `Tauri + Rust` shell on top of the Python publishing engine in the repository root.

First start:

```bash
cd desktop
npm install
npm run tauri:dev
```

If your Python executable is not `python3`, set it before launch:

```bash
export ORDO_PYTHON=/path/to/python
cd desktop
npm run tauri:dev
```

Current desktop workbench coverage:

- visual WeChat settings (`AppID` / `Secret` / `Author`)
- top-level WeChat readiness status and blocking hint when credentials are missing
- paste / single-file / folder import
- theme-pool and cover-pool discovery
- per-article theme override and non-WeChat cover override
- Python bridge planning and streaming publish execution
- `continue_on_error` passed through to publish planning
- retry-only-failed-items flow after a failed run
- structured result details and recent history refresh after publishing

Cover-pool note:

- non-WeChat platforms read the default local cover pool from `covers/`
- you can override that path with `assignment.cover_dir` in `config.json`
- the desktop UI now shows an explicit target directory when the cover pool is missing or empty

### Desktop Packaging Preview

The current desktop shell can already build a development preview bundle:

```bash
cd desktop
npm run tauri:build
```

If you want the built shell to point to an explicit engine checkout, set:

```bash
export ORDO_REPO_ROOT=/path/to/tiandidistribute
export ORDO_PYTHON=/path/to/python
cd desktop
npm run tauri:dev
```

Notes:

- the current bundle is best treated as a developer preview, not a fully standalone installer with an embedded Python engine
- `ORDO_REPO_ROOT` lets the desktop shell find `scripts/workbench_bridge.py` outside the original source launch layout
- `tauri.conf.json` is still oriented toward `.app`-level output; Windows installer packaging remains a later step

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
- assign covers for **non-WeChat** browser platforms from a local cover pool (separate from WeChat’s `covers/cover_*.png` / AI cover behavior; see `tiandi_engine` config)

### Structured results for GUI consumers

After each platform step, the CLI prints one JSON line prefixed with `[META]`, containing: `article_id`, `theme_name`, `template_mode`, `cover_path`, `platform`, `status`, and `error_type`. A future desktop GUI or automation can parse this without scraping unstructured logs.

`publish_records.csv` includes the same columns. If you still have an older 8-column file, the first append under the new logic **migrates** the file to the wider schema (back up the CSV before upgrading).

### Browser cover support (current behavior)

- **Zhihu, Toutiao, Yidian**: publisher scripts accept a cover path from the engine and attempt custom cover upload (DOM-dependent; site changes may break it).
- **Jianshu**: the editor is restrictive; when custom cover cannot be applied, the flow fails with an **explicit diagnostic**—do not read this as full Jianshu custom-cover support.

## Useful CDP Commands

```bash
node live_cdp.mjs list
node live_cdp.mjs warmall
node live_cdp.mjs eval <target> "document.title"
node live_cdp.mjs pastehtml <target> "<p>Hello</p>"
node live_cdp.mjs setfile <target> "<css-selector>" "/path/to/local/file"
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
