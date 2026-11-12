#!/usr/bin/env python3
"""Validate compact archives, website links and search targets; optionally check SQLite."""
from __future__ import annotations

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

from textoria_common import BuildPaths, ensure_dirs, write_stage_report
from textoria_export import load_archive
from textoria_build_search import read_browser_search_index


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id'):
            self.ids.add(values['id'])
        for key in ('href', 'src'):
            if values.get(key):
                self.links.append(values[key])


def validate_outputs(paths: BuildPaths, db_path: Path | None = None) -> dict:
    errors = []
    required = [paths.intermediate / 'archive.json', paths.site / 'index.html', paths.site / 'read.html',
                paths.site / 'search.html', paths.site / 'assets/css/style.css',
                paths.site / 'assets/js/reader.js', paths.site / 'assets/js/reader-search.js',
                paths.site_data / 'search_index.js']
    if db_path is not None:
        required.append(db_path)
    for path in required:
        if not path.is_file():
            errors.append(f'Missing required file: {path}')
    data = None
    if (paths.intermediate / 'archive.json').exists():
        try:
            data = load_archive(paths)
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'Invalid archive checkpoint: {exc}')
    counts = {}
    expected_ids = []
    paragraph_ids = set()
    if data is not None:
        counts = {table: len(data.get(table, [])) for table in
                  ('collections', 'documents', 'divisions', 'paragraphs', 'sentences', 'tokens')}
        if not counts['paragraphs']:
            errors.append('Archive contains no paragraphs')
        expected_ids = [r['division_id'] for r in data['divisions']
                        if not r.get('parent_division_id') or r['level'] == 1]
        paragraph_ids = {r['paragraph_id'] for r in data['paragraphs']}
    if db_path is not None and db_path.is_file():
        import sqlite3
        with sqlite3.connect(db_path) as con:
            try:
                if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    errors.append('SQLite integrity check failed')
                db_counts = {table: con.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                             for table in ('collections', 'documents', 'divisions', 'paragraphs', 'sentences', 'tokens', 'paragraphs_fts')}
                if db_counts['paragraphs'] == 0 or db_counts['paragraphs_fts'] != db_counts['paragraphs']:
                    errors.append('Missing or incomplete paragraph FTS index')
                if con.execute('SELECT count(*) FROM paragraphs p LEFT JOIN divisions d ON p.division_id=d.division_id WHERE d.division_id IS NULL OR p.document_id<>d.document_id').fetchone()[0]:
                    errors.append('Broken paragraph linkage')
                if data:
                    for table in ('collections', 'documents', 'divisions', 'paragraphs', 'sentences', 'tokens'):
                        if len(data.get(table, [])) != db_counts[table]:
                            errors.append(f'Checkpoint/database count mismatch: {table}')
                sample = con.execute("SELECT division_title FROM paragraphs_fts WHERE division_title<>'' LIMIT 1").fetchone()
                if sample and not con.execute('SELECT count(*) FROM paragraphs_fts WHERE paragraphs_fts MATCH ?', ('"' + sample[0].replace('"', '""') + '"',)).fetchone()[0]:
                    errors.append('Sample FTS query returned no rows')
            except sqlite3.Error as exc:
                errors.append(f'SQLite validation failed: {exc}')
    pages = {}
    for path in paths.site.rglob('*.html'):
        parsed = PageLinks()
        parsed.feed(path.read_text(encoding='utf-8'))
        pages[path.resolve()] = parsed
    for path, parsed in pages.items():
        for link in parsed.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(paths.site.resolve()) or not target.is_file():
                errors.append(f'Broken website reference: {path.name}: {link}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'Broken anchor: {path.name}: {link}')
    for identity in expected_ids:
        if not (paths.site / 'read' / f'{identity}.html').exists():
            errors.append(f'Missing reading page: {identity}')
    for page in [paths.site / 'read.html', paths.site / 'search.html', *sorted((paths.site / 'read').glob('*.html'))]:
        if not page.exists():
            continue
        html = page.read_text(encoding='utf-8')
        index_position = html.find('data/search_index.js')
        search_position = html.find('js/reader-search.js')
        if index_position < 0 or search_position < 0 or index_position >= search_position:
            errors.append(f'Search index must load before reader search UI: {page.name}')

    index_path = paths.site_data / 'search_index.js'
    if index_path.exists():
        try:
            rows = read_browser_search_index(index_path)['paragraphs']
            if {r['paragraph_id'] for r in rows} != paragraph_ids or len(rows) != counts.get('paragraphs'):
                errors.append('Website search index differs from archive paragraphs')
            if data is not None:
                indexed = {r['paragraph_id']: r for r in rows}
                for paragraph in data['paragraphs']:
                    row = indexed.get(paragraph['paragraph_id'])
                    if row is not None and row.get('text') != paragraph['text']:
                        errors.append(f'Stale search text: {paragraph["paragraph_id"]}')
            for row in rows:
                url = urlsplit(row['href'])
                target = (paths.site / url.path).resolve()
                if target not in pages or url.fragment not in pages[target].ids:
                    errors.append(f'Broken search result: {row["paragraph_id"]}')
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(f'Invalid search index: {exc}')
    result = {'ok': not errors, 'counts': counts, 'site': str(paths.site),
              'division_pages': len(list((paths.site / 'read').glob('*.html'))),
              'top_level_division_pages_expected': len(expected_ids), 'errors': errors}
    if db_path is not None:
        result['sqlite'] = str(db_path)
    write_stage_report(paths, 'validate_output', result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate a Textoria archive.')
    parser.add_argument('collection_root')
    parser.add_argument('--check-sqlite', action='store_true', help='Also validate an explicitly generated database')
    args = parser.parse_args()
    paths = ensure_dirs(Path(args.collection_root).resolve())
    result = validate_outputs(paths, paths.sqlite / 'library.sqlite' if args.check_sqlite else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
