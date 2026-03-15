# Article Auto Publisher

This repo currently supports:

- `wechat_publisher.py`: publish Markdown articles to the WeChat Official Account draft box
- `yidian_publisher.py`: reuse your current Chrome session and publish or save drafts to 一点号
- `jianshu_publisher.py`: reuse your current Chrome session and publish or save drafts to 简书
- `toutiao_publisher.py`: reuse your current Chrome session and publish or save drafts to 头条号
- `zhihu_publisher.py`: reuse your current Chrome session and publish or save drafts to 知乎文章
- `publish.py`: one entrypoint to publish one Markdown article to multiple web platforms
- `live_cdp.mjs`: a tiny helper that connects to your live Chrome tab via DevTools Protocol

## Features
- **WeChat draft publishing**: Converts Markdown to WeChat-ready HTML with premium minimalist CSS.
- **Live Chrome publishing**: Reuses your already logged-in Chrome session for web platforms.
- **Draft-first workflow**: You can verify content on the target platform before final publish.
- **Credential protection**: Uses `.env` files to keep API tokens safe.

## Setup
1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `secrets.env` file in the root directory:
   ```env
   WECHAT_APPID=your_appid
   WECHAT_SECRET=your_secret
   ```
   You can copy from `secrets.env.example`.
4. Run the WeChat publisher:
   ```bash
   python wechat_publisher.py
   ```

## Usage
Edit the article directory path in `wechat_publisher.py` to point to your Markdown collection.

## Multi-platform Usage

Publish one article to all supported platforms:

```bash
python publish.py "神圣愿景难敌养命碎银.md" --mode publish
```

`publish.py` now does these automatically by default:

- auto-launch Chrome if needed
- auto-open missing platform tabs
- bind a fixed workbench of platform tabs
- auto-warm the corresponding Chrome tabs
- run a preflight check before the real publish starts
- then run the actual platform publishers

Only publish to selected platforms:

```bash
python publish.py "神圣愿景难敌养命碎银.md" --platform zhihu,toutiao --mode draft
```

Continue even if one platform fails:

```bash
python publish.py "神圣愿景难敌养命碎银.md" --platform all --mode publish --continue-on-error
```

Disable automation helpers only when needed:

```bash
python publish.py "神圣愿景难敌养命碎银.md" --no-auto-launch --no-auto-open --no-warmup
```

Rebind the fixed workbench to the tabs you currently have open:

```bash
python publish.py "神圣愿景难敌养命碎银.md" --platform all --mode draft --rebind-workbench
```

Currently supported in `publish.py`:

- `wechat`
- `zhihu`
- `toutiao`
- `jianshu`
- `yidian`

Batch publish a whole directory:

```bash
python publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode publish --continue-on-error
```

Only process the first 5 files in a directory:

```bash
python publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode draft --limit 5
```

Skip the first 10 files in a directory:

```bash
python publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode publish --offset 10 --continue-on-error
```

See `BATCH_PUBLISHING_GUIDE.md` for the reusable title-cleaning and cover requirements.

## live_cdp Usage

List tabs:

```bash
node live_cdp.mjs list
```

Common commands:

```bash
node live_cdp.mjs eval <target> "document.title"
node live_cdp.mjs nav <target> "https://example.com"
node live_cdp.mjs click <target> "button.primary"
node live_cdp.mjs clickxy <target> 500 300
node live_cdp.mjs type <target> "hello world"
node live_cdp.mjs html <target> ".article"
node live_cdp.mjs shot <target> "/tmp/page.png"
node live_cdp.mjs snap <target>
node live_cdp.mjs warm <target>
node live_cdp.mjs warmall
node live_cdp.mjs stop
```

`live_cdp.mjs` now uses a long-lived broker so repeated commands reuse the same CDP connection instead of reconnecting every time.

To reduce repeated Chrome authorization prompts even further:

- run `node live_cdp.mjs warmall` once after opening your working tabs
- the daemon idle timeout is now 12 hours by default
- you can override it with `LIVE_CDP_IDLE_TIMEOUT_MS`

## Yidian Usage

Before using `yidian_publisher.py`:

1. Open Chrome
2. Enable remote debugging at `chrome://inspect/#remote-debugging`
3. Log in to 一点号 and open the article editor:
   [一点号编辑器](https://mp.yidianzixun.com/#/Writing/articleEditor)

Save an article as draft:

```bash
python yidian_publisher.py "神圣愿景难敌养命碎银.md" --mode draft
```

Directly publish:

```bash
python yidian_publisher.py "神圣愿景难敌养命碎银.md" --mode publish
```

## Jianshu Usage

Before using `jianshu_publisher.py`:

1. Open Chrome
2. Enable remote debugging at `chrome://inspect/#remote-debugging`
3. Log in to 简书 and open the writer page:
   [简书写作页](https://www.jianshu.com/writer#/)

Save a new article as draft:

```bash
python jianshu_publisher.py "神圣愿景难敌养命碎银.md" --mode draft
```

Directly publish:

```bash
python jianshu_publisher.py "神圣愿景难敌养命碎银.md" --mode publish
```

## Toutiao Usage

Before using `toutiao_publisher.py`:

1. Open Chrome
2. Enable remote debugging at `chrome://inspect/#remote-debugging`
3. Log in to 头条号 and open the article editor:
   [头条号编辑器](https://mp.toutiao.com/profile_v4/graphic/publish)

Save an article as draft:

```bash
python toutiao_publisher.py "神圣愿景难敌养命碎银.md" --mode draft
```

Directly publish:

```bash
python toutiao_publisher.py "神圣愿景难敌养命碎银.md" --mode publish
```

## Zhihu Usage

Before using `zhihu_publisher.py`:

1. Open Chrome
2. Enable remote debugging at `chrome://inspect/#remote-debugging`
3. Log in to 知乎 and open any Zhihu page or directly open the writer page:
   [知乎写文章](https://zhuanlan.zhihu.com/write)

Write into draft/editor page:

```bash
python zhihu_publisher.py "神圣愿景难敌养命碎银.md" --mode draft
```

Attempt direct publish:

```bash
python zhihu_publisher.py "神圣愿景难敌养命碎银.md" --mode publish
```
