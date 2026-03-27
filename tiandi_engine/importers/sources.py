import uuid
from pathlib import Path
from typing import Iterable, Optional, Tuple

from . import normalize
from tiandi_engine.models.workbench import ArticleDraft

_SUPPORTED_SUFFIXES = {".md", ".txt", ".docx"}


class DocxImportNotAvailableError(RuntimeError):
    """Raised when importing .docx without an optional parser dependency."""

    def __init__(self) -> None:
        super().__init__(
            "DOCX import is not available in this build; add a DOCX library "
            "(e.g. python-docx) to requirements.txt to enable .docx files."
        )


class UnsupportedSourceError(ValueError):
    pass


def _word_count(text: str) -> int:
    return sum(1 for c in text if not c.isspace())


def _new_article_id() -> str:
    return uuid.uuid4().hex


def _markdown_title(content: str, fallback_stem: str) -> str:
    title, _body = normalize.split_markdown_title_body(content, fallback_stem)
    return title


def _draft_from_txt_content(
    raw: str,
    *,
    article_id: str,
    source_path: Optional[Path],
    source_kind: str,
) -> ArticleDraft:
    norm = normalize.normalize_paste_text(raw)
    if source_kind == "paste":
        title, body_md = normalize.split_paste_title_body(norm, fallback_title="Untitled")
    else:
        title, body_raw = normalize.split_txt_title_body(norm)
        body_md = normalize.body_txt_to_markdown_paragraphs(body_raw)
        if not title:
            title = "Untitled"
    return ArticleDraft(
        article_id=article_id,
        title=title,
        body_markdown=body_md,
        source_path=source_path,
        source_kind=source_kind,
        image_paths=(),
        word_count=_word_count(body_md),
        template_mode="default",
        theme_name=None,
        is_config_complete=False,
    )


def import_file(path: Path) -> ArticleDraft:
    path = Path(path).resolve()
    suffix = path.suffix.lower()
    if suffix == ".docx":
        raise DocxImportNotAvailableError()
    if suffix not in (".md", ".txt"):
        raise UnsupportedSourceError(f"unsupported file type: {suffix!r} ({path})")

    raw = path.read_text(encoding="utf-8")
    article_id = _new_article_id()

    if suffix == ".md":
        title, body_for_count = normalize.split_markdown_title_body(raw, path.stem)
        return ArticleDraft(
            article_id=article_id,
            title=title,
            body_markdown=raw,
            source_path=path,
            source_kind="markdown",
            image_paths=(),
            word_count=_word_count(body_for_count),
            template_mode="default",
            theme_name=None,
            is_config_complete=False,
        )

    return _draft_from_txt_content(
        raw,
        article_id=article_id,
        source_path=path,
        source_kind="txt",
    )


def import_pasted_text(text: str, *, article_id: Optional[str] = None) -> ArticleDraft:
    aid = article_id or _new_article_id()
    return _draft_from_txt_content(
        text,
        article_id=aid,
        source_path=None,
        source_kind="paste",
    )


def list_import_candidates(directory: Path) -> Tuple[Path, ...]:
    root = Path(directory).resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    found: list[Path] = []
    for p in root.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() in _SUPPORTED_SUFFIXES:
            found.append(p)
    found.sort(key=lambda x: x.name.lower())
    return tuple(found)
