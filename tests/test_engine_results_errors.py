import tempfile
import unittest
from pathlib import Path

from tiandi_engine.config import EngineConfig, load_engine_config
from tiandi_engine.models.task import build_task_spec
from tiandi_engine.results.errors import ErrorType, is_blocking_error, is_retryable_error
from tiandi_engine.results.record import ExecutionResult


class EngineTaskModelTests(unittest.TestCase):
    def test_build_task_spec_creates_article_and_platform_requests(self):
        spec = build_task_spec(
            source_path=Path("/tmp/articles"),
            article_paths=[Path("/tmp/articles/a.md"), Path("/tmp/articles/b.md")],
            platforms=["wechat", "zhihu"],
            mode="draft",
            default_theme="chinese",
            task_id="task-001",
        )

        self.assertEqual(spec.task_id, "task-001")
        self.assertEqual(spec.mode, "draft")
        self.assertEqual(len(spec.articles), 2)
        self.assertEqual(spec.articles[0].title, "a")
        self.assertEqual(spec.articles[0].platforms[0].platform, "wechat")
        self.assertEqual(spec.articles[0].platforms[0].theme_name, "chinese")

    def test_build_task_spec_optional_article_level_fields(self):
        spec = build_task_spec(
            source_path=Path("/tmp/articles"),
            article_paths=[Path("/tmp/articles/a.md")],
            platforms=["zhihu", "wechat"],
            mode="draft",
            default_theme="chinese",
            default_cover_path="/covers/1.png",
            default_template_mode="rich",
            default_article_id="art-7",
        )
        zh = spec.articles[0].platforms[0]
        wc = spec.articles[0].platforms[1]
        self.assertEqual(zh.platform, "zhihu")
        self.assertEqual(zh.cover_path, "/covers/1.png")
        self.assertEqual(zh.template_mode, "rich")
        self.assertEqual(zh.article_id, "art-7")
        self.assertEqual(wc.theme_name, "chinese")
        self.assertEqual(wc.cover_path, "/covers/1.png")


class EngineConfigTests(unittest.TestCase):
    def test_load_engine_config_prefers_cli_over_env_and_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "config.json").write_text(
                """
{
  "wechat": {
    "app_id": "config-app",
    "app_secret": "config-secret",
    "author": "config-author"
  }
}
""".strip(),
                encoding="utf-8",
            )
            (base_dir / "secrets.env").write_text(
                "WECHAT_APPID=env-file-app\nWECHAT_SECRET=env-file-secret\nWECHAT_AUTHOR=env-file-author\n",
                encoding="utf-8",
            )

            config = load_engine_config(
                base_dir,
                cli_overrides={
                    "wechat_app_id": "cli-app",
                    "wechat_secret": "cli-secret",
                    "wechat_author": "cli-author",
                },
                environ={
                    "WECHAT_APPID": "env-app",
                    "WECHAT_SECRET": "env-secret",
                    "WECHAT_AUTHOR": "env-author",
                },
            )

        self.assertIsInstance(config, EngineConfig)
        self.assertEqual(config.resolve_wechat_credentials(), ("cli-app", "cli-secret", "cli-author"))

    def test_load_engine_config_falls_back_to_env_then_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            (base_dir / "config.json").write_text(
                """
{
  "wechat": {
    "app_id": "config-app",
    "app_secret": "config-secret",
    "author": "config-author"
  }
}
""".strip(),
                encoding="utf-8",
            )

            config = load_engine_config(
                base_dir,
                cli_overrides={},
                environ={
                    "WECHAT_APPID": "env-app",
                    "WECHAT_SECRET": "env-secret",
                    "WECHAT_AUTHOR": "env-author",
                },
            )

        self.assertEqual(config.resolve_wechat_credentials(), ("env-app", "env-secret", "env-author"))


class EngineErrorAndResultTests(unittest.TestCase):
    def test_error_type_helpers(self):
        self.assertTrue(is_retryable_error(ErrorType.TRANSIENT_ERROR))
        self.assertFalse(is_retryable_error(ErrorType.LOGIN_REQUIRED))
        self.assertTrue(is_blocking_error(ErrorType.CONFIG_ERROR))
        self.assertFalse(is_blocking_error(ErrorType.DUPLICATE_OR_SKIPPED))

    def test_execution_result_to_dict_serializes_error_type(self):
        result = ExecutionResult(
            platform="wechat",
            stage="publish",
            status="failed",
            error_type=ErrorType.CONFIG_ERROR,
            summary="missing credentials",
            stdout="",
            stderr="missing appid",
            current_url="",
            retryable=False,
        )

        payload = result.to_dict()
        self.assertEqual(payload["platform"], "wechat")
        self.assertEqual(payload["error_type"], "config_error")
        self.assertEqual(payload["summary"], "missing credentials")
        self.assertFalse(payload["retryable"])


if __name__ == "__main__":
    unittest.main()
