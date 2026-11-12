#!/usr/bin/env python3
"""Textoria UTF-8 preparation stage."""

from __future__ import annotations

import hashlib
import unicodedata
import re
from pathlib import Path

from charset_normalizer import from_bytes

from textoria_common import BuildPaths, SUPPORTED_EXTENSIONS, write_json, write_stage_report


def detect_encoding(raw: bytes) -> tuple[str, float | None]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", 1.0
    try:
        raw.decode("utf-8")
        return "utf-8", 1.0
    except UnicodeDecodeError:
        pass

    for encoding in ("big5hkscs", "big5", "shift_jis", "gb2312"):
        try:
            raw.decode(encoding)
            return encoding, None
        except UnicodeDecodeError:
            continue
    result = from_bytes(raw).best()
    if result and result.encoding:
        return result.encoding, getattr(result, "percent_coherence", None)
    return "big5", None


def decode_to_text(raw: bytes, encoding: str) -> str:
    candidates = [encoding]
    if encoding.lower().replace("-", "") in {"big5", "big5hkscs"}:
        candidates = ["big5hkscs", "big5"]
    for candidate in candidates:
        try:
            return raw.decode(candidate, errors="replace")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="replace")


def normalize_decoded_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    text = text.replace("\ufffd", "■")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    return unicodedata.normalize("NFKC", text)


def inspect_input(source: Path, config: dict | None = None) -> dict:
    if not source.is_file():
        raise ValueError(f"Source file does not exist: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input format: {source.suffix}")
    raw = source.read_bytes()
    encoding, confidence = detect_encoding(raw)
    text = decode_to_text(raw, encoding)
    return {
        "source_file": str(source), "extension": source.suffix.lower(),
        "detected_format": source.suffix.lower().lstrip("."),
        "detected_encoding": encoding, "encoding_confidence": confidence,
        "byte_size": len(raw), "line_count": text.count("\n") + 1,
        "has_bom": raw.startswith(b"\xef\xbb\xbf"), "readable": bool(text.strip()),
        "sha256": hashlib.sha256(raw).hexdigest(), "warnings": [],
    }


def prepare_utf8(source: Path, paths: BuildPaths, *, persist: bool = False) -> dict:
    manifest = inspect_input(source)
    decoded = normalize_decoded_text(decode_to_text(source.read_bytes(), manifest["detected_encoding"]))
    prepared_path = None
    if persist:
        paths.prepared.mkdir(parents=True, exist_ok=True)
        prepared_path = paths.prepared / f"{source.stem}.utf8{source.suffix.lower()}"
        prepared_path.write_text(decoded, encoding="utf-8")
        manifest["prepared_path"] = str(prepared_path)
    write_stage_report(paths, "convert_encoding", {"ok": True, "source_manifest": manifest})
    return {"text": decoded, "prepared_path": prepared_path, "manifest": manifest}
