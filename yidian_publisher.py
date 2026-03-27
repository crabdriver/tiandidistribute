import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from markdown_utils import render_markdown_html


BASE_DIR = Path(__file__).resolve().parent
CDP_SCRIPT = BASE_DIR / "live_cdp.mjs"
YIDIAN_MATCH = "mp.yidianzixun.com"
YIDIAN_EDITOR_URL = "https://mp.yidianzixun.com/#/Writing/articleEditor"
YIDIAN_COVER_FILE_INPUT = ".upload-input"
YIDIAN_SINGLE_COVER_TEXT = "单图"
YIDIAN_AI_DECLARATION = "内容由AI生成"
AI_KEYWORDS = ["AI创作", "AI辅助", "AIGC", "人工智能生成", "AI生成", "AI工具", "使用AI"]


def clean_title(title):
    return re.sub(r"^\d{1,2}-\d{1,2}_", "", title).strip()


def run_cdp(command, *args, timeout=120):
    result = subprocess.run(
        ["node", str(CDP_SCRIPT), command, *args],
        cwd=str(BASE_DIR),
        text=True,
        capture_output=True,
        check=True,
        timeout=timeout,
    )
    return result.stdout.strip()


def normalize_ui_text(text):
    return "".join((text or "").split())


def list_yidian_targets():
    output = run_cdp("list")
    targets = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        target_id, _title, url = parts[0], parts[1], parts[2]
        if YIDIAN_MATCH in url:
            targets.append(target_id)
    return targets


def editor_ready(target_id, timeout_seconds=3):
    return wait_until(
        target_id,
        "(() => !!document.querySelector(\"input.post-title\") && !!document.querySelector(\".editor-content[contenteditable='true']\"))()",
        timeout_seconds=timeout_seconds,
        interval_seconds=1,
    )


def open_fresh_editor_tab(target_id):
    before_targets = set(list_yidian_targets())
    result = run_cdp(
        "eval",
        target_id,
        f"window.open({json.dumps(YIDIAN_EDITOR_URL, ensure_ascii=False)}, '_blank'); 'opened'",
    )
    if result != "opened":
        return None

    deadline = time.time() + 12
    while time.time() < deadline:
        current_targets = list_yidian_targets()
        for candidate in current_targets:
            if candidate not in before_targets and editor_ready(candidate, timeout_seconds=2):
                return candidate
        time.sleep(1)
    return None


def find_yidian_target():
    bound_target = os.environ.get("PUBLISH_TARGET_YIDIAN")
    if bound_target and editor_ready(bound_target, timeout_seconds=1):
        return bound_target

    targets = list_yidian_targets()
    for target_id in targets:
        if target_id == bound_target:
            continue
        if editor_ready(target_id, timeout_seconds=1):
            return target_id

    return bound_target or (targets[0] if targets else None)


def load_article(markdown_path):
    path = Path(markdown_path).expanduser().resolve()
    raw_text = path.read_text(encoding="utf-8")
    title = clean_title(path.stem)
    body = raw_text

    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = clean_title(stripped[2:].strip())
            body = raw_text.replace(line, "", 1).lstrip()
            break

    title = title[:64]
    html = render_markdown_html(body)
    return title, body, html, path


def wait_until(target_id, expression, timeout_seconds=20, interval_seconds=1):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run_cdp("eval", target_id, expression)
        if result == "true":
            return True
        time.sleep(interval_seconds)
    return False


def ensure_editor_ready(target_id):
    run_cdp("nav", target_id, YIDIAN_EDITOR_URL)
    if wait_for_button(target_id, "再写一篇", timeout_seconds=3, interval_seconds=1):
        action = click_action(target_id, "再写一篇")
        if action != "clicked":
            raise RuntimeError(f"一点号返回编辑器失败: {action}")
    ready = editor_ready(target_id, timeout_seconds=8)
    if ready:
        return target_id

    # 一点号偶尔停在“内容管理/审核中”视图，虽然 URL 还是编辑页，但需要手动点一次“发布/发文章”才能回到编辑器。
    reopen_result = run_cdp(
        "eval",
        target_id,
        """
(() => {
  const link = document.querySelector('a.editor')
    || Array.from(document.querySelectorAll('a')).find((el) => {
      const text = (el.innerText || '').trim();
      const href = el.getAttribute('href') || '';
      return text === '发文章' || text === '发布' || href === '#/Writing/articleEditor';
    });
  if (!link) return 'entry-not-found';
  link.click();
  return 'clicked';
})()
""".strip(),
    )
    if reopen_result != "clicked":
        raise RuntimeError(f"一点号无法切回编辑器: {reopen_result}")

    ready = editor_ready(target_id, timeout_seconds=10)
    if not ready:
        for candidate in list_yidian_targets():
            if candidate != target_id and editor_ready(candidate, timeout_seconds=2):
                return candidate
        fresh_target = open_fresh_editor_tab(target_id)
        if fresh_target:
            return fresh_target
        raise RuntimeError("一点号编辑器未就绪，请确认当前标签已登录并可进入发文页")
    return target_id


def inject_article(target_id, title, html):
    title_json = json.dumps(title, ensure_ascii=False)
    html_json = json.dumps(html, ensure_ascii=False)
    expression = f"""
(() => {{
  const title = {title_json};
  const html = {html_json};
  const titleInput = document.querySelector("input.post-title");
  const editor = document.querySelector(".editor-content[contenteditable='true']");
  if (!titleInput || !editor) {{
    return "missing-editor";
  }}

  const inputSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
  if (inputSetter) {{
    inputSetter.call(titleInput, title);
  }} else {{
    titleInput.value = title;
  }}
  titleInput.dispatchEvent(new Event("input", {{ bubbles: true }}));
  titleInput.dispatchEvent(new Event("change", {{ bubbles: true }}));

  editor.focus();
  editor.innerHTML = html;
  editor.dispatchEvent(new InputEvent("input", {{ bubbles: true, inputType: "insertFromPaste" }}));
  editor.dispatchEvent(new Event("keyup", {{ bubbles: true }}));
  editor.dispatchEvent(new Event("blur", {{ bubbles: true }}));

  return JSON.stringify({{
    title: titleInput.value,
    bodyLength: (editor.innerText || "").trim().length
  }});
}})()
"""
    return run_cdp("eval", target_id, expression)


def click_action(target_id, button_text):
    button_json = json.dumps(button_text, ensure_ascii=False)
    expression = f"""
(() => {{
  const text = {button_json};
  const button = Array.from(document.querySelectorAll("button")).find((btn) => btn.innerText.trim() === text);
  if (!button) {{
    return "button-not-found";
  }}
  if (button.disabled) {{
    return "button-disabled";
  }}
  button.click();
  return "clicked";
}})()
"""
    return run_cdp("eval", target_id, expression)


def apply_cover(target_id, cover_path):
    path = Path(cover_path).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"封面文件不存在: {path}")
    mode_result = select_cover_type(target_id, YIDIAN_SINGLE_COVER_TEXT)
    if not wait_for_cover_type(target_id, YIDIAN_SINGLE_COVER_TEXT, timeout_seconds=8):
        raise RuntimeError(f"一点号封面未切换到单图: {mode_result}")
    run_cdp("setfile", target_id, YIDIAN_COVER_FILE_INPUT, str(path))
    if not wait_for_cover_upload(target_id, timeout_seconds=12):
        raise RuntimeError(f"一点号封面上传后未检测到预览或成功状态: {path.name}")
    print(f"[INFO] 已向一点号封面上传控件注入文件: {path}")


def select_cover_type(target_id, option_text):
    option_json = json.dumps(option_text, ensure_ascii=False)
    expression = f"""
(() => {{
  const items = Array.from(document.querySelectorAll('.cover-type .item'));
  const targetItem = items.find((item) => (item.innerText || '').replace(/\s+/g, '') === {option_json}.replace(/\s+/g, ''));
  if (!targetItem) {{
    return 'cover-option-not-found';
  }}
  targetItem.click();
  return Array.from(document.querySelectorAll('.cover-type .item')).map((item) => ({{
    text: item.innerText.trim(),
    checked: item.classList.contains('checked')
  }}));
}})()
"""
    return run_cdp("eval", target_id, expression)


def wait_for_cover_type(target_id, option_text, timeout_seconds=10, interval_seconds=1):
    option_json = json.dumps(option_text, ensure_ascii=False)
    expression = f"""
(() => {{
  const items = Array.from(document.querySelectorAll('.cover-type .item'));
  const targetItem = items.find((item) => (item.innerText || '').replace(/\s+/g, '') === {option_json}.replace(/\s+/g, ''));
  return !!targetItem && targetItem.classList.contains('checked');
}})()
"""
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def select_default_cover(target_id):
    return select_cover_type(target_id, "默认")


def wait_for_default_cover(target_id, timeout_seconds=10, interval_seconds=1):
    return wait_for_cover_type(target_id, "默认", timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def wait_for_cover_upload(target_id, timeout_seconds=10, interval_seconds=1):
    expression = """
(() => {
  const root = document.querySelector('.cover-content, .cover-wrap, .cover-box, .cover-type') || document.body;
  const hasPreview = !!root.querySelector(
    'img, .cover-preview img, .preview img, .upload-list img, .cover-box img, [style*="background-image"]'
  );
  const bodyText = (root.innerText || document.body.innerText || '').replace(/\s+/g, '');
  const hasSuccessText = ['更换封面', '重新上传', '裁剪', '删除', '预览'].some(text => bodyText.includes(text));
  return hasPreview || hasSuccessText;
})()
"""
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def wait_for_button(target_id, button_text, timeout_seconds=10, interval_seconds=1):
    button_json = json.dumps(button_text, ensure_ascii=False)
    expression = f"""
(() => {{
  const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === {button_json});
  return !!btn && !btn.disabled;
}})()
"""
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def wait_for_text(target_id, text, timeout_seconds=15, interval_seconds=1):
    text_json = json.dumps(text, ensure_ascii=False)
    expression = f"(() => (document.body.innerText || '').includes({text_json}))()"
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def wait_for_any_text(target_id, texts, timeout_seconds=20, interval_seconds=1):
    texts_json = json.dumps(texts, ensure_ascii=False)
    expression = f"""
(() => {{
  const body = document.body.innerText || '';
  return {texts_json}.some(text => body.includes(text));
}})()
"""
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def attempt_ai_declaration(target_id):
    target_json = json.dumps(YIDIAN_AI_DECLARATION, ensure_ascii=False)
    expression = (
        "(() => {"
        "  const targetText = " + target_json + ";"
        "  const normalize = (text) => (text || '').replace(/\\s+/g, '');"
        "  const selectors = '.content-claim label, .content-claim .item, label, .item, [role=radio], [role=checkbox], span, div';"
        "  const nodes = Array.from(document.querySelectorAll(selectors));"
        "  const target = nodes.find(node => normalize(node.innerText || node.textContent || node.getAttribute('aria-label') || '') === normalize(targetText));"
        "  if (!target) return JSON.stringify({found: false});"
        "  const readChecked = () => !!("
        "    target.classList.contains('checked') ||"
        "    target.getAttribute('aria-checked') === 'true' ||"
        "    target.querySelector('input:checked') ||"
        "    target.querySelector('.checked')"
        "  );"
        "  if (readChecked()) return JSON.stringify({found: true, checked: true, already: true});"
        "  target.click();"
        "  return JSON.stringify({found: true, checked: readChecked(), already: false, text: (target.innerText || target.textContent || '').trim()});"
        "})()"
    )
    raw = run_cdp("eval", target_id, expression)
    result = json.loads(raw)

    if not result.get("found"):
        raise RuntimeError(f"一点号未找到内容声明选项「{YIDIAN_AI_DECLARATION}」")

    if result.get("checked"):
        print(f"[INFO] 一点号 AI 创作声明已勾选: {result}")
        return result

    raise RuntimeError(f"一点号内容声明「{YIDIAN_AI_DECLARATION}」勾选失败: {result}")


def detect_publish_limit(target_id):
    output = run_cdp("eval", target_id, "(() => document.body.innerText || '')()")
    markers = [
        "达到发布上限",
        "发布上限",
        "发布次数",
        "请明天再来",
        "审核通过前你将无法继续编辑",
        "时间限制",
    ]
    for marker in markers:
        if marker in output:
            return marker
    return None


def main():
    parser = argparse.ArgumentParser(description="Publish Markdown article to Yidian using live Chrome.")
    parser.add_argument("markdown_file", help="Markdown article path")
    parser.add_argument(
        "--mode",
        choices=["draft", "publish"],
        default="draft",
        help="draft 保存草稿，publish 直接发布",
    )
    parser.add_argument(
        "--theme",
        default=None,
        help="可选主题标识（编排层预留，当前发布流程可不使用）。",
    )
    parser.add_argument(
        "--cover",
        default=None,
        metavar="PATH",
        help="可选封面图路径（编排层预留，当前发布流程可不使用）。",
    )
    parser.add_argument(
        "--template-mode",
        dest="template_mode",
        default=None,
        help="可选模板模式（编排层预留，当前发布流程可不使用）。",
    )
    parser.add_argument(
        "--article-id",
        dest="article_id",
        default=None,
        help="可选文章标识（编排层预留，当前发布流程可不使用）。",
    )
    args = parser.parse_args()
    _ = (args.theme, args.template_mode, args.article_id)

    title, _body, html, article_path = load_article(args.markdown_file)
    target_id = find_yidian_target()
    if not target_id:
        raise RuntimeError("没有找到一点号标签页，请先在当前 Chrome 中打开并登录一点号发文页")

    target_id = ensure_editor_ready(target_id)
    result = inject_article(target_id, title, html)
    print(f"[INFO] 已写入一点号编辑器: {result}")

    attempt_ai_declaration(target_id)

    if args.cover:
        apply_cover(target_id, args.cover)

    if args.mode == "draft":
        action = click_action(target_id, "存草稿")
        if action != "clicked":
            raise RuntimeError(f"点击存草稿失败: {action}")
        print(f"[OK] 已存草稿: {article_path}")
        return

    if not args.cover:
        cover_result = select_default_cover(target_id)
        print(f"[INFO] 已尝试切换默认封面: {cover_result}")
        if not wait_for_default_cover(target_id):
            raise RuntimeError("默认封面未选中，无法继续发布")

    publish_ready = wait_for_button(target_id, "发布", timeout_seconds=10)
    if not publish_ready:
        raise RuntimeError("发布按钮仍不可点击，请检查页面是否还有未填项")

    action = click_action(target_id, "发布")
    if action != "clicked":
        raise RuntimeError(f"点击发布失败: {action}")

    if wait_for_button(target_id, "确定", timeout_seconds=8):
        confirm_action = click_action(target_id, "确定")
        if confirm_action != "clicked":
            raise RuntimeError(f"点击发布确认失败: {confirm_action}")
        print("[INFO] 已确认发布弹窗")

    limit_marker = detect_publish_limit(target_id)
    if limit_marker and "审核通过前你将无法继续编辑" not in limit_marker:
        raise RuntimeError(f"一点号发布受限: {limit_marker}")

    if not wait_for_any_text(target_id, ["发布成功", "查看文章", "再写一篇"], timeout_seconds=20):
        limit_marker = detect_publish_limit(target_id)
        if limit_marker:
            raise RuntimeError(f"一点号发布受限: {limit_marker}")
        raise RuntimeError("未检测到一点号发布成功提示，请检查页面状态")

    if wait_for_button(target_id, "查看文章", timeout_seconds=5):
        view_action = click_action(target_id, "查看文章")
        if view_action != "clicked":
            raise RuntimeError(f"点击查看文章失败: {view_action}")

    print(f"[OK] 已发布成功: {article_path}")


if __name__ == "__main__":
    main()
