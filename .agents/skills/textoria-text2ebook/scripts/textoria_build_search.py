#!/usr/bin/env python3
"""Textoria static search-index stage."""

from __future__ import annotations

import json
from pathlib import Path

from textoria_common import BuildPaths, write_stage_report


def build_search_index(paths: BuildPaths, reader_paragraphs: list[dict]) -> dict:
    from textoria_build_site import enrich_search_index
    from textoria_export import load_archive
    data = load_archive(paths)
    from textoria_build_site import annotate_page_divisions
    annotate_page_divisions(data)
    search_index = enrich_search_index(data, reader_paragraphs)
    write_browser_search_index(paths, search_index)
    write_stage_report(paths, "build_fulltext_search", {"ok": True, "paragraph_count": len(reader_paragraphs)})
    return search_index


INDEX_PREFIX = "window.TEXTORIA_SEARCH_INDEX = "


def write_browser_search_index(paths: BuildPaths, search_index: dict) -> Path:
    """Write one classic script index usable over HTTP and file URLs."""
    payload = json.dumps(search_index, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    target = paths.site_data / "search_index.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(INDEX_PREFIX + payload + ";\n", encoding="utf-8")
    return target


def read_browser_search_index(path: Path) -> dict:
    """Parse the generated JSON payload without executing JavaScript."""
    content = path.read_text(encoding="utf-8").strip()
    if not content.startswith(INDEX_PREFIX) or not content.endswith(";"):
        raise ValueError("Invalid browser search-index wrapper")
    return json.loads(content[len(INDEX_PREFIX):-1])
