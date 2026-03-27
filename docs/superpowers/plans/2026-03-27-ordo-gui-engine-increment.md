# Ordo GUI-Ready Engine Increment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `ordo` 增加内容导入、模板分配、非微信平台封面分配和 GUI-ready 工作台数据契约，让现有 CLI/引擎可以直接承接后续桌面 GUI。

**Architecture:** 继续沿用当前 `tiandi_engine` 作为统一执行内核，把新增能力拆成 4 层：导入归一化、模板/封面分配、平台执行扩展、CLI 与工作台契约输出。GUI 本轮不直接引入 `Tauri`，先把可复用的数据对象、任务输入和执行结果补齐，再在下一轮接桌面壳。

**Tech Stack:** Python, `unittest`, 现有 `tiandi_engine` 运行管线, 浏览器平台脚本, 本地 JSON 状态文件, 必要时新增 1 个 DOCX 解析依赖

---

## Current Status Note

这份文档是“引擎 GUI-ready 增量阶段”的历史实施计划，当前仓库状态已经明显超出本文最初范围：

- `tiandi_engine/importers/`、`tiandi_engine/assignment/`、`tiandi_engine/workbench/`、相关测试与桥接能力已落地
- 仓库中已经存在 `desktop/` 下的 `Tauri + Rust` 桌面工作台 MVP
- 因此本文中关于“本轮不直接引入 `Tauri`”的描述已不再代表当前仓库现状

后续判断实现状态时，应以代码、`README.md` 与更新后的桌面工作台文档为准；本文件主要保留为阶段性实施记录。

## File Structure

- Create: `tiandi_engine/models/workbench.py`
  - 定义 `ImportJob`、`ArticleDraft`、`TemplateAssignment`、`CoverAssignment`、`PublishJob`
- Create: `tiandi_engine/importers/__init__.py`
- Create: `tiandi_engine/importers/normalize.py`
  - 负责 `Markdown` / `TXT` / `DOCX` / 粘贴文本 -> 内部文章结构
- Create: `tiandi_engine/importers/sources.py`
  - 负责单文件、目录、文本输入的入口适配
- Create: `tiandi_engine/assignment/__init__.py`
- Create: `tiandi_engine/assignment/templates.py`
  - 负责默认模板/自定义模板分配、随机主题分配
- Create: `tiandi_engine/assignment/covers.py`
  - 负责非微信平台封面池扫描、随机分配、短周期去重
- Create: `tests/test_engine_importers.py`
- Create: `tests/test_engine_assignments.py`
- Modify: `tiandi_engine/models/task.py`
  - 把文章级模板/封面信息纳入任务对象
- Modify: `tiandi_engine/config.py`
  - 暴露主题池、封面池、封面目录、重复窗口等配置
- Modify: `tiandi_engine/platforms/base.py`
  - 扩展平台适配器 `prepare()` 输入，允许透传封面/模板上下文
- Modify: `tiandi_engine/runner/pipeline.py`
  - 让 pipeline 基于文章级配置执行，而不是只有 `theme_name`
- Modify: `tiandi_engine/state/session.py`
  - 记录分配结果与恢复所需的模板/封面状态
- Modify: `publish.py`
  - 增加导入、模板模式、封面策略的 CLI 入口
- Modify: `zhihu_publisher.py`
- Modify: `toutiao_publisher.py`
- Modify: `jianshu_publisher.py`
- Modify: `yidian_publisher.py`
  - 接受封面/模板参数并在现有发布链路里应用
- Modify: `tests/test_engine_pipeline.py`
- Modify: `tests/test_platform_contracts.py`
- Modify: `tests/test_publish_classify_and_parse.py`
- Modify: `tests/test_publish_preflight.py`
- Modify: `zhihu_publisher.py`
- Modify: `toutiao_publisher.py`
- Modify: `jianshu_publisher.py`
- Modify: `yidian_publisher.py`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `docs/manual-validation/local-publish-engine-phase1.md`
- Optional Modify: `requirements.txt`
  - 若内置实现无法稳定覆盖 `DOCX`，在这里补入解析依赖

### Task 1: 建立导入模型与内容归一化

**Files:**
- Create: `tiandi_engine/models/workbench.py`
- Create: `tiandi_engine/importers/__init__.py`
- Create: `tiandi_engine/importers/normalize.py`
- Create: `tiandi_engine/importers/sources.py`
- Test: `tests/test_engine_importers.py`
- Test: `tests/test_engine_results_errors.py`
- Optional Modify: `requirements.txt`

- [ ] **Step 1: 先写失败测试，锁定导入输出结构**

在 `tests/test_engine_importers.py` 写这些用例：

```python
def test_import_markdown_file_builds_article_draft():
    drafts = import_sources([Path("/tmp/a.md")], source_kind="file")
    assert drafts[0].title == "a"
    assert drafts[0].body_markdown.startswith("#")

def test_import_folder_collects_supported_files_only():
    drafts = import_path(folder_path)
    assert sorted({draft.source_kind for draft in drafts}) == ["docx", "markdown", "txt"]

def test_normalize_txt_promotes_first_line_to_title():
    draft = normalize_text_document("标题\n\n第一段")
    assert draft.title == "标题"
    assert "第一段" in draft.body_markdown
```

- [ ] **Step 2: 运行导入测试，确认当前失败**

Run: `python3 -m unittest tests.test_engine_importers -v`
Expected: FAIL，提示导入模块或 workbench 数据对象尚不存在

- [ ] **Step 3: 实现 workbench 数据对象**

在 `tiandi_engine/models/workbench.py` 最少落下这些 dataclass：

```python
@dataclass(frozen=True)
class ArticleDraft:
    article_id: str
    title: str
    body_markdown: str
    source_path: Optional[Path]
    source_kind: str
    image_paths: Tuple[Path, ...] = ()
```

并补 `ImportJob` / `TemplateAssignment` / `CoverAssignment` / `PublishJob` 的字段定义和 `to_dict()`。

首版可以先落最小字段，但本任务结束前必须把规格第 16 节里 GUI 一期真正会消费的最小字段补齐，至少包括：

- `ArticleDraft.word_count`
- `ArticleDraft.template_mode`
- `ArticleDraft.is_config_complete`
- `TemplateAssignment.is_confirmed`
- `CoverAssignment.platform`
- `PublishJob.current_step`
- `PublishJob.recoverable`

- [ ] **Step 4: 实现导入入口与归一化器**

在 `tiandi_engine/importers/normalize.py` / `sources.py` 完成：

- `Markdown`：保留正文，标题优先取首个 `# `
- `TXT`：首个非空行作为标题，剩余内容归一为 Markdown 段落
- `DOCX`：优先用稳定方式抽取标题、段落、列表、图片引用
- 目录导入：只收 `md` / `txt` / `docx`
- 粘贴文本：走与 `TXT/Markdown` 相同的轻量归一化

- [ ] **Step 5: 补充配置与回归测试**

如果 `DOCX` 需要额外依赖，最后再改 `requirements.txt`，并补 1 个最小 `DOCX` 夹具测试；同时更新 `tests/test_engine_results_errors.py` 中与新 dataclass 序列化相关的断言。

- [ ] **Step 6: 运行测试确认通过**

Run: `python3 -m unittest tests.test_engine_importers tests.test_engine_results_errors -v`
Expected: PASS

### Task 2: 建立模板分配与封面分配服务

**Files:**
- Create: `tiandi_engine/assignment/__init__.py`
- Create: `tiandi_engine/assignment/templates.py`
- Create: `tiandi_engine/assignment/covers.py`
- Modify: `tiandi_engine/config.py`
- Modify: `tiandi_engine/state/session.py`
- Test: `tests/test_engine_assignments.py`
- Test: `tests/test_engine_state_session.py`

- [ ] **Step 1: 写失败测试，锁定分配规则**

在 `tests/test_engine_assignments.py` 先覆盖：

```python
def test_default_template_mode_assigns_random_theme_per_article():
    assignments = assign_templates(drafts, mode="default", available_themes=["a", "b", "c"], seed=7)
    assert len({item.theme_name for item in assignments}) > 1

def test_custom_template_mode_respects_manual_mapping():
    assignments = assign_templates(drafts, mode="custom", custom_map={"article-1": "midnight"})
    assert assignments["article-1"].theme_name == "midnight"

def test_cover_assignment_is_per_article_per_platform():
    covers = assign_platform_covers(drafts, ["zhihu", "toutiao"], cover_pool=pool, history={})
    assert covers[("article-1", "zhihu")] != covers[("article-1", "toutiao")]
```

- [ ] **Step 2: 运行测试，确认当前失败**

Run: `python3 -m unittest tests.test_engine_assignments -v`
Expected: FAIL，提示 assignment 模块不存在

- [ ] **Step 3: 实现模板分配服务**

在 `tiandi_engine/assignment/templates.py` 实现：

- `default` 模式：对每篇文章分配主题
- `custom` 模式：读取人工映射；未指定项自动回退默认主题
- 随机分配允许传入 `seed`，方便测试
- 默认主题池从 `themes/*.json` 扫描，不写死名称

- [ ] **Step 4: 实现非微信封面分配服务**

在 `tiandi_engine/assignment/covers.py` 实现：

- 从本地封面目录扫描候选资源
- 只给 `zhihu` / `toutiao` / `jianshu` / `yidian` 分配
- 分配粒度为 `article x platform`
- 支持读取历史分配记录，尽量避免短周期重复
- 封面不足时给出显式告警，不静默降级

- [ ] **Step 5: 扩展配置与会话落盘**

在 `tiandi_engine/config.py` / `state/session.py` 增加：

- `cover_dir`
- `cover_repeat_window`
- `default_template_mode`
- 当前文章模板/封面分配结果

- [ ] **Step 6: 运行测试确认通过**

Run: `python3 -m unittest tests.test_engine_assignments tests.test_engine_state_session -v`
Expected: PASS

### Task 3: 把模板与封面接入任务模型、runner 和平台适配器

**Files:**
- Modify: `tiandi_engine/models/task.py`
- Modify: `tiandi_engine/platforms/base.py`
- Modify: `tiandi_engine/platforms/registry.py`
- Modify: `tiandi_engine/runner/pipeline.py`
- Modify: `tiandi_engine/platforms/zhihu/publisher.py`
- Modify: `tiandi_engine/platforms/toutiao/publisher.py`
- Modify: `tiandi_engine/platforms/jianshu/publisher.py`
- Modify: `tiandi_engine/platforms/yidian/publisher.py`
- Modify: `zhihu_publisher.py`
- Modify: `toutiao_publisher.py`
- Modify: `jianshu_publisher.py`
- Modify: `yidian_publisher.py`
- Modify: `tests/test_engine_pipeline.py`
- Modify: `tests/test_platform_contracts.py`

- [ ] **Step 1: 写失败测试，锁定 runner 透传行为**

先在 `tests/test_engine_pipeline.py` 和 `tests/test_platform_contracts.py` 写断言：

```python
def test_run_platform_task_passes_cover_and_theme_context():
    result = run_platform_task(..., theme_name="midnight", cover_path="/tmp/cover1.png")
    assert result["command"].endswith("--cover /tmp/cover1.png")

def test_browser_platform_prepare_supports_cover_argument():
    prepared = registry["zhihu"].prepare(..., theme_name="midnight", cover_path="/tmp/cover1.png")
    assert "--cover" in prepared["command"]
```

- [ ] **Step 2: 运行定向测试，确认当前失败**

Run: `python3 -m unittest tests.test_engine_pipeline tests.test_platform_contracts -v`
Expected: FAIL，提示 `prepare()` 和 pipeline 还不接受 `cover_path`

- [ ] **Step 3: 扩展任务模型**

在 `tiandi_engine/models/task.py` 为平台请求或文章任务增加：

- `theme_name`
- `cover_path`
- `template_mode`
- 必要时 `draft_id/article_id`

同时保证旧的只传微信主题路径仍兼容。

- [ ] **Step 4: 扩展平台适配器与 runner**

在 `tiandi_engine/platforms/base.py` / `runner/pipeline.py`：

- `prepare()` 增加 `cover_path` 和上下文字段
- `run_platform_task()` / `run_publish_pipeline()` 改为按文章级配置调用
- 返回 payload 时把最终模板/封面信息写回结果，供 GUI/CLI 展示

- [ ] **Step 5: 让各浏览器平台先接受新参数**

先保证 4 个浏览器平台 CLI 至少能接受：

```bash
python3 zhihu_publisher.py article.md --mode draft --theme midnight --cover /tmp/cover.png
```

即使某个平台暂时不用 `--theme`，也要接受参数并把它纳入日志/后续扩展位，避免 runner 再次分叉。

这里的落点以根目录兼容入口 `zhihu_publisher.py` / `toutiao_publisher.py` / `jianshu_publisher.py` / `yidian_publisher.py` 为准；`tiandi_engine/platforms/*/publisher.py` 继续只承担 adapter 薄封装，避免两套逻辑分叉。

- [ ] **Step 6: 跑回归测试**

Run: `python3 -m unittest tests.test_engine_pipeline tests.test_platform_contracts -v`
Expected: PASS

### Task 4: 在真实浏览器平台链路中应用封面策略

**Files:**
- Modify: `zhihu_publisher.py`
- Modify: `toutiao_publisher.py`
- Modify: `jianshu_publisher.py`
- Modify: `yidian_publisher.py`
- Modify: `publish.py`
- Modify: `tests/test_publish_preflight.py`
- Optional Test: `tests/test_publish_browser_options.py`

- [ ] **Step 1: 先写行为测试/参数测试**

优先锁定 CLI 层行为：

```python
def test_preflight_warns_when_non_wechat_cover_pool_missing():
    blockers, warnings = run_preflight_checks(["zhihu"], "publish", workbench={}, cover_status=...)
    assert "封面池" in warnings[0] or "封面池" in blockers[0]
```

如果顶层 `publish.py` 已经足够复杂，新增 `tests/test_publish_browser_options.py` 专门覆盖参数解析和封面策略路由。

- [ ] **Step 2: 运行测试，确认失败**

Run: `python3 -m unittest tests.test_publish_preflight -v`
Expected: FAIL，提示预检层尚未理解非微信封面池

- [ ] **Step 3: 先把 `publish.py` 接到分配服务**

在主入口做这些事：

- 导入阶段支持文件/目录/文本三种输入模型
- 初始化模板模式与封面模式
- 生成文章级主题/封面分配结果
- 预检封面池是否可用
- 把分配结果传给 `run_publish_pipeline()`

CLI 必须明确表达“这一次批量任务的全局模板模式”，至少支持：

- `default`：整批任务统一按系统规则随机分配
- `custom`：整批任务进入逐篇映射模式，未指定项回退默认主题

逐篇覆盖优先级必须高于全局模式默认分配。

- [ ] **Step 4: 按平台落地封面选择**

逐个平台接入真实封面操作：

- `zhihu_publisher.py`：补充上传/选择封面流程
- `toutiao_publisher.py`：从当前“无封面”切换为指定封面上传
- `jianshu_publisher.py`：补齐封面入口，有则上传，无则继续现有流程
- `yidian_publisher.py`：从默认封面切换到指定封面，保留兜底

如果某个平台暂时缺少稳定 DOM 钩子，至少先把“支持指定封面/回退默认封面”的行为做成可诊断失败，而不是静默继续。

- [ ] **Step 5: 回归主入口测试**

Run: `python3 -m unittest tests.test_publish_preflight tests.test_publish_classify_and_parse -v`
Expected: PASS

### Task 5: 暴露 GUI-ready 工作台输入输出并更新文档

**Files:**
- Modify: `publish.py`
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `docs/manual-validation/local-publish-engine-phase1.md`
- Optional Create: `docs/manual-validation/non-wechat-cover-checklist.md`

- [ ] **Step 1: 先写最小结果断言**

如果当前测试不足，给 `tests/test_engine_pipeline.py` 或新测试补 1 个断言：

```python
def test_publish_pipeline_result_contains_template_and_cover_metadata():
    result = results[0]
    assert result["theme_name"] == "midnight"
    assert result["cover_path"].endswith(".png")
```

- [ ] **Step 2: 让 CLI 输出 GUI-ready 元数据**

主入口最终结果里至少带上：

- `article_id`
- `theme_name`
- `template_mode`
- `cover_path`
- `platform`
- `status`
- `error_type`

后续 GUI 可以直接消费这些字段，不再自己拼接状态。

- [ ] **Step 3: 更新文档**

同步更新：

- `README.md`：新增导入方式、模板模式、非微信平台封面策略
- `README_EN.md`：同步英文说明
- `docs/manual-validation/local-publish-engine-phase1.md`：补非微信封面验证矩阵

- [ ] **Step 4: 跑本轮完整回归**

Run: `python3 -m unittest`
Expected: PASS

- [ ] **Step 5: 做一次最小人工验证**

至少验证：

1. 单篇 `Markdown` + 默认模板 + 非微信封面分配
2. 目录批量 + 随机主题分配
3. 一个浏览器平台的指定封面发布/草稿链路
4. 封面池为空时的报错或警告

记录结果到手工验证文档，再进入下一轮 GUI 桌面壳实现。

## Recovery Test Note

虽然本轮不展开完整 GUI 恢复界面，但涉及 `session` 的改动必须至少补 1 组回归用例，覆盖：

- 中断后恢复时，已分配的主题和封面不会被重新随机化
- 跳过已成功项后，未执行项仍沿用原分配结果
- 恢复执行时结果输出中的 `theme_name` / `cover_path` 与首次执行一致

## Scope Notes

- 本轮不直接起 `Tauri` 工程，避免一边补核心引擎一边引入第二套前端/桌面工程，导致范围失控。
- 本轮交付的是“GUI-ready engine + workbench contract + browser platform cover support”。
- 真正的桌面工作台、设置中心、预览页和打包流程，放在这轮代码稳定后单独起下一份实现计划。
- 根目录 `*_publisher.py` 继续作为兼容 CLI 入口，执行逻辑以 `tiandi_engine` 与共享服务为准，不新增第二套并行实现。
