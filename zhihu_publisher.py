import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from markdown_utils import render_markdown_plain_text


BASE_DIR = Path(__file__).resolve().parent
CDP_SCRIPT = BASE_DIR / "live_cdp.mjs"
ZHIHU_MATCHES = ("zhuanlan.zhihu.com", "www.zhihu.com/write", "www.zhihu.com/creator")
ZHIHU_EDITOR_URL = "https://zhuanlan.zhihu.com/write"


def clean_title(title):
    return re.sub(r"^\d{1,2}-\d{1,2}_", "", title).strip()


def run_cdp(command, *args, timeout=120):
    try:
        result = subprocess.run(
            ["node", str(CDP_SCRIPT), command, *args],
            cwd=str(BASE_DIR),
            text=True,
            capture_output=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"CDP call timed out after {timeout}s: {command} {args}") from exc


def find_zhihu_target():
    bound_target = os.environ.get("PUBLISH_TARGET_ZHIHU")
    if bound_target:
        return bound_target
    output = run_cdp("list")
    fallback_target = None
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        target_id, _title, url = parts[0], parts[1], parts[2]
        if "zhihu.com" in url and fallback_target is None:
            fallback_target = target_id
        if any(match in url for match in ZHIHU_MATCHES):
            return target_id
    return fallback_target


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

    title = title[:100]
    plain_body = render_markdown_plain_text(body)
    return title, plain_body, path


def wait_until(target_id, expression, timeout_seconds=20, interval_seconds=1):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run_cdp("eval", target_id, expression)
        if result == "true":
            return True
        time.sleep(interval_seconds)
    return False


def ensure_editor_ready(target_id):
    already_ready = wait_until(
        target_id,
        """
(() => {
  const titleEl = document.querySelector('textarea[placeholder*="标题"], input[placeholder*="标题"]');
  const editor = document.querySelector('.public-DraftEditor-content, .ProseMirror, [data-lexical-editor="true"], [contenteditable="true"]');
  return !!titleEl && !!editor;
})()
""".strip(),
        timeout_seconds=3,
        interval_seconds=0.5,
    )
    if already_ready:
        return

    run_cdp("nav", target_id, ZHIHU_EDITOR_URL)
    ready = wait_until(
        target_id,
        """
(() => {
  const titleEl = document.querySelector('textarea[placeholder*="标题"], input[placeholder*="标题"]');
  const editor = Array.from(document.querySelectorAll('.public-DraftEditor-content,.ProseMirror,[data-lexical-editor="true"],[contenteditable="true"]')).find(el => {
    const rect = el.getBoundingClientRect();
    return rect.width >= 300 && rect.height >= 10;
  });
  return !!titleEl && !!editor;
})()
""".strip(),
        timeout_seconds=30,
    )
    if not ready:
        raise RuntimeError("知乎写作页未就绪，请确认当前 Chrome 已登录知乎并能进入写文章页面")


def inject_article(target_id, title, plain_body):
    title_json = json.dumps(title, ensure_ascii=False)
    expression = f"""
(() => {{
  const isVisible = (el) => {{
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }};

  const titleEl = document.querySelector('textarea[placeholder*="标题"], input[placeholder*="标题"]');
  const editor = Array.from(document.querySelectorAll(
    '.public-DraftEditor-content,.ProseMirror,[data-lexical-editor="true"],[contenteditable="true"]'
  )).find(el => {{
    if (!isVisible(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width >= 300 && rect.height >= 10;
  }});

  if (!titleEl || !editor) {{
    return JSON.stringify({{
      ok: false,
      reason: 'missing-editor',
      hasTitle: !!titleEl
    }});
  }}

  if ('value' in titleEl) {{
    const proto = titleEl.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
    if (setter) {{
      setter.call(titleEl, {title_json});
    }} else {{
      titleEl.value = {title_json};
    }}
  }} else {{
    titleEl.textContent = {title_json};
  }}
  titleEl.dispatchEvent(new Event('input', {{ bubbles: true }}));
  titleEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
  editor.focus();
  editor.click();
  try {{
    document.execCommand('selectAll');
    document.execCommand('delete');
  }} catch (_err) {{}}
  const rect = editor.getBoundingClientRect();

  return JSON.stringify({{
    ok: true,
    title: ('value' in titleEl ? titleEl.value : titleEl.innerText || titleEl.textContent || '').trim(),
    editorTag: editor.tagName,
    point: {{
      x: rect.left + Math.min(rect.width / 2, 80),
      y: rect.top + Math.max(rect.height / 2, 12)
    }}
  }});
}})()
"""
    output = run_cdp("eval", target_id, expression)
    parsed = json.loads(output)
    if not parsed.get("ok"):
        raise RuntimeError(f"写入知乎编辑器失败: {parsed}")
    point = parsed["point"]
    run_cdp("clickxy", target_id, str(point["x"]), str(point["y"]))
    time.sleep(0.3)
    run_cdp("type", target_id, plain_body)
    time.sleep(0.5)

    verify_output = run_cdp(
        "eval",
        target_id,
        """
(() => {
  const titleEl = document.querySelector('textarea[placeholder*="标题"], input[placeholder*="标题"]');
  const editor = document.querySelector('.public-DraftEditor-content, .ProseMirror, [data-lexical-editor="true"], [contenteditable="true"]');
  const bodyText = (editor?.innerText || editor?.textContent || editor?.value || '').trim();
  const wordCount = Number((document.body.innerText || '').match(/字数：(\d+)/)?.[1] || 0);
  return JSON.stringify({
    title: (titleEl?.value || titleEl?.innerText || '').trim(),
    bodyLength: bodyText.length || wordCount
  });
})()
""".strip(),
    )
    verify = json.loads(verify_output)
    return json.dumps({**parsed, **verify}, ensure_ascii=False)


def get_click_center(target_id, text, selector):
    text_json = json.dumps(text, ensure_ascii=False)
    selector_json = json.dumps(selector, ensure_ascii=False)
    expression = f"""
(() => {{
  const isVisible = (el) => {{
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  }};

  const nodes = Array.from(document.querySelectorAll({selector_json})).filter(isVisible);
  const target = nodes.find(node => (node.innerText || '').replace(/\\s+/g, '') === {text_json}.replace(/\\s+/g, ''));
  if (!target) return '';
  const rect = target.getBoundingClientRect();
  return JSON.stringify({{
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2
  }});
}})()
"""
    output = run_cdp("eval", target_id, expression)
    if not output:
        return None
    return json.loads(output)


def click_text_by_xy(target_id, text, selector):
    point = get_click_center(target_id, text, selector=selector)
    if not point:
        return "target-not-found"
    run_cdp("clickxy", target_id, str(point["x"]), str(point["y"]))
    return "clicked"


def wait_for_any_text(target_id, texts, timeout_seconds=20, interval_seconds=1):
    texts_json = json.dumps(texts, ensure_ascii=False)
    expression = f"""
(() => {{
  const content = document.body.innerText || '';
  return {texts_json}.some(text => content.includes(text));
}})()
"""
    return wait_until(target_id, expression, timeout_seconds=timeout_seconds, interval_seconds=interval_seconds)


def detect_publish_limit(target_id):
    output = run_cdp(
        "eval",
        target_id,
        """
(() => document.body.innerText || '')()
""".strip(),
    )
    markers = [
        "达到发布上限",
        "发布次数已达上限",
        "今日发布次数",
        "请明天再来",
        "频繁发布",
        "稍后再试",
    ]
    for marker in markers:
        if marker in output:
            return marker
    return None


def main():
    parser = argparse.ArgumentParser(description="Publish Markdown article to Zhihu using live Chrome.")
    parser.add_argument("markdown_file", help="Markdown article path")
    parser.add_argument(
        "--mode",
        choices=["draft", "publish"],
        default="draft",
        help="draft 只写入并等待自动保存；publish 尝试直接发布",
    )
    args = parser.parse_args()

    title, plain_body, article_path = load_article(args.markdown_file)
    target_id = find_zhihu_target()
    if not target_id:
        raise RuntimeError("没有找到知乎标签页，请先在当前 Chrome 中打开并登录任意知乎页面")

    ensure_editor_ready(target_id)
    inject_result = inject_article(target_id, title, plain_body)
    print(f"[INFO] 已写入知乎编辑器: {inject_result}")

    if args.mode == "draft":
        draft_saved = wait_for_any_text(
            target_id,
            ["草稿", "已保存", "保存成功", "正在保存", "已自动保存"],
            timeout_seconds=15,
        )
        if not draft_saved:
            print("[WARN] 未明确检测到知乎保存文案，可能仍在自动保存")
        print(f"[OK] 已写入知乎草稿页: {article_path}")
        return

    publish_result = click_text_by_xy(target_id, "发布", selector="button,a,div,span")
    if publish_result != "clicked":
        publish_result = click_text_by_xy(target_id, "发布文章", selector="button,a,div,span")
    if publish_result != "clicked":
        raise RuntimeError(f"点击知乎发布失败: {publish_result}")

    if wait_until(
        target_id,
        "(() => Array.from(document.querySelectorAll('button,a,div,span')).some(el => ['确认发布','立即发布','发布'].includes((el.innerText || '').replace(/\\s+/g, ''))))()",
        timeout_seconds=8,
    ):
        confirm_result = click_text_by_xy(target_id, "确认发布", selector="button,a,div,span")
        if confirm_result != "clicked":
            confirm_result = click_text_by_xy(target_id, "立即发布", selector="button,a,div,span")
        if confirm_result != "clicked":
            confirm_result = click_text_by_xy(target_id, "发布", selector="button,a,div,span")
        if confirm_result != "clicked":
            raise RuntimeError(f"点击知乎确认发布失败: {confirm_result}")

    limit_marker = detect_publish_limit(target_id)
    if limit_marker:
        raise RuntimeError(f"知乎发布受限: {limit_marker}")

    published = wait_until(
        target_id,
        """
(() => {
  const text = document.body.innerText || '';
  return (
    text.includes('发布成功') ||
    text.includes('文章已发布') ||
    text.includes('查看文章') ||
    (!location.href.includes('/write') && !location.href.includes('/creator'))
  );
})()
""".strip(),
        timeout_seconds=30,
    )
    if not published:
        limit_marker = detect_publish_limit(target_id)
        if limit_marker:
            raise RuntimeError(f"知乎发布受限: {limit_marker}")
        raise RuntimeError("未检测到知乎发布成功提示，请检查页面状态")

    print(f"[OK] 已发布到知乎: {article_path}")


if __name__ == "__main__":
    main()
