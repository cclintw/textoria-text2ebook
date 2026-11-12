#!/usr/bin/env python3
"""Check Textoria's local Python runtime dependencies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys


REQUIRED_PACKAGES = ["charset_normalizer", "bs4", "jinja2", "markdown_it", "pypinyin"]


def check_runtime(*, check_sqlite: bool = False) -> dict:
    missing = [name for name in REQUIRED_PACKAGES if importlib.util.find_spec(name) is None]
    result = {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 10),
        "required_packages": REQUIRED_PACKAGES,
        "missing_packages": missing,
        "ready": sys.version_info >= (3, 10) and not missing,
    }
    if check_sqlite:
        try:
            import sqlite3
        except ImportError:
            fts5 = False
        else:
            try:
                with sqlite3.connect(":memory:") as con:
                    con.execute("CREATE VIRTUAL TABLE test_fts USING fts5(text)")
                fts5 = True
            except sqlite3.Error:
                fts5 = False
        result.update(sqlite_fts5=fts5, ready=result['ready'] and fts5)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-sqlite', action='store_true', help='Require SQLite FTS5 for a database task')
    result = check_runtime(check_sqlite=parser.parse_args().check_sqlite)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
