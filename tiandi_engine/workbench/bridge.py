from __future__ import annotations

import csv
import json
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from tiandi_engine.assignment.covers import COVER_PLATFORMS, assign_covers
from tiandi_engine.assignment.templates import assign_templates, scan_theme_pool
from tiandi_engine.config import load_engine_config
from tiandi_engine.importers.sources import import_file, import_pasted_text, list_import_candidates
from tiandi_engine.models.workbench import ArticleDraft, ImportJob, PublishJob
from tiandi_engine.runner.pipeline import run_platform_task

WORKBENCH_ROOT = Path(".tiandidistribute") / "workbench"
SESSION_PATH = Path(".tiandidistribute") / "publish-console" / "publish-console-session.json"
RECORDS_PATH = Path("publish_records.csv")
SUCCESS_STATUSES = {"published", "draft_only", "success_unknown"}
SKIP_STATUSES = {"skipped_existing"}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _new_job_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _ensure_base_dir(base_dir) -> Path:
    return Path(base_dir).expanduser().resolve()


def _coerce_path(value) -> Optional[Path]:
    if value in (None, ""):
        return None
    return Path(value).expanduser().resolve()


def _coerce_draft(raw) -> ArticleDraft:
    if isinstance(raw, ArticleDraft):
        return raw
    if not isinstance(raw, Mapping):
        raise TypeError(f"unsupported draft payload: {type(raw)!r}")
    image_paths = tuple(_coerce_path(item) for item in raw.get("image_paths", []) if item)
    return ArticleDraft(
        article_id=str(raw["article_id"]),
        title=str(raw.get("title") or "Untitled"),
        body_markdown=str(raw.get("body_markdown") or ""),
        source_path=_coerce_path(raw.get("source_path")),
        source_kind=str(raw.get("source_kind") or "markdown"),
        image_paths=tuple(path for path in image_paths if path is not None),
        word_count=int(raw.get("word_count") or 0),
        template_mode=str(raw.get("template_mode") or "default"),
        theme_name=raw.get("theme_name"),
        is_config_complete=bool(raw.get("is_config_complete", False)),
    )


def _materialize_markdown(draft: ArticleDraft) -> str:
    body = draft.body_markdown.strip()
    if draft.source_kind == "markdown" and body.startswith("#"):
        return draft.body_markdown
    if body:
        return f"# {draft.title}\n\n{body}\n"
    return f"# {draft.title}\n"


def _write_staged_articles(base_dir: Path, drafts: Sequence[ArticleDraft], job_id: str):
    root = base_dir / WORKBENCH_ROOT / "articles" / job_id
    root.mkdir(parents=True, exist_ok=True)
    staged = []
    for draft in drafts:
        path = root / f"{draft.article_id}.md"
        path.write_text(_materialize_markdown(draft), encoding="utf-8")
        staged.append({"article_id": draft.article_id, "markdown_path": str(path)})
    return staged


def _theme_pool_payload(base_dir: Path):
    config = load_engine_config(base_dir)
    entries = scan_theme_pool(config.resolve_themes_dir())
    return {
        **config.discover_theme_pool(),
        "entries": [
            {
                "theme_id": entry.theme_id,
                "display_name": entry.display_name,
            }
            for entry in entries
        ],
    }


def _wechat_settings_payload(base_dir: Path):
    config = load_engine_config(base_dir)
    return {
        "settings": config.get_wechat_settings(),
        "status": config.get_wechat_config_status(),
    }


def _write_simple_env_updates(env_path: Path, updates: Mapping[str, str]):
    normalized = {str(key): str(value) for key, value in updates.items()}
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen = set()
    out = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            out.append(raw_line)
            continue
        key, _old_value = raw_line.split("=", 1)
        key = key.strip()
        if key in normalized:
            out.append(f"{key}={normalized[key]}")
            seen.add(key)
        else:
            out.append(raw_line)
    for key, value in normalized.items():
        if key not in seen:
            out.append(f"{key}={value}")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def read_wechat_settings(base_dir):
    root = _ensure_base_dir(base_dir)
    payload = _wechat_settings_payload(root)
    return {
        **payload["settings"],
        "status": payload["status"],
    }


def save_wechat_settings(base_dir, *, app_id="", secret="", author=""):
    root = _ensure_base_dir(base_dir)
    env_path = root / "secrets.env"
    _write_simple_env_updates(
        env_path,
        {
            "WECHAT_APPID": app_id,
            "WECHAT_SECRET": secret,
            "WECHAT_AUTHOR": author,
        },
    )
    return read_wechat_settings(root)


def _apply_manual_cover_overrides(cover_assignments, manual_cover_by_article_platform):
    manual = dict(manual_cover_by_article_platform or {})
    if not manual:
        return tuple(cover_assignments)

    by_key = {(item.article_id, item.platform): item for item in cover_assignments}
    for raw_key, raw_path in manual.items():
        if isinstance(raw_key, str):
            article_id, _, platform = raw_key.partition(":")
        else:
            article_id, platform = raw_key
        cover_path = _coerce_path(raw_path)
        if not article_id or not platform or cover_path is None:
            continue
        if (article_id, platform) in by_key:
            original = by_key[(article_id, platform)]
            by_key[(article_id, platform)] = replace(
                original,
                cover_path=cover_path,
                cover_source="manual",
                is_random=False,
                is_manual_override=True,
            )
        else:
            from tiandi_engine.models.workbench import CoverAssignment

            by_key[(article_id, platform)] = CoverAssignment(
                article_id=article_id,
                platform=platform,
                cover_path=cover_path,
                cover_source="manual",
                is_random=False,
                is_manual_override=True,
            )
    return tuple(by_key[key] for key in sorted(by_key))


def import_sources(
    base_dir,
    *,
    import_mode: str,
    source_path: Optional[str] = None,
    pasted_text: Optional[str] = None,
    job_id: Optional[str] = None,
    imported_at: Optional[str] = None,
):
    root = _ensure_base_dir(base_dir)
    drafts: tuple[ArticleDraft, ...]
    source = _coerce_path(source_path)
    mode = str(import_mode)
    if mode == "paste":
        drafts = (import_pasted_text(pasted_text or ""),)
    elif mode == "file":
        if source is None:
            raise ValueError("file import requires source_path")
        drafts = (import_file(source),)
    elif mode == "folder":
        if source is None:
            raise ValueError("folder import requires source_path")
        drafts = tuple(import_file(path) for path in list_import_candidates(source))
    else:
        raise ValueError(f"unsupported import_mode: {mode}")

    job = ImportJob(
        job_id=job_id or _new_job_id("import"),
        import_mode=mode,
        source_path=source,
        pasted_preview=(pasted_text or "")[:120] if mode == "paste" else None,
        imported_at=imported_at or _now_iso(),
        drafts=drafts,
    )
    return {"job": job.to_dict(), "resources": discover_resources(root)}


def discover_resources(base_dir):
    root = _ensure_base_dir(base_dir)
    config = load_engine_config(root)
    return {
        "theme_pool": _theme_pool_payload(root),
        "cover_pool": config.discover_cover_pool(),
        "wechat": _wechat_settings_payload(root),
        "defaults": {
            "template_mode": config.get_default_template_mode(),
            "cover_repeat_window": config.get_cover_repeat_window(),
        },
    }


def plan_publish_job(
    base_dir,
    *,
    drafts,
    platforms: Sequence[str],
    mode: str = "draft",
    continue_on_error: bool = False,
    template_mode: Optional[str] = None,
    manual_theme_by_article: Optional[Mapping[str, str]] = None,
    manual_cover_by_article_platform: Optional[Mapping[str, str]] = None,
    seed: Optional[int] = None,
    recent_cover_paths: Optional[Sequence[str]] = None,
    job_id: Optional[str] = None,
):
    root = _ensure_base_dir(base_dir)
    config = load_engine_config(root)
    draft_objects = tuple(_coerce_draft(item) for item in drafts)
    article_ids = tuple(draft.article_id for draft in draft_objects)
    selected_platforms = tuple(str(platform) for platform in platforms)
    publish_job_id = job_id or _new_job_id("publish")
    assignment_mode = template_mode or config.get_default_template_mode()

    theme_entries = scan_theme_pool(config.resolve_themes_dir())
    template_assignments = ()
    if theme_entries:
        template_assignments = assign_templates(
            article_ids,
            themes_dir=config.resolve_themes_dir(),
            assignment_mode=assignment_mode,
            manual_theme_by_article=manual_theme_by_article,
            seed=seed,
        )

    cover_assignments = ()
    if any(platform in COVER_PLATFORMS for platform in selected_platforms):
        cover_pool = config.discover_cover_pool()
        if cover_pool.get("ok"):
            cover_assignments = assign_covers(
                article_ids,
                selected_platforms,
                cover_dir=config.resolve_cover_dir(),
                recent_cover_paths=tuple(recent_cover_paths or ()),
                repeat_window=config.get_cover_repeat_window(),
                seed=seed,
            )
    cover_assignments = _apply_manual_cover_overrides(cover_assignments, manual_cover_by_article_platform)

    template_by_article = {item.article_id: item for item in template_assignments}
    enriched_drafts = []
    for draft in draft_objects:
        assignment = template_by_article.get(draft.article_id)
        enriched_drafts.append(
            replace(
                draft,
                template_mode=assignment.template_mode if assignment else assignment_mode,
                theme_name=assignment.theme_name if assignment else draft.theme_name,
                is_config_complete=True,
            )
        )

    staged_articles = _write_staged_articles(root, enriched_drafts, publish_job_id)
    staged_by_article = {item["article_id"]: item["markdown_path"] for item in staged_articles}
    cover_by_pair = {(item.article_id, item.platform): item for item in cover_assignments}
    context_map = []
    for draft in enriched_drafts:
        assignment = template_by_article.get(draft.article_id)
        for platform in selected_platforms:
            cover_assignment = cover_by_pair.get((draft.article_id, platform))
            context_map.append(
                {
                    "article_id": draft.article_id,
                    "platform": platform,
                    "markdown_path": staged_by_article[draft.article_id],
                    "theme_name": assignment.theme_id if assignment else None,
                    "template_mode": assignment.template_mode if assignment else assignment_mode,
                    "cover_path": str(cover_assignment.cover_path) if cover_assignment and cover_assignment.cover_path else None,
                }
            )

    publish_job = PublishJob(
        job_id=publish_job_id,
        article_ids=tuple(draft.article_id for draft in enriched_drafts),
        platforms=selected_platforms,
        status="pending",
    )
    return {
        "publish_job": publish_job.to_dict(),
        "mode": mode,
        "continue_on_error": bool(continue_on_error),
        "drafts": [draft.to_dict() for draft in enriched_drafts],
        "template_assignments": [item.to_dict() for item in template_assignments],
        "cover_assignments": [item.to_dict() for item in cover_assignments],
        "staged_articles": staged_articles,
        "context_map": context_map,
        "resources": discover_resources(root),
    }


def _build_context_lookup(plan_payload):
    mapping = {}
    for item in plan_payload.get("context_map", []):
        mapping[(item["article_id"], item["platform"])] = item
    return mapping


def _status_counts(results):
    success = failure = skipped = 0
    recoverable = True
    for result in results:
        status = result.get("status")
        if status in SUCCESS_STATUSES:
            success += 1
        elif status in SKIP_STATUSES:
            skipped += 1
        else:
            failure += 1
            recoverable = recoverable and bool(result.get("retryable", False))
    return success, failure, skipped, recoverable


def run_publish_job(base_dir, plan_payload, *, registry=None, append_record=None, event_sink=None):
    root = _ensure_base_dir(base_dir)
    staged_by_article = {item["article_id"]: item["markdown_path"] for item in plan_payload.get("staged_articles", [])}
    draft_by_article = {item["article_id"]: item for item in plan_payload.get("drafts", [])}
    publish_job = dict(plan_payload["publish_job"])
    mode = plan_payload.get("mode", "draft")
    continue_on_error = bool(plan_payload.get("continue_on_error", False))
    context_entries = list(plan_payload.get("context_map", []))
    events = []

    def emit(event):
        events.append(event)
        if event_sink:
            event_sink(event)

    emit(
        {
            "type": "job_started",
            "job_id": publish_job["job_id"],
            "article_ids": list(publish_job["article_ids"]),
            "platforms": list(publish_job["platforms"]),
            "mode": mode,
        }
    )
    results = []
    current_article_id = None
    for context in context_entries:
        article_id = context["article_id"]
        platform = context["platform"]
        if article_id != current_article_id:
            current_article_id = article_id
            emit(
                {
                    "type": "article_started",
                    "job_id": publish_job["job_id"],
                    "article_id": article_id,
                    "title": draft_by_article.get(article_id, {}).get("title", article_id),
                    "markdown_path": staged_by_article.get(article_id, context["markdown_path"]),
                }
            )
        emit(
            {
                "type": "platform_started",
                "job_id": publish_job["job_id"],
                "article_id": article_id,
                "platform": platform,
            }
        )
        result = run_platform_task(
            base_dir=root,
            platform=platform,
            markdown_file=context["markdown_path"],
            mode=mode,
            theme_name=context.get("theme_name"),
            cover_path=context.get("cover_path"),
            template_mode=context.get("template_mode"),
            article_id=article_id,
            registry=registry,
        )
        result["article"] = context["markdown_path"]
        results.append(result)
        if append_record:
            append_record(result)
        emit(
            {
                "type": "platform_finished",
                "job_id": publish_job["job_id"],
                "article_id": article_id,
                "platform": platform,
                "result": result,
            }
        )
        if result["returncode"] != 0 and not continue_on_error:
            break

    success_count, failure_count, skip_count, recoverable = _status_counts(results)
    last_failed_result = next((item for item in reversed(results) if item.get("returncode") != 0), None)
    publish_job.update(
        {
            "status": "completed" if failure_count == 0 else "failed",
            "current_step": "done",
            "success_count": success_count,
            "failure_count": failure_count,
            "skip_count": skip_count,
            "recoverable": recoverable,
            "error_summary": last_failed_result["summary"] if last_failed_result else "",
        }
    )
    emit(
        {
            "type": "job_finished",
            "job_id": publish_job["job_id"],
            "publish_job": publish_job,
            "result_count": len(results),
        }
    )
    return {
        "publish_job": publish_job,
        "events": events,
        "results": results,
    }


def read_recent_history(base_dir, *, limit: int = 20):
    root = _ensure_base_dir(base_dir)
    records_path = root / RECORDS_PATH
    session_path = root / SESSION_PATH
    records = []
    if records_path.exists():
        with records_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        records = rows[-max(0, int(limit)) :] if limit is not None else rows
    session = None
    if session_path.exists():
        session = json.loads(session_path.read_text(encoding="utf-8"))
    return {
        "records": records,
        "session": session,
    }


def handle_bridge_command(base_dir, payload, *, registry=None, append_record=None):
    if not isinstance(payload, Mapping):
        raise TypeError("bridge payload must be a mapping")
    command = payload.get("command")
    if command == "import_sources":
        return import_sources(
            base_dir,
            import_mode=payload.get("import_mode", "paste"),
            source_path=payload.get("source_path"),
            pasted_text=payload.get("pasted_text"),
            job_id=payload.get("job_id"),
            imported_at=payload.get("imported_at"),
        )
    if command == "discover_resources":
        return discover_resources(base_dir)
    if command == "read_wechat_settings":
        return read_wechat_settings(base_dir)
    if command == "save_wechat_settings":
        return save_wechat_settings(
            base_dir,
            app_id=str(payload.get("app_id", "")),
            secret=str(payload.get("secret", "")),
            author=str(payload.get("author", "")),
        )
    if command == "plan_publish_job":
        return plan_publish_job(
            base_dir,
            drafts=payload.get("drafts", ()),
            platforms=payload.get("platforms", ()),
            mode=payload.get("mode", "draft"),
            continue_on_error=payload.get("continue_on_error", False),
            template_mode=payload.get("template_mode"),
            manual_theme_by_article=payload.get("manual_theme_by_article"),
            manual_cover_by_article_platform=payload.get("manual_cover_by_article_platform"),
            seed=payload.get("seed"),
            recent_cover_paths=payload.get("recent_cover_paths"),
            job_id=payload.get("job_id"),
        )
    if command == "run_publish_job":
        return run_publish_job(
            base_dir,
            payload["plan"],
            registry=registry,
            append_record=append_record,
        )
    if command == "run_publish_job_stream":
        return run_publish_job(
            base_dir,
            payload["plan"],
            registry=registry,
            append_record=append_record,
        )
    if command == "read_recent_history":
        return read_recent_history(base_dir, limit=int(payload.get("limit", 20)))
    raise ValueError(f"unsupported bridge command: {command}")
