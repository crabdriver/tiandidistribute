import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import jianshu_publisher
import yidian_publisher
import zhihu_publisher


class ZhihuApplyCoverTests(unittest.TestCase):
    def test_apply_cover_calls_setfile_with_known_selector(self):
        mock_run = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(b"x")
            tmp_path = handle.name
        try:
            zhihu_publisher.apply_cover("abc12345", Path(tmp_path), run_cdp_fn=mock_run)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        mock_run.assert_called_once_with(
            "setfile",
            "abc12345",
            zhihu_publisher.ZHIHU_COVER_FILE_INPUT,
            str(Path(tmp_path).resolve()),
        )

    def test_apply_cover_missing_file_raises(self):
        mock_run = MagicMock()
        with self.assertRaises(RuntimeError) as ctx:
            zhihu_publisher.apply_cover("tid", Path("/no/such/cover.png"), run_cdp_fn=mock_run)
        self.assertIn("不存在", str(ctx.exception))
        mock_run.assert_not_called()


class JianshuCoverArgTests(unittest.TestCase):
    def test_cover_flag_fails_fast_with_diagnostic(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8") as handle:
            handle.write("# T\n\nbody")
            md_path = handle.name
        old_argv = sys.argv
        try:
            sys.argv = ["jianshu_publisher.py", md_path, "--mode", "draft", "--cover", "/tmp/cover.png"]
            with self.assertRaises(RuntimeError) as ctx:
                jianshu_publisher.main()
        finally:
            sys.argv = old_argv
            Path(md_path).unlink(missing_ok=True)
        self.assertIn("简书", str(ctx.exception))
        self.assertIn("--cover", str(ctx.exception))


class YidianCoverArgTests(unittest.TestCase):
    def test_draft_mode_with_cover_still_applies_cover(self):
        argv = [
            "yidian_publisher.py",
            "/tmp/article.md",
            "--mode",
            "draft",
            "--cover",
            "/tmp/cover.png",
        ]
        with patch.object(sys, "argv", argv), patch.object(
            yidian_publisher,
            "load_article",
            return_value=("Title", "Body", "<p>Body</p>", Path("/tmp/article.md")),
        ), patch.object(
            yidian_publisher,
            "find_yidian_target",
            return_value="target-1",
        ), patch.object(
            yidian_publisher,
            "ensure_editor_ready",
            return_value="target-1",
        ), patch.object(
            yidian_publisher,
            "inject_article",
            return_value="ok",
        ), patch.object(
            yidian_publisher,
            "attempt_ai_declaration",
            return_value=None,
        ), patch.object(
            yidian_publisher,
            "apply_cover",
        ) as apply_cover_mock, patch.object(
            yidian_publisher,
            "click_action",
            return_value="clicked",
        ):
            yidian_publisher.main()

        apply_cover_mock.assert_called_once_with("target-1", "/tmp/cover.png")


if __name__ == "__main__":
    unittest.main()
