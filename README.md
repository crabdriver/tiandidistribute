# ordo

`ordo` 是一个面向中文内容创作者的本地多平台自动发布引擎。它以 Markdown 为单一内容源，负责把同一篇文章整理并分发到微信、知乎、头条号、简书、一点号等平台，目标是减少重复登录、重复排版和重复复制粘贴。

当前仓库已经包含一个可运行的桌面工作台 MVP，同时仍保留本地 CLI 工作流；项目的正式演进方向是继续把这套本地发布内核打磨稳定，并最终封装成可在 `macOS` 和 `Windows` 上一键安装的原生桌面软件。

自动化边界目前定义为：默认依赖用户已经存在的登录态，系统负责文章装载、内容转换、平台注入、草稿或发布、结果记录和失败恢复；不承诺自动登录、验证码处理或风控绕过。

兼容性说明：当前仓库中的部分内部路径与缓存目录仍沿用 `.tiandidistribute/` 命名，以兼容现有工作流和历史数据；对外项目名称统一为 `ordo`。

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
- `tiandi_engine/`: 本地发布引擎核心包，承载任务、配置、状态、结果、平台适配与 runner
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

- `publish.py`: 对外 CLI 入口，当前主流程已通过 `tiandi_engine` 统一调度
- `tiandi_engine/`: 引擎内核，包含任务模型、配置模型、状态恢复、平台适配与统一 runner
- `wechat_publisher.py`: 微信兼容入口，保留现有 CLI 使用方式
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

### 桌面工作台 MVP

桌面工作台位于 `desktop/`，采用 `Tauri + Rust` 桌面壳，底层继续调用仓库根目录下的 Python 发布引擎。

首次启动：

```bash
cd desktop
npm install
npm run tauri:dev
```

如果你的 Python 不在 `python3`，可在启动前指定：

```bash
export ORDO_PYTHON=/path/to/python
cd desktop
npm run tauri:dev
```

桌面工作台当前已打通的主链路：

- 顶部 `设置` 弹窗可直接填写微信 `AppID` / `Secret` / `Author`
- 微信配置状态会在顶部即时显示，未配置时会阻止微信发布并给出明确提示
- 粘贴 / 单文件 / 文件夹导入
- 主题池 / 封面池发现
- 逐篇模板覆盖与非微信封面覆盖
- 调用 Python bridge 创建发布计划
- `遇错继续` 开关会透传到引擎侧发布计划
- 失败后可切换到“仅重试失败项”的最小续跑计划
- 发起发布并实时回看结构化日志
- 发布后可直接查看平台级结果详情与失败摘要
- 读取最近发布记录与最近 session 快照

封面接入补充说明：

- 非微信平台默认从仓库根目录 `covers/` 读取本地封面池
- 如果你想改目录，可在 `config.json` 里设置 `assignment.cover_dir`
- 当前工作台会在封面池不可用时直接提示目标目录，而不是静默跳过

推荐首次使用顺序：

1. 打开桌面工作台
2. 点击顶部 `设置`
3. 填写微信 `AppID`、`Secret`、`Author`
4. 保存后再开始导入文章并发布

### 桌面打包预览

当前桌面壳已经可以构建开发预览包：

```bash
cd desktop
npm run tauri:build
```

如果你希望把构建出来的桌面壳指向一个明确的引擎仓库目录，可在启动前设置：

```bash
export ORDO_REPO_ROOT=/path/to/tiandidistribute
export ORDO_PYTHON=/path/to/python
cd desktop
npm run tauri:dev
```

说明：

- 当前打包产物更适合作为“开发预览 / 内测包”，尚不是完全独立、内嵌 Python 引擎的一键安装版
- `ORDO_REPO_ROOT` 用于让桌面壳在非源码目录启动时，仍能找到 `scripts/workbench_bridge.py`
- 当前 `tauri.conf.json` 仍以 `.app` 级别产物为主，Windows 安装器与正式分发流程仍属于后续阶段

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
- 从本地封面池为**非微信平台**自动分配封面（与微信的 `covers/cover_*.png` / AI 封面策略相互独立，详见 `tiandi_engine` 配置）

### 结构化结果与 GUI 消费

每条平台执行结束后，除原有日志外会额外输出一行 `[META]` 前缀的 JSON，字段包括：`article_id`、`theme_name`、`template_mode`、`cover_path`、`platform`、`status`、`error_type`。后续桌面 GUI 或外部脚本可直接解析，无需再从散落的 stdout 推断状态。

`publish_records.csv` 会写入与上述一致的列。若你仍在使用旧版仅有 8 列的 CSV，首次按新逻辑追加记录时会**自动迁移**为扩展表头（建议在版本升级后备份该文件）。

### 浏览器侧封面能力（当前实现）

- **知乎、头条号、一点号**：发布脚本支持通过引擎传入的封面路径设置自定义封面（依赖远程调试 Chrome 与页面 DOM；平台改版可能导致不稳定）。
- **简书**：编辑器对封面上传限制较多，当前实现会在无法完成自定义封面时给出**明确诊断失败**，请勿理解为已全面支持简书自定义封面。

## 常用 CDP 命令

```bash
node live_cdp.mjs list
node live_cdp.mjs warmall
node live_cdp.mjs eval <target> "document.title"
node live_cdp.mjs pastehtml <target> "<p>Hello</p>"
node live_cdp.mjs setfile <target> "<css-selector>" "/path/to/local/file"
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
