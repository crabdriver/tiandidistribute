# 浏览器平台真实发布与 Smoke 验证记录

日期：2026-03-28

## 当前结论

本页现在同时保留两部分信息：

- 上半部分是本轮已经完成的正式发布 / 定时发布验收结论
- 下半部分保留早期 draft smoke 与逐步修复过程，方便回溯

当前功能主线验收结果：

| 平台 | 模式 | 结果 | 备注 |
| --- | --- | --- | --- |
| 微信 | draft | 通过 | 产品边界仍为“写入草稿”，不纳入正式发布主线 |
| 知乎 | publish | 通过 | 正式发布成功 |
| 头条号 | publish | 通过 | 正式发布成功 |
| 头条号 | publish + scheduled | 通过 | 成功写入 `scheduled` 状态 |
| 一点号 | publish | 通过 | 正式发布成功 |
| 简书 | publish | 通过 | 不走封面与 AI 声明，最小正式发布链路通过 |

本轮用于真实验收的测试文章建议固定为：

- `docs/manual-validation/test-articles/2026-03-28-zhihu-publish.md`
- `docs/manual-validation/test-articles/2026-03-28-toutiao-publish.md`
- `docs/manual-validation/test-articles/2026-03-28-yidian-publish.md`
- `docs/manual-validation/test-articles/2026-03-28-jianshu-publish.md`
- `docs/manual-validation/test-articles/2026-03-28-toutiao-scheduled.md`

本轮新增或确认收口的关键点：

- 头条号任务级 `scheduled_publish_at` 已打通桌面前端、bridge、runner、平台脚本与结果状态
- 头条号定时发布改为适配真实下拉控件，而不是假设页面存在可写 `datetime-local` 输入框
- 头条号封面上传已兼容动态 file input、确认按钮延迟启用，以及明显无效占位图过滤
- 简书已从封面分配平台集合中移除，避免“平台不支持但规划层仍强塞封面”
- 托管浏览器重启后自动补齐平台标签页已通过真实会话复核

推荐把本页和 `docs/manual-validation/2026-03-28-functional-freeze-checklist.md` 一起作为“打包前功能冻结”依据。

## 目标

为知乎、头条号、一点号整理一份最小 smoke 验证路径，确保后续在真实登录环境中可以快速确认以下关键链路：

- 编辑器页面可进入
- 标题可写入
- 正文可注入
- 预检提示清晰
- 草稿保存链路可人工确认

## 本轮边界

- 本轮已完成本地工程侧验证：Windows/CDP 路径策略、恢复状态、配置 warning、repo root / Python 诊断、快照与历史容错。
- 本轮已在用户协助下，直接对已登录真实站点执行草稿写入验证。
- 已补跑知乎、头条号、一点号的“带封面 + AI 声明 + 草稿链路”，以及简书的最小草稿链路。

## 本轮已完成的本地验证

- `python3 -m unittest tests.test_engine_results_errors tests.test_engine_workbench_bridge tests.test_platform_contracts tests.test_publish_preflight -v`
- `node --test tests/test_live_cdp_ws_resolver.mjs`
- `cd desktop && npm test`
- `cd desktop && npm run build`

结果：以上命令在本轮整改后均返回 `0`，说明“托管浏览器会话 + 发布选项合同 + 前端最小入口 + 失败提示”已经通过工程侧验证。

## 本轮真实 smoke 尝试

- 样例文章：`docs/manual-validation/browser-smoke-sample.md`、`docs/manual-validation/sample-article.md`
- 临时测试图：
  - `covers/ordo-smoke-temp-cover-wide.png`
  - `covers/ordo-smoke-temp-cover-1920x1080.png`
- 第一次执行命令：

```bash
python3 publish.py "docs/manual-validation/browser-smoke-sample.md" \
  --platform zhihu,toutiao,yidian \
  --mode draft \
  --no-auto-launch \
  --no-auto-open \
  --no-warmup
```

- 第一次结果：在进入平台级标题/正文注入前即被统一预检阻断，报错为 `没有检测到可用的 Chrome 标签页，请先打开 Chrome 并启用远程调试`。
- 后续动作：手动调用 Ordo 的浏览器拉起逻辑，强制打开知乎 / 头条号 / 一点号写作页，然后在主工作区补跑默认 `auto` 组合。
- 第二次执行命令：

```bash
python3 publish.py "docs/manual-validation/browser-smoke-sample.md" \
  --platform zhihu,toutiao,yidian \
  --mode draft \
  --continue-on-error
```

- 第二次结果：
  - 远程调试 Chrome 标签页已可见，三平台都成功进入写作页。
  - 当前 CDP 来源仍显示为 `Library/Application Support/Google/Chrome/DevToolsActivePort`，说明这轮更接近“系统 Chrome / profile 线索已可用”，还不能宣称“托管会话已完全稳定复用”。
  - 知乎：标题 / 正文注入成功，但 `包含 AI 辅助创作` 选项未被脚本正确识别。
  - 头条号：标题 / 正文注入成功，`无封面` 与 `引用AI` 已生效，但未检测到草稿提示。
  - 一点号：标题 / 正文注入成功，但 `内容由AI生成` 勾选失败。
- 第三次执行命令（逐平台真实补跑）：

```bash
PUBLISH_TARGET_ZHIHU=75B9BB57 python3 zhihu_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover "covers/ordo-smoke-temp-cover.png" \
  --cover-mode force_on \
  --ai-declaration-mode auto

PUBLISH_TARGET_TOUTIAO=E272DB86 python3 toutiao_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover "covers/ordo-smoke-temp-cover-wide.png" \
  --cover-mode force_on \
  --ai-declaration-mode auto

PUBLISH_TARGET_YIDIAN=3940C8D7 python3 yidian_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover "covers/ordo-smoke-temp-cover-1920x1080.png" \
  --cover-mode force_on \
  --ai-declaration-mode auto

python3 jianshu_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover-mode force_off \
  --ai-declaration-mode force_off
```

- 第三次结果：
  - 知乎：临时测试图可注入，`包含 AI 辅助创作` 已识别为选中态，草稿写入成功。
  - 头条号：单图封面上传成功，`引用AI` 保持勾选，草稿链路通过。
  - 一点号：`内容由AI生成` 识别与校验通过；使用 `1920x1080` 测试图后，单图封面链路通过，草稿写入成功。
  - 简书：在显式关闭封面 / AI 声明选项下，标题正文注入与草稿链路通过。
- 第四次执行命令（`force_off` 与会话复用复核）：

```bash
PUBLISH_TARGET_ZHIHU=75B9BB57 python3 zhihu_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover-mode force_off \
  --ai-declaration-mode force_off

PUBLISH_TARGET_TOUTIAO=E272DB86 python3 toutiao_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover-mode force_off \
  --ai-declaration-mode force_off

PUBLISH_TARGET_YIDIAN=3940C8D7 python3 yidian_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover-mode force_off \
  --ai-declaration-mode force_off

python3 jianshu_publisher.py "docs/manual-validation/sample-article.md" \
  --mode draft \
  --cover-mode force_off \
  --ai-declaration-mode force_off
```

- 第四次结果：
  - 知乎：在 fresh `write` 页上，`force_off` 后页面保持 `添加文章封面` 空态，声明值为 `无声明`，草稿写入成功。
  - 头条号：`force_off` 后真实页面已切到 `无封面`，且 `引用AI` 未勾选，草稿写入成功。
  - 一点号：首次复核发现 reused draft 上 `force_off` 只是“跳过设置”，未主动清理旧状态；随后已修复为显式切到 `无需声明` 与 `默认` 封面，并重新通过真实 draft smoke。
  - 简书：`force_off` 维持最小草稿链路通过。
- 会话复用复核：
  - 使用当前已登录标签页直接执行 `run_preflight_checks(platforms=['zhihu','toutiao','yidian','jianshu'], mode='draft', cover_mode='force_off')`
  - 返回 `blockers=[]`
  - 唯一 warning 仍为 `当前 CDP 连接来源：Library/Application Support/Google/Chrome/DevToolsActivePort`
  - 说明当前会话无需重新登录即可继续通过预检，但当前仍然是系统 Chrome 调试端口来源，而非单独托管端口证明

## 执行前检查

1. 使用同一个启用远程调试的 Chrome/Chromium 实例。
2. 在该实例中确认知乎、头条号、一点号都已登录。
3. 打开桌面工作台，确认执行区出现 Chrome 远程调试和登录态提示。
4. 确认顶部已显示当前实际 `Repo Root` 与 `Python` 路径。
5. 若 `config.json` 损坏，桌面工作台或 CLI 预检应直接提示解析 warning。

## 本轮协作验收重点

本轮真实站点验收只收敛三件事：

1. 托管浏览器首次登录后，后续是否无需重复授权即可复用。
2. 三平台是否能进入编辑器并完成最小草稿保存。
3. 当前任务级发布选项是否真的影响真实页面行为：
   - `cover_mode`: `auto` / `force_on` / `force_off`
   - `ai_declaration_mode`: `auto` / `force_on` / `force_off`

推荐按以下三轮补记录：

| 轮次 | 目标 | 推荐命令 / 配置 |
| --- | --- | --- |
| A | 复核当前默认行为是否仍生效 | 工作台保持 `封面: 自动`、`AI 声明: 自动`，或 CLI 使用默认值 |
| B | 验证显式关闭是否生效 | `--cover-mode force_off --ai-declaration-mode force_off` |
| C | 验证显式开启是否生效 | `--cover-mode force_on --ai-declaration-mode auto/force_on`，并准备满足平台要求的测试图（如一点号建议 `1920x1080`） |

## 平台最小 Smoke 清单

| 平台 | 入口 URL | 最小步骤 | 本轮记录 |
| --- | --- | --- | --- |
| 知乎 | `https://zhuanlan.zhihu.com/write` | 1. 打开编辑器 2. 导入单篇内容 3. 标题注入 4. 正文注入 5. 检查 AI 声明与封面逻辑 6. 存草稿 | 修复后真实 smoke 已通过：临时封面注入成功，`包含 AI 辅助创作` 已生效，草稿写入成功 |
| 头条号 | `https://mp.toutiao.com/profile_v4/graphic/publish` | 1. 打开编辑器 2. 导入单篇内容 3. 标题注入 4. 正文注入 5. 检查单图封面与 AI 声明 6. 存草稿 | 修复后真实 smoke 已通过：单图封面上传成功，`引用AI` 已生效，草稿提示已识别 |
| 一点号 | `https://mp.yidianzixun.com/#/Writing/articleEditor` | 1. 打开编辑器 2. 导入单篇内容 3. 标题注入 4. 正文注入 5. 检查单图封面与 AI 声明 6. 存草稿 | 修复后真实 smoke 已通过：`内容由AI生成` 勾选成功，使用 `1920x1080` 测试图时单图封面链路通过 |
| 简书 | `https://www.jianshu.com/writer#/` | 1. 打开写作页 2. 新建文章 3. 标题注入 4. Markdown 源码注入 5. 最小草稿链路校验 | 本轮最小 smoke 已通过：在 `cover_mode=force_off`、`ai_declaration_mode=force_off` 下，标题正文注入与草稿生成成功 |

## 结果判定标准

### Smoke 通过

- 平台编辑器成功进入，且不是停留在登录页、内容管理页或空白页。
- 标题写入后可立即从页面读取到目标标题。
- 正文注入后能从编辑器读取到非零正文长度。
- 平台特有设置可定位并完成最小校验：
  - 知乎：`包含 AI 辅助创作`
  - 头条号：`单图` 封面 + `引用AI`
  - 一点号：`单图` 封面 + `内容由AI生成`
- 草稿保存动作完成后，页面出现明确草稿成功信号，或至少能看到与草稿态一致的结果文案。

### 仅预检通过

- Chrome 远程调试已连通。
- 目标平台标签页存在并已登录。
- 编辑器入口 URL 正确，但本轮没有执行标题/正文注入和草稿保存。

### 功能项未生效

- 已成功进入编辑器，并完成标题/正文注入。
- 但本轮选定的封面策略或 AI 声明策略没有按预期反映到真实页面。
- 常见表现：
  - `force_off` 仍然被平台脚本或页面默认逻辑强行带出封面 / 声明
  - `force_on` 未真正上传封面、未真正勾选目标声明
  - 平台不支持当前选项，但 UI / 文档没有给出回退说明

### Smoke 失败

- 无法进入编辑器，或进入后页面缺少标题/正文输入区域。
- 标题写入后页面回读为空或不匹配。
- 正文注入后正文长度仍为 0，或编辑器内容明显未更新。
- 平台特有设置找不到、点击无效，或校验值不匹配。
- 草稿保存按钮不可点击、点击后无成功信号，或页面直接暴露登录/平台结构异常。

## 三平台最小检查表

### 知乎

1. 打开 `https://zhuanlan.zhihu.com/write`。
2. 确认标题框与正文编辑器同时存在。
3. 导入单篇文章并执行标题注入。
4. 回读标题，确认与预期一致。
5. 执行正文注入，并确认 `bodyLength > 0`。
6. 如本轮包含封面，确认封面控件可注入文件。
7. 展开发布设置，确认 `创作声明` 可切换到 `包含 AI 辅助创作`。
8. 使用 `draft` 模式后，确认页面出现 `草稿` / `已保存` / `保存成功` / `正在保存` / `已自动保存` 之一。

失败判定：

- 未进入写作页，或标题框/正文编辑器缺失。
- 创作声明下拉框不存在，或声明值无法校验为目标文案。
- draft 模式下长时间无任何保存态反馈。

### 头条号

1. 打开 `https://mp.toutiao.com/profile_v4/graphic/publish`。
2. 确认标题框与 `.ProseMirror` 编辑器存在。
3. 导入单篇文章并执行标题注入。
4. 回读标题，确认与预期一致。
5. 执行正文注入，并确认 `bodyLength > 0`。
6. 如本轮包含封面，确认 `展示封面` 已切到 `单图`，且封面上传后能看到预览或成功信号。
7. 展开 `作品声明`，确认 `引用AI` 已勾选。
8. 使用 `draft` 模式后，确认页面出现 `草稿已保存`、`草稿将自动保存` 或 `草稿保存中...`。

失败判定：

- 仍停留在非图文编辑器页面，或标题/正文控件缺失。
- `单图` 无法选中，或封面上传后无预览/成功信号。
- `引用AI` 找不到或勾选失败。
- draft 模式下没有任何草稿保存提示。

### 一点号

1. 打开 `https://mp.yidianzixun.com/#/Writing/articleEditor`。
2. 确认标题框 `input.post-title` 与正文编辑器 `.editor-content[contenteditable='true']` 存在。
3. 若页面停留在内容管理或审核中视图，确认可点击 `发文章` / `发布` 回到编辑器。
4. 导入单篇文章并执行标题注入。
5. 回读标题，确认与预期一致。
6. 执行正文注入，并确认 `bodyLength > 0`。
7. 如本轮包含封面，确认封面类型已切到 `单图`，且上传后出现预览或成功状态。
8. 确认内容声明可切换到 `内容由AI生成`。
9. 使用 `draft` 模式后，确认 `存草稿` 可点击且页面反馈成功。

失败判定：

- 无法切回编辑器，或始终停留在内容管理/审核中态。
- 标题或正文输入区缺失。
- `单图` 封面未选中，或声明项 `内容由AI生成` 无法勾选。
- `存草稿` 按钮不可点击，或点击后无明确成功反馈。

## 验收记录模板

后续在真实环境补跑时，建议直接追加以下记录：

| 日期 | 平台 | 会话复用 | 结果 | 封面模式 | 封面结果 | AI 声明模式 | AI 声明结果 | 草稿结果 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-03-28 | 知乎 | 未验证 | 阻塞 | auto | 未验证 | auto | 未验证 | 未验证 | 执行入口已触发，但当前会话没有远程调试 Chrome 标签页 |
| 2026-03-28 | 头条号 | 未验证 | 阻塞 | auto | 未验证 | auto | 未验证 | 未验证 | 执行入口已触发，但当前会话没有远程调试 Chrome 标签页 |
| 2026-03-28 | 一点号 | 未验证 | 阻塞 | auto | 未验证 | auto | 未验证 | 未验证 | 执行入口已触发，但当前会话没有远程调试 Chrome 标签页 |
| 2026-03-28 | 知乎 | 待继续观察 | 功能项未生效 | auto | 本轮未验证自定义封面（封面池为空） | auto | 未生效 | 未执行到草稿确认 | 标题 / 正文注入成功，卡在 `包含 AI 辅助创作` 选项未被脚本识别 |
| 2026-03-28 | 头条号 | 待继续观察 | Smoke 失败 | auto | `无封面` 已生效 | auto | `引用AI` 已生效 | 失败 | 标题 / 正文注入成功，但未检测到草稿提示 |
| 2026-03-28 | 一点号 | 待继续观察 | 功能项未生效 | auto | 本轮未验证自定义封面（在声明步骤前失败） | auto | 未生效 | 未执行到草稿确认 | 标题 / 正文注入成功，但 `内容由AI生成` 勾选失败 |
| 2026-03-28 | 知乎 | 待继续观察 | Smoke 通过 | force_on | 已生效 | auto | 已生效 | 成功 | 使用临时图 `ordo-smoke-temp-cover.png`，当前 URL 为草稿编辑页 |
| 2026-03-28 | 头条号 | 待继续观察 | Smoke 通过 | force_on | 单图 | auto | 引用AI | 成功 | 使用临时图 `ordo-smoke-temp-cover-wide.png`，上传弹层需识别 `已上传 1 张图片` 并确认 |
| 2026-03-28 | 一点号 | 待继续观察 | Smoke 通过 | force_on | 单图 | auto | 内容由AI生成 | 成功 | 使用 `1920x1080` 临时图 `ordo-smoke-temp-cover-1920x1080.png` 后链路通过 |
| 2026-03-28 | 简书 | 待继续观察 | Smoke 通过 | force_off | 平台未启用封面 | force_off | 已跳过 | 成功 | 最小 smoke，仅验证新建文章、标题正文注入与草稿链路 |
| 2026-03-28 | 知乎 | 是 | Smoke 通过 | force_off | 空态 / 未注入自定义封面 | force_off | 无声明 | 成功 | fresh `write` 页上复核，脚本跳过设置后页面保持无封面、无声明 |
| 2026-03-28 | 头条号 | 是 | Smoke 通过 | force_off | 无封面 | force_off | 未勾选引用AI | 成功 | 真实页面确认 `无封面` 被选中，`引用AI` 未勾选 |
| 2026-03-28 | 一点号 | 是 | Smoke 通过 | force_off | 平台默认封面 | force_off | 无需声明 | 成功 | 初次复核发现旧状态残留，已补脚本：draft 模式下显式回退 `默认` + `无需声明` 后复跑通过 |
| 2026-03-28 | 简书 | 是 | Smoke 通过 | force_off | 平台未启用封面 | force_off | 已跳过 | 成功 | 与前一轮相同，最小草稿链路持续通过 |
| YYYY-MM-DD | 知乎 | 是 / 否 | Smoke 通过 / 仅预检通过 / 功能项未生效 / Smoke 失败 | auto / force_on / force_off | 已生效 / 未生效 / 平台回退 | auto / force_on / force_off | 已生效 / 未生效 | 成功 / 失败 | 记录页面 URL、草稿提示、异常文案 |
| YYYY-MM-DD | 头条号 | 是 / 否 | Smoke 通过 / 仅预检通过 / 功能项未生效 / Smoke 失败 | auto / force_on / force_off | 单图 / 无封面 / 未生效 | auto / force_on / force_off | 引用AI / 未生效 | 成功 / 失败 | 记录页面 URL、草稿提示、异常文案 |
| YYYY-MM-DD | 一点号 | 是 / 否 | Smoke 通过 / 仅预检通过 / 功能项未生效 / Smoke 失败 | auto / force_on / force_off | 单图 / 平台默认封面 / 未生效 | auto / force_on / force_off | 内容由AI生成 / 未生效 | 成功 / 失败 | 如 `force_off` 仍回退默认封面，请在此注明 |
| YYYY-MM-DD | 简书 | 是 / 否 | Smoke 通过 / 仅预检通过 / Smoke 失败 | auto / force_off | 平台未启用封面 | auto / force_off | 已跳过 / 未生效 | 成功 / 失败 | 记录是否新建文章成功、是否进入编辑器、是否生成草稿 |

## 本轮结论

- 工程侧高风险整改已覆盖到 Windows/CDP、恢复保护、配置一致性与历史容错。
- 浏览器平台的真实 smoke 清单已经落文档，并补到了三类真实记录：入口阻塞、第一次真实失败点、修复后的真实通过结果。
- 本轮已补完 `force_off` 真实 smoke，并额外修复了一点号在 reused draft 上“跳过设置但不清旧状态”的问题。
- 发布选项层面已经新增 `封面 / AI 声明` 的任务级显式开关，并把“平台回退说明”纳入验收模板。
- 本轮已完成知乎 / 头条号 / 一点号的 `force_on` 与 `force_off` 两组真实验证，以及简书最小 smoke；前一轮的三个真实失败点和一点号 `force_off` 清理缺口都已修通。
- 会话复用层面，当前已可在不重新登录的情况下持续通过预检；剩余待观察点是后续是否能稳定切换到“托管浏览器独立端口”来源。
