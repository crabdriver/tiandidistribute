import subprocess
import sys
import unittest
from pathlib import Path

from tiandi_engine.platforms.base import BasePlatformAdapter
from tiandi_engine.platforms.registry import build_platform_registry
from tiandi_engine.results.errors import ErrorType


class PlatformContractTests(unittest.TestCase):
    def test_registry_contains_all_current_platforms(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        self.assertEqual(
            sorted(registry.keys()),
            ["jianshu", "toutiao", "wechat", "yidian", "zhihu"],
        )

    def test_adapters_expose_required_methods(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        for adapter in registry.values():
            self.assertIsInstance(adapter, BasePlatformAdapter)
            self.assertTrue(callable(adapter.prepare))
            self.assertTrue(callable(adapter.publish))
            self.assertTrue(callable(adapter.verify))
            self.assertTrue(callable(adapter.collect_result))

    def test_wechat_prepare_includes_theme(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        prepared = registry["wechat"].prepare(
            markdown_file="/tmp/article.md",
            mode="draft",
            theme_name="chinese",
        )

        self.assertEqual(prepared["platform"], "wechat")
        self.assertIn("wechat_publisher.py", str(prepared["command"][1]))
        self.assertEqual(prepared["command"][-2:], ["--theme", "chinese"])

    def test_zhihu_prepare_includes_theme_cover_and_template_mode_in_command(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        prepared = registry["zhihu"].prepare(
            markdown_file="/tmp/article.md",
            mode="draft",
            theme_name="editorial",
            cover_path="/tmp/cover.png",
            template_mode="rich",
            article_id="rev-1",
        )

        self.assertEqual(prepared["platform"], "zhihu")
        cmd = prepared["command"]
        self.assertIn("zhihu_publisher.py", str(cmd[1]))
        self.assertIn("--theme", cmd)
        self.assertEqual(cmd[cmd.index("--theme") + 1], "editorial")
        self.assertIn("--cover", cmd)
        self.assertEqual(cmd[cmd.index("--cover") + 1], "/tmp/cover.png")
        self.assertIn("--template-mode", cmd)
        self.assertEqual(cmd[cmd.index("--template-mode") + 1], "rich")
        self.assertIn("--article-id", cmd)
        self.assertEqual(cmd[cmd.index("--article-id") + 1], "rev-1")
        self.assertEqual(prepared.get("article_id"), "rev-1")

    def test_browser_publish_scripts_accept_theme_cover_in_help(self):
        repo_root = Path(__file__).resolve().parent.parent
        for script in (
            "zhihu_publisher.py",
            "toutiao_publisher.py",
            "jianshu_publisher.py",
            "yidian_publisher.py",
        ):
            completed = subprocess.run(
                [sys.executable, str(repo_root / script), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            helptext = completed.stdout + completed.stderr
            self.assertIn("--theme", helptext, msg=script)
            self.assertIn("--cover", helptext, msg=script)
            self.assertIn("--article-id", helptext, msg=script)

    def test_collect_result_builds_structured_failure(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        result = registry["zhihu"].collect_result(
            {
                "platform": "zhihu",
                "returncode": 1,
                "stdout": "",
                "stderr": "编辑器未就绪",
            },
            mode="publish",
        )

        self.assertEqual(result.platform, "zhihu")
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.summary, "编辑器未就绪")

    def test_collect_result_marks_timeout_as_retryable_transient_error(self):
        registry = build_platform_registry(Path("/tmp/repo"))
        result = registry["zhihu"].collect_result(
            {
                "platform": "zhihu",
                "returncode": 124,
                "stdout": "partial stdout",
                "stderr": "Process timed out after 180 seconds",
                "timed_out": True,
            },
            mode="publish",
        )

        self.assertEqual(result.platform, "zhihu")
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_type, ErrorType.TRANSIENT_ERROR)
        self.assertTrue(result.retryable)


if __name__ == "__main__":
    unittest.main()
