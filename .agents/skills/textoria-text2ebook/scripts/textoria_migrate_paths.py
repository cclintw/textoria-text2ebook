#!/usr/bin/env python3
"""Migrate verified legacy Textoria roots without merging unrelated folders."""
from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import tarfile
from pathlib import Path

from textoria_common import SKILL_NAMESPACE, RUNTIME_DIRECTORY

TEXT_FIELDS = {'text', 'title', 'name', 'description', 'subtitle', 'label', 'normalized_text'}


def migration_plan(project: Path) -> dict:
    old = project / 'textoria'
    runtime = project / '.textoria'
    pairs = []
    if old.exists():
        if old.is_symlink() or not (old / 'registry.json').is_file():
            raise ValueError('Legacy textoria/ is not a verified collection root')
        registry = json.loads((old / 'registry.json').read_text(encoding='utf-8'))
        if not isinstance(registry.get('collections'), list) or not registry['collections']:
            raise ValueError('Legacy registry has no verifiable collections')
        for row in registry['collections']:
            path = Path(row['path'])
            root = path if path.is_absolute() else project / path
            root = root.resolve()
            if not root.is_relative_to((old / 'collections').resolve()):
                raise ValueError('Legacy registry points outside its collection root')
            if not (root / 'sqlite/library.sqlite').is_file() and not (root / 'intermediate/archive.json').is_file():
                raise ValueError('Legacy collection has no verifiable database or checkpoint')
        pairs.append((old, project / SKILL_NAMESPACE))
    if runtime.exists():
        if runtime.is_symlink() or not (runtime / 'logs/runtime_check.json').is_file():
            raise ValueError('Legacy .textoria/ ownership is unverified; leave it unchanged')
        required = set(json.loads((runtime / 'logs/runtime_check.json').read_text()).get('required_packages', []))
        if not {'charset_normalizer', 'bs4', 'jinja2', 'markdown_it', 'pypinyin'} <= required:
            raise ValueError('Legacy runtime does not match the Textoria dependency manifest')
        if set(p.name for p in runtime.iterdir()) - {'venv', 'logs', 'backups'}:
            raise ValueError('Legacy runtime contains unrecognized files; leave it unchanged')
        pairs.append((runtime, project / RUNTIME_DIRECTORY))
    for before, after in pairs:
        if after.exists() or after.is_symlink():
            raise ValueError(f'Destination already exists; no folders were merged: {after}')
    return {'project_root': str(project), 'moves': [{'from': str(a), 'to': str(b)} for a, b in pairs]}


def rebase(value: str, project: Path) -> str:
    for old, new in [('textoria', SKILL_NAMESPACE), ('.textoria', RUNTIME_DIRECTORY)]:
        for before, after in [(str(project / old), str(project / new)), (old, new)]:
            if value == before or value.startswith(before + '/'):
                return after + value[len(before):]
    return value


def rebase_json(value, project: Path, key: str = ''):
    if key in TEXT_FIELDS:
        return value
    if isinstance(value, dict):
        return {k: rebase_json(v, project, k) for k, v in value.items()}
    if isinstance(value, list):
        return [rebase_json(v, project, key) for v in value]
    return rebase(value, project) if isinstance(value, str) else value


def migrate(project: Path) -> dict:
    plan = migration_plan(project)
    if not plan['moves']:
        return {**plan, 'ok': True, 'changed_files': 0}
    runtime = project / '.textoria'
    backup_root = runtime / 'backups' if runtime.exists() else project / RUNTIME_DIRECTORY / 'backups'
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / 'before-namespace-migration.tar.gz'
    if backup.exists():
        raise ValueError(f'Migration backup already exists: {backup}')
    with tarfile.open(backup, 'w:gz') as archive:
        if (project / 'textoria').exists():
            archive.add(project / 'textoria', arcname='textoria')
        for path in (runtime / 'venv/bin', runtime / 'venv/pyvenv.cfg'):
            if path.exists():
                archive.add(path, arcname=str(path.relative_to(project)))
    moved = []
    originals = {}
    def replace_file(path: Path, content: bytes):
        originals.setdefault(path, path.read_bytes())
        path.write_bytes(content)
    try:
        for pair in plan['moves']:
            before, after = Path(pair['from']), Path(pair['to'])
            before.rename(after)
            moved.append((before, after))
        output = project / SKILL_NAMESPACE
        output_moved = any(before == project / 'textoria' for before, _ in moved)
        for path in (output.rglob('*.json') if output_moved else []):
            if 'original' in path.relative_to(output).parts:
                continue
            value = json.loads(path.read_text(encoding='utf-8'))
            updated = rebase_json(value, project)
            if value != updated:
                replace_file(path, (json.dumps(updated, ensure_ascii=False, indent=2) + '\n').encode())
        for path in (output.glob('collections/*/csv/*.csv') if output_moved else []):
            with path.open(encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                fields = reader.fieldnames
                rows = list(reader)
            updated = [rebase_json(row, project) for row in rows]
            if rows != updated:
                buffer = io.StringIO(newline='')
                writer = csv.DictWriter(buffer, fieldnames=fields)
                writer.writeheader()
                writer.writerows(updated)
                replace_file(path, buffer.getvalue().encode())
        for path in (output.glob('collections/*/sqlite/library.sqlite') if output_moved else []):
            originals[path] = path.read_bytes()
            with sqlite3.connect(path) as con:
                for table, fields in [('source_files', ('original_path', 'prepared_path', 'extracted_text_path')),
                                      ('documents', ('source_file',)), ('paragraphs', ('source_file',))]:
                    for field in fields:
                        rows = con.execute(f'SELECT rowid, {field} FROM {table}').fetchall()
                        for rowid, value in rows:
                            if isinstance(value, str) and rebase(value, project) != value:
                                con.execute(f'UPDATE {table} SET {field}=? WHERE rowid=?', (rebase(value, project), rowid))
                if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError(f'SQLite integrity check failed: {path}')
        venv = project / RUNTIME_DIRECTORY / 'venv'
        runtime_files = list((venv / 'bin').glob('*')) + [venv / 'pyvenv.cfg']
        for path in runtime_files:
            if not path.is_file() or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            updated = text.replace(str(project / '.textoria') + '/', str(project / RUNTIME_DIRECTORY) + '/')
            if text != updated:
                replace_file(path, updated.encode())
    except Exception:
        for path, content in originals.items():
            path.write_bytes(content)
        for before, after in reversed(moved):
            after.rename(before)
        raise
    return {**plan, 'ok': True, 'changed_files': len(originals), 'backup': rebase(str(backup), project)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True)
    parser.add_argument('--apply', action='store_true', help='Apply the inspected migration plan')
    args = parser.parse_args()
    try:
        project = Path(args.project_root).resolve()
        result = migrate(project) if args.apply else migration_plan(project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
