import json
import tempfile
import unittest
from pathlib import Path

from scripts.format import build_gallery_bundle, render_publish_console_page


class FormatConsoleBundleTests(unittest.TestCase):
    def test_build_gallery_bundle_renders_requested_themes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            article = tmp_path / "demo.md"
            article.write_text("# 示例标题\n\n这是一段正文。", encoding="utf-8")

            bundle = build_gallery_bundle(
                input_path=article,
                vault_root=tmp_path,
                output_dir=tmp_path / "out",
                theme_ids=["chinese", "newspaper"],
            )

        self.assertEqual(bundle["title"], "示例标题")
        self.assertEqual(bundle["theme_ids"], ["chinese", "newspaper"])
        self.assertIn("chinese", bundle["rendered_map"])
        self.assertIn("newspaper", bundle["rendered_map"])

    def test_render_publish_console_page_embeds_session_and_controls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            article = tmp_path / "demo.md"
            output_dir = tmp_path / "out"
            html_path = tmp_path / "console.html"
            article.write_text("# 控制台标题\n\n测试正文。", encoding="utf-8")

            bundle = build_gallery_bundle(
                input_path=article,
                vault_root=tmp_path,
                output_dir=output_dir,
                theme_ids=["chinese"],
            )
            session = {
                "current_index": 0,
                "current_theme": "chinese",
                "items": [{"status": "reviewing", "platforms": {"wechat": {"status": "pending", "detail": ""}}}],
                "summary": {"total_articles": 1, "completed_articles": 0},
            }

            render_publish_console_page(bundle, session, html_path)
            html = html_path.read_text(encoding="utf-8")

        self.assertIn("控制台标题", html)
        self.assertIn("确认并发布当前文章", html)
        self.assertIn(json.dumps(session, ensure_ascii=False), html)


if __name__ == "__main__":
    unittest.main()
