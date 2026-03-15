# 批量发布与封面规范

## 适用目录

默认文章目录：

`/Users/wizard/work_2025/tiandiworkspace/拆解后文章`

`publish.py` 现在支持直接传目录，会按文件名排序批量执行。

## 文件命名规范

- Markdown 文件建议保持 `11-06_标题.md` 这样的前缀格式，便于排序。
- 发布时会自动去掉前缀，只保留真实标题。
- 如果正文第一行是 `# 标题`，则优先使用正文里的标题。

## 封面规范

- 比例：`1.35:1`
- 风格：清新、干净、雅致
- 要求：和文章主题一致，不要强营销感，不要过度艳丽
- 优先级：如果文章已有合适首图，可复用；如果没有，再补封面

## 封面提示词建议

可按下面模板生成：

```text
为一篇中文观点文章生成封面图，画面比例 1.35:1，整体风格清新、克制、雅致、有思想感，适合知识类自媒体文章封面。不要出现营销海报感，不要大字报，不要夸张表情，不要低俗配色。主体画面要贴合文章标题《{标题}》的含义，用具象但含蓄的视觉隐喻表达主题，背景简洁，有留白，适合后续平台裁切。
```

## 微信配置

仓库不提交真实密钥，请在项目根目录自行创建：

`secrets.env`

内容格式：

```env
WECHAT_APPID=你的公众号appid
WECHAT_SECRET=你的公众号secret
```

当前代码库里提供了模板文件：

`secrets.env.example`

## 批量发布命令

批量正式发布：

```bash
python3 publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode publish --continue-on-error
```

只跑前 5 篇：

```bash
python3 publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode draft --limit 5
```

跳过前 10 篇，从后面继续：

```bash
python3 publish.py "/Users/wizard/work_2025/tiandiworkspace/拆解后文章" --platform all --mode publish --offset 10 --continue-on-error
```

## 当前已知平台约束

- 微信公众号：必须先正确配置 `WECHAT_APPID` 和 `WECHAT_SECRET`
- 简书：公开文章存在每日发布次数限制
- 知乎、头条号、一点号：依赖当前远程调试 Chrome 的登录态
- `publish.py` 在真正执行前会先做预检，提前拦截明显不可执行的平台状态

## 推荐执行方式

1. 先打开开启了 Remote Debugging 的同一个 Chrome 实例
2. 确认知乎、头条号、简书、一点号都在这个实例里保持登录
3. 先用 `--mode draft` 小批量试跑
4. 确认页面正常后，再切 `--mode publish`
