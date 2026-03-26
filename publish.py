import argparse
import csv
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CDP_SCRIPT = BASE_DIR / "live_cdp.mjs"
WORKBENCH_FILE = BASE_DIR / ".publish-workbench.json"
COVERS_DIR = BASE_DIR / "covers"
PUBLISH_RECORDS_FILE = BASE_DIR / "publish_records.csv"
CHROME_APP_CANDIDATES = [
    "Google Chrome",
    "Google Chrome Beta",
    "Google Chrome Dev",
    "Chromium",
]
PLATFORM_SCRIPTS = {
    "wechat": "wechat_publisher.py",
    "zhihu": "zhihu_publisher.py",
    "toutiao": "toutiao_publisher.py",
    "jianshu": "jianshu_publisher.py",
    "yidian": "yidian_publisher.py",
}
PLATFORM_URLS = {
    "zhihu": "https://zhuanlan.zhihu.com/write",
    "toutiao": "https://mp.toutiao.com/profile_v4/graphic/publish",
    "jianshu": "https://www.jianshu.com/writer#/",
    "yidian": "https://mp.yidianzixun.com/#/Writing/articleEditor",
}
PLATFORM_MATCHES = {
    "zhihu": ["zhihu.com"],
    "toutiao": ["mp.toutiao.com"],
    "jianshu": ["jianshu.com/writer"],
    "yidian": ["mp.yidianzixun.com"],
}
DEFAULT_PLATFORMS = ["wechat", "zhihu", "toutiao", "jianshu", "yidian"]
BROWSER_PLATFORMS = list(PLATFORM_URLS.keys())


def parse_platforms(raw_value):
    value = (raw_value or "all").strip().lower()
    if value == "all":
        return DEFAULT_PLATFORMS

    platforms = []
    for item in value.split(","):
        platform = item.strip()
        if not platform:
            continue
        if platform not in PLATFORM_SCRIPTS:
            supported = ", ".join(sorted(PLATFORM_SCRIPTS))
            raise ValueError(f"不支持的平台: {platform}，可选: {supported}, all")
        if platform not in platforms:
            platforms.append(platform)
    if not platforms:
        raise ValueError("至少要指定一个平台")
    return platforms


def collect_markdown_files(raw_path, offset=0, limit=None):
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    if path.is_file():
        files = [path]
    else:
        files = sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".md")

    if not files:
        raise ValueError(f"没有找到 Markdown 文件: {path}")

    if offset:
        files = files[offset:]
    if limit is not None:
        files = files[:limit]

    if not files:
        raise ValueError("筛选后没有可执行的 Markdown 文件")

    return files


def load_simple_env_file(env_path):
    values = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_project_config():
    path = BASE_DIR / "config.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def get_wechat_config_status():
    env_file = BASE_DIR / "secrets.env"
    file_values = load_simple_env_file(env_file)
    config = load_project_config()
    appid = os.environ.get("WECHAT_APPID") or file_values.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET") or file_values.get("WECHAT_SECRET")
    cover_files = sorted(COVERS_DIR.glob("cover_*.png"))
    placeholder_markers = ("CHANGE_ME", "your_", "你的", "example", "appid_here")

    def is_real(value):
        if not value:
            return False
        upper_value = value.upper()
        return not any(marker.upper() in upper_value for marker in placeholder_markers)

    ai_key = (
        config.get("secrets", {}).get("api_key")
        or config.get("ai", {}).get("api_key")
        or (os.environ.get("OPENROUTER_API_KEY") if config else None)
    )
    ai_base_url = config.get("settings", {}).get("base_url")
    ai_model = config.get("settings", {}).get("model")
    prefer_ai_first = config.get("cover", {}).get("prefer_ai_first", True)

    return {
        "env_file_exists": env_file.exists(),
        "appid_ready": is_real(appid),
        "secret_ready": is_real(secret),
        "covers_ready": len(cover_files) >= 1,
        "cover_count": len(cover_files),
        "ai_cover_ready": prefer_ai_first and is_real(ai_key) and is_real(ai_base_url) and is_real(ai_model),
    }


def get_page_text_snippet(target_id, limit=2000):
    expression = f"(() => (document.body.innerText || '').slice(0, {limit}))()"
    return run_cdp("eval", target_id, expression)


def run_preflight_checks(platforms, mode, workbench):
    blockers = []
    warnings = []

    if "wechat" in platforms:
        wechat = get_wechat_config_status()
        if not wechat["appid_ready"] or not wechat["secret_ready"]:
            blockers.append("微信公众号缺少 `WECHAT_APPID` 或 `WECHAT_SECRET`，请先配置 `secrets.env`")
        if not wechat["covers_ready"] and not wechat["ai_cover_ready"]:
            blockers.append("微信公众号缺少可用封面：请配置 AI 封面所需的 `config.json`，或准备 `covers/cover_*.png`")
        elif not wechat["covers_ready"] and wechat["ai_cover_ready"]:
            warnings.append("未检测到本地默认封面，当前将默认优先使用 AI 封面生成能力")

    if mode == "publish" and "jianshu" in platforms:
        jianshu_target = workbench.get("jianshu")
        if jianshu_target:
            try:
                body = get_page_text_snippet(jianshu_target, limit=3000)
                if "每天只能发布 2 篇公开文章" in body:
                    blockers.append("简书今天已达到公开文章发布上限（每天最多 2 篇）")
            except subprocess.CalledProcessError:
                warnings.append("简书预检读取失败，发布时再做实际判断")

    for platform in platforms:
        if platform in BROWSER_PLATFORMS and not workbench.get(platform):
            blockers.append(f"未找到 `{platform}` 的可用标签页，请先在当前远程调试 Chrome 中打开并登录")

    return blockers, warnings


def run_platform(platform, markdown_file, mode, theme_name=None):
    script_name = PLATFORM_SCRIPTS[platform]
    script_path = BASE_DIR / script_name
    command = [sys.executable, str(script_path), markdown_file, "--mode", mode]
    if platform == "wechat" and theme_name:
        command.extend(["--theme", theme_name])
        
    env = os.environ.copy()
    bound_targets = load_workbench_targets()
    target = bound_targets.get(platform)
    if target:
        env[f"PUBLISH_TARGET_{platform.upper()}"] = target

    result = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        text=True,
        capture_output=True,
        env=env,
        timeout=180,
    )
    return {
        "platform": platform,
        "script": script_name,
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def classify_result(result):
    output = "\n".join(filter(None, [result.get("stdout", ""), result.get("stderr", "")]))
    platform = result["platform"]
    mode = result.get("mode")
    limit_markers = [
        "达到发布上限",
        "发布上限",
        "次数上限",
        "每天最多",
        "请明天再来",
        "未来7天",
        "审核通过前你将无法继续编辑",
        "暂不发布",
        "时间限制",
        "排期",
    ]

    if any(marker in output for marker in limit_markers):
        return "limit_reached"

    if result["returncode"] != 0:
        if "草稿" in output:
            return "draft_only"
        return "failed"

    if platform == "wechat":
        if "已存在同标题文章" in output:
            return "skipped_existing"
        if "已发布到微信公众号" in output:
            return "published"
        if "已写入微信公众号草稿" in output:
            return "draft_only"
        return "success_unknown"

    if mode == "publish":
        publish_markers = {
            "zhihu": "已发布到知乎",
            "toutiao": "已发布到头条号",
            "jianshu": "已发布到简书",
            "yidian": "已发布成功",
        }
        if publish_markers.get(platform) and publish_markers[platform] in output:
            return "published"
        return "failed"

    draft_markers = {
        "zhihu": "已写入知乎草稿页",
        "toutiao": "已写入头条草稿页",
        "jianshu": "已生成简书草稿",
        "yidian": "已存草稿",
    }
    if draft_markers.get(platform) and draft_markers[platform] in output:
        return "draft_only"
    return "success_unknown"


def append_publish_record(result):
    file_exists = PUBLISH_RECORDS_FILE.exists()
    with PUBLISH_RECORDS_FILE.open("a", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "timestamp",
                "article",
                "platform",
                "mode",
                "status",
                "returncode",
                "stdout",
                "stderr",
            ],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "article": result.get("article", ""),
                "platform": result["platform"],
                "mode": result.get("mode", ""),
                "status": result.get("status", ""),
                "returncode": result["returncode"],
                "stdout": result.get("stdout", "").replace("\n", "\\n"),
                "stderr": result.get("stderr", "").replace("\n", "\\n"),
            }
        )


def print_result(result):
    platform = result["platform"]
    print(f"===== {platform} =====")
    if result["stdout"]:
        print(result["stdout"])
    if result["stderr"]:
        print(result["stderr"])
    print(f"[EXIT] {result['returncode']}")


def run_cdp(*args):
    command = ["node", str(CDP_SCRIPT), *args]
    return subprocess.run(
        command,
        cwd=str(BASE_DIR),
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    ).stdout.strip()


def load_workbench_targets():
    if not WORKBENCH_FILE.exists():
        return {}
    return json.loads(WORKBENCH_FILE.read_text(encoding="utf-8"))


def save_workbench_targets(targets):
    WORKBENCH_FILE.write_text(
        json.dumps(targets, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def launch_chrome(urls):
    last_error = None
    for app_name in CHROME_APP_CANDIDATES:
        command = ["open", "-a", app_name]
        command.extend(urls or [])
        try:
            subprocess.run(
                command,
                cwd=str(BASE_DIR),
                text=True,
                capture_output=True,
                check=True,
            )
            return app_name
        except subprocess.CalledProcessError as exc:
            last_error = exc
    if last_error:
        raise RuntimeError("未找到可用的 Chrome/Chromium 应用，无法自动启动浏览器")
    raise RuntimeError("无法自动启动浏览器")


def list_tabs_or_none():
    try:
        return list_tabs()
    except subprocess.CalledProcessError:
        return None


def ensure_chrome_ready(platforms):
    tabs = list_tabs_or_none()
    if tabs is not None:
        return tabs, None

    urls = [PLATFORM_URLS[platform] for platform in platforms]
    app_name = launch_chrome(urls)

    deadline = time.time() + 20
    while time.time() < deadline:
        tabs = list_tabs_or_none()
        if tabs is not None:
            return tabs, app_name
        time.sleep(1)

    raise RuntimeError(
        f"已尝试自动启动 {app_name}，但仍无法连接 CDP。请确认 Chrome 远程调试已开启。"
    )


def list_tabs():
    output = run_cdp("list")
    tabs = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        tabs.append({"target": parts[0], "title": parts[1], "url": parts[2]})
    return tabs


def platform_tab_exists(platform, tabs):
    return any(
        any(match in tab["url"] for match in PLATFORM_MATCHES[platform])
        for tab in tabs
    )


def find_platform_target(platform, tabs):
    return next(
        (
            tab["target"]
            for tab in tabs
            if any(match in tab["url"] for match in PLATFORM_MATCHES[platform])
        ),
        None,
    )


def bind_workbench(platforms, tabs):
    # Browser platforms must keep reusing the same logged-in tab whenever possible.
    # Do not casually switch to a freshly opened tab, because it may belong to a
    # different Chrome session and lose the working login / CDP authorization chain.
    existing = load_workbench_targets()
    live_targets = {tab["target"] for tab in tabs}
    updated = {
        platform: target
        for platform, target in existing.items()
        if platform not in BROWSER_PLATFORMS or target in live_targets
    }

    for platform in platforms:
        if platform not in BROWSER_PLATFORMS:
            continue
        existing_target = updated.get(platform)
        if existing_target and existing_target in live_targets:
            continue

        target = find_platform_target(platform, tabs)
        if target:
            updated[platform] = target

    save_workbench_targets(updated)
    return updated


def open_missing_platform_tabs(platforms, auto_launch=True):
    browser_platforms = [platform for platform in platforms if platform in BROWSER_PLATFORMS]
    if not browser_platforms:
        return []

    if auto_launch:
        tabs, launched_app = ensure_chrome_ready(browser_platforms)
    else:
        tabs = list_tabs_or_none()
        launched_app = None
    if launched_app:
        print(f"[INFO] 已自动启动浏览器: {launched_app}")
    if not tabs:
        raise RuntimeError("没有检测到可用的 Chrome 标签页，请先打开 Chrome 并启用远程调试")

    base_target = tabs[0]["target"]
    missing_platforms = [platform for platform in browser_platforms if not platform_tab_exists(platform, tabs)]
    if not missing_platforms:
        return []

    js = " ".join(
        [f"window.open({PLATFORM_URLS[platform]!r}, '_blank');" for platform in missing_platforms]
    ) + " 'opened';"
    run_cdp("eval", base_target, js)
    time.sleep(1)
    return missing_platforms


def warm_platforms(platforms):
    workbench = load_workbench_targets()
    warmed = []
    for platform in platforms:
        if platform not in BROWSER_PLATFORMS:
            continue
        try:
            target = workbench.get(platform)
            if not target:
                tabs = list_tabs()
                target = find_platform_target(platform, tabs)
            if target:
                run_cdp("warm", target)
                warmed.append(platform)
        except subprocess.CalledProcessError:
            continue
    return warmed


def resolve_wechat_theme_mode(args, available_themes):
    if args.wechat_theme_mode == "random":
        return "random"
    if args.wechat_theme_mode == "fixed":
        return "fixed"
    if args.wechat_theme_mode == "prompt":
        return "prompt"
    if not sys.stdin.isatty() or not available_themes:
        return "fixed"
    return "prompt"


def resolve_wechat_theme_for_article(article_path, theme_mode, available_themes, fixed_theme):
    if theme_mode == "random" and available_themes:
        theme_name = random.choice(available_themes)
        print(f"  [INFO] 随机分配微信排版主题: {theme_name}")
        return theme_name
    if theme_mode == "prompt":
        ans = input(
            f"  请输入并为文章《{article_path.name}》指定微信排版主题 (直接回车默认 '{fixed_theme}'): "
        ).strip()
        return ans if ans else fixed_theme
    return fixed_theme


def main():
    parser = argparse.ArgumentParser(description="Publish one or many Markdown articles to multiple platforms.")
    parser.add_argument("markdown_path", help="Markdown 文件或目录路径")
    parser.add_argument(
        "--platform",
        default="all",
        help="平台列表，逗号分隔，可选 wechat,zhihu,toutiao,jianshu,yidian 或 all",
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "publish"],
        default="draft",
        help="draft 保存草稿；publish 正式发布",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="某个平台失败后继续执行后续平台",
    )
    parser.add_argument(
        "--no-auto-open",
        action="store_true",
        help="不自动补开缺失的平台标签页",
    )
    parser.add_argument(
        "--rebind-workbench",
        action="store_true",
        help="忽略旧的固定工作台绑定，按当前打开的标签页重新绑定",
    )
    parser.add_argument(
        "--no-auto-launch",
        action="store_true",
        help="检测不到浏览器/CDP 时不自动尝试启动 Chrome",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="不在执行前自动预热平台标签页",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="目录模式下最多处理多少篇文章",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="目录模式下跳过前多少篇文章",
    )
    parser.add_argument(
        "--wechat-theme",
        default="chinese",
        help="微信默认主题名，非交互模式下直接使用；默认 chinese",
    )
    parser.add_argument(
        "--wechat-theme-mode",
        choices=["auto", "prompt", "random", "fixed"],
        default="auto",
        help="微信主题分配方式：auto 自动判断；prompt 每篇手动输入；random 随机；fixed 固定使用 --wechat-theme",
    )
    args = parser.parse_args()

    platforms = parse_platforms(args.platform)
    article_paths = collect_markdown_files(args.markdown_path, offset=args.offset, limit=args.limit)
    results = []

    print(f"[INFO] 准备执行平台: {', '.join(platforms)}")
    print(f"[INFO] 模式: {args.mode}")
    print(f"[INFO] 本次文章数量: {len(article_paths)}")

    browser_platforms = [platform for platform in platforms if platform in BROWSER_PLATFORMS]
    tabs = []
    if browser_platforms:
        if args.no_auto_launch:
            tabs = list_tabs_or_none()
        else:
            tabs, launched_app = ensure_chrome_ready(browser_platforms)
            if launched_app:
                print(f"[INFO] 已自动启动浏览器: {launched_app}")

        if not tabs:
            raise RuntimeError("没有检测到可用的 Chrome 标签页，请先打开 Chrome 并启用远程调试")

    if not args.no_auto_open:
        opened = open_missing_platform_tabs(platforms, auto_launch=not args.no_auto_launch)
        if opened:
            print(f"[INFO] 已自动打开平台标签页: {', '.join(opened)}")
        if browser_platforms:
            tabs = list_tabs()

    if args.rebind_workbench and WORKBENCH_FILE.exists():
        WORKBENCH_FILE.unlink()

    workbench = bind_workbench(platforms, tabs)
    bound_platforms = [platform for platform in platforms if workbench.get(platform)]
    if bound_platforms:
        print(f"[INFO] 已绑定固定工作台标签页: {', '.join(bound_platforms)}")

    if not args.no_warmup:
        warmed = warm_platforms(platforms)
        if warmed:
            print(f"[INFO] 已自动预热平台标签页: {', '.join(warmed)}")

    blockers, warnings = run_preflight_checks(platforms, args.mode, workbench)
    for warning in warnings:
        print(f"[WARN] {warning}")
    for blocker in blockers:
        print(f"[BLOCK] {blocker}")
    if blockers:
        raise SystemExit(1)

    theme_mode = "fixed"
    available_themes = []
    if "wechat" in platforms:
        theme_dir = BASE_DIR / "themes"
        if theme_dir.exists():
            available_themes = sorted(f.stem for f in theme_dir.glob("*.json"))

        theme_mode = resolve_wechat_theme_mode(args, available_themes)
        if theme_mode == "prompt":
            while True:
                ans = input(
                    "\n请选择微信排版主题分配方式:\n1. 为每篇文章自定义主题 (手动输入)\n2. 为每篇文章随机分配主题\n3. 全部使用固定主题\n请选择 [1/2/3]: "
                ).strip()
                if ans == "1":
                    theme_mode = "prompt"
                    break
                if ans == "2":
                    theme_mode = "random"
                    break
                if ans == "3":
                    theme_mode = "fixed"
                    break

    for index, article_path in enumerate(article_paths, start=1):
        print(f"===== article {index}/{len(article_paths)} =====")
        print(article_path)

        for platform in platforms:
            theme_name = None
            if platform == "wechat":
                theme_name = resolve_wechat_theme_for_article(
                    article_path,
                    theme_mode,
                    available_themes,
                    args.wechat_theme,
                )

            result = run_platform(platform, str(article_path), args.mode, theme_name=theme_name)
            result["article"] = str(article_path)
            result["mode"] = args.mode
            result["status"] = classify_result(result)
            results.append(result)
            append_publish_record(result)
            print_result(result)

            if result["returncode"] != 0 and not args.continue_on_error:
                raise SystemExit(result["returncode"])

    failed = [item for item in results if item["returncode"] != 0]
    succeeded = [item for item in results if item["returncode"] == 0]

    print("===== summary =====")
    print(f"成功: {len(succeeded)}")
    print(f"失败: {len(failed)}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
