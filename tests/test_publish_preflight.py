import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish


class PublishPreflightTests(unittest.TestCase):
    def test_run_preflight_checks_blocks_when_wechat_credentials_missing(self):
        with patch.object(
            publish,
            "get_wechat_config_status",
            return_value={
                "appid_ready": False,
                "secret_ready": False,
                "covers_ready": True,
                "ai_cover_ready": False,
            },
        ):
            blockers, warnings = publish.run_preflight_checks(
                platforms=["wechat"],
                mode="draft",
                workbench={},
            )

        self.assertEqual(warnings, [])
        self.assertTrue(any("WECHAT_APPID" in item for item in blockers))

    def test_run_preflight_checks_warns_when_ai_cover_ready_but_local_cover_missing(self):
        with patch.object(
            publish,
            "get_wechat_config_status",
            return_value={
                "appid_ready": True,
                "secret_ready": True,
                "covers_ready": False,
                "ai_cover_ready": True,
            },
        ):
            blockers, warnings = publish.run_preflight_checks(
                platforms=["wechat"],
                mode="draft",
                workbench={},
            )

        self.assertEqual(blockers, [])
        self.assertTrue(any("AI 封面" in item for item in warnings))

    def test_run_preflight_checks_requires_browser_tabs_for_browser_platforms(self):
        with patch.object(
            publish,
            "get_wechat_config_status",
            return_value={
                "appid_ready": True,
                "secret_ready": True,
                "covers_ready": True,
                "ai_cover_ready": False,
            },
        ):
            blockers, _warnings = publish.run_preflight_checks(
                platforms=["zhihu", "toutiao"],
                mode="draft",
                workbench={"zhihu": "target-1"},
            )

        self.assertIn("未找到 `toutiao` 的可用标签页，请先在当前远程调试 Chrome 中打开并登录", blockers)

    def test_run_preflight_checks_blocks_jianshu_daily_limit(self):
        with patch.object(
            publish,
            "get_page_text_snippet",
            return_value="每天只能发布 2 篇公开文章，今天已达上限",
        ), patch.object(
            publish,
            "get_wechat_config_status",
            return_value={
                "appid_ready": True,
                "secret_ready": True,
                "covers_ready": True,
                "ai_cover_ready": False,
            },
        ):
            blockers, warnings = publish.run_preflight_checks(
                platforms=["jianshu"],
                mode="publish",
                workbench={"jianshu": "note-1"},
            )

        self.assertEqual(warnings, [])
        self.assertIn("简书今天已达到公开文章发布上限（每天最多 2 篇）", blockers)

    def test_preflight_blocks_publish_when_non_wechat_cover_pool_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            missing_dir = base / "no_covers_here"
            with patch.object(
                publish,
                "get_wechat_config_status",
                return_value={
                    "appid_ready": True,
                    "secret_ready": True,
                    "covers_ready": True,
                    "ai_cover_ready": False,
                },
            ):
                blockers, warnings = publish.run_preflight_checks(
                    platforms=["zhihu"],
                    mode="publish",
                    workbench={"zhihu": "t-1"},
                    base_dir=base,
                    cover_dir_override=missing_dir,
                )
        self.assertEqual(warnings, [])
        self.assertTrue(
            any("封面" in b and "zhihu" in b for b in blockers),
            msg=f"expected cover pool blocker, got {blockers!r}",
        )

    def test_preflight_warns_draft_when_non_wechat_cover_pool_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            empty_covers = base / "covers"
            empty_covers.mkdir()
            with patch.object(
                publish,
                "get_wechat_config_status",
                return_value={
                    "appid_ready": True,
                    "secret_ready": True,
                    "covers_ready": True,
                    "ai_cover_ready": False,
                },
            ):
                blockers, warnings = publish.run_preflight_checks(
                    platforms=["toutiao", "yidian"],
                    mode="draft",
                    workbench={"toutiao": "t-1", "yidian": "y-1"},
                    base_dir=base,
                    cover_dir_override=empty_covers,
                )
        self.assertEqual(blockers, [])
        self.assertTrue(
            any("封面" in w for w in warnings),
            msg=f"expected cover pool warning, got {warnings!r}",
        )

    def test_append_publish_record_includes_gui_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = Path(tmp) / "publish_records.csv"
            with patch.object(publish, "PUBLISH_RECORDS_FILE", rec):
                publish.append_publish_record(
                    {
                        "article": "/a/b/post.md",
                        "platform": "zhihu",
                        "mode": "draft",
                        "status": "draft_only",
                        "returncode": 0,
                        "stdout": "",
                        "stderr": "",
                        "article_id": "0000-post",
                        "theme_name": "midnight",
                        "template_mode": "rich",
                        "cover_path": str(Path(tmp) / "c.png"),
                        "error_type": None,
                    }
                )
            lines = rec.read_text(encoding="utf-8").splitlines()
            header = lines[0]
            self.assertIn("article_id", header)
            self.assertIn("theme_name", header)
            self.assertIn("cover_path", header)
            self.assertIn("error_type", header)
            with rec.open(encoding="utf-8", newline="") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["article_id"], "0000-post")
            self.assertEqual(rows[0]["theme_name"], "midnight")
            self.assertEqual(rows[0]["template_mode"], "rich")
            self.assertTrue(rows[0]["cover_path"].endswith("c.png"))
            self.assertEqual(rows[0]["error_type"], "")

    def test_print_result_emits_meta_json_line(self):
        out = []

        def fake_print(*args, **_kwargs):
            out.append(args[0] if args else "")

        with patch("builtins.print", fake_print):
            publish.print_result(
                {
                    "platform": "toutiao",
                    "stdout": "",
                    "stderr": "",
                    "returncode": 0,
                    "article_id": "x",
                    "theme_name": "t1",
                    "template_mode": "plain",
                    "cover_path": "/tmp/z.png",
                    "status": "draft_only",
                    "error_type": None,
                }
            )
        meta_lines = [line for line in out if isinstance(line, str) and line.startswith("[META] ")]
        self.assertEqual(len(meta_lines), 1, msg=out)
        payload = json.loads(meta_lines[0].split("[META] ", 1)[1])
        self.assertEqual(payload["platform"], "toutiao")
        self.assertEqual(payload["article_id"], "x")
        self.assertEqual(payload["theme_name"], "t1")
        self.assertEqual(payload["template_mode"], "plain")
        self.assertTrue(payload["cover_path"].endswith(".png"))
        self.assertEqual(payload["status"], "draft_only")
        self.assertIsNone(payload["error_type"])


class ChromeLaunchTests(unittest.TestCase):
    def test_iter_chrome_launch_commands_windows_uses_start_command(self):
        commands = publish.iter_chrome_launch_commands(["https://example.com"], platform="win32")

        self.assertGreaterEqual(len(commands), 1)
        self.assertEqual(
            commands[0],
            ["cmd", "/c", "start", "", "chrome", "https://example.com"],
        )

    def test_iter_chrome_launch_commands_macos_keeps_open_a_behavior(self):
        commands = publish.iter_chrome_launch_commands(["https://example.com"], platform="darwin")

        self.assertEqual(commands[0], ["open", "-a", "Google Chrome", "https://example.com"])


if __name__ == "__main__":
    unittest.main()
