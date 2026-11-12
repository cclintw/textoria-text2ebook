#!/usr/bin/env python3
"""Persist one validated archive checkpoint; export CSV only on request."""
from __future__ import annotations

from textoria_common import BuildPaths, CSV_FIELDS, read_json, write_csv, write_json, write_stage_report

REQUIRED_TABLES = ("collections", "documents", "divisions", "paragraphs", "source_files", "metadata")


def reader_paragraphs(data: dict) -> list[dict]:
    divs = {row["division_id"]: row for row in data["divisions"]}
    return [{**row, "division_path": divs[row["division_id"]].get("path", ""),
             "division_title": divs[row["division_id"]].get("title", "")}
            for row in data["paragraphs"]]


def validate_archive(data: dict) -> None:
    for table in REQUIRED_TABLES:
        if table not in data or not isinstance(data[table], list):
            raise ValueError(f"Missing archive table: {table}")
    for table, fields in CSV_FIELDS.items():
        rows = data.get(table, [])
        ids = set()
        for row in rows:
            missing = set(fields) - row.keys()
            if missing:
                raise ValueError(f"Missing {table} fields: {sorted(missing)}")
            identity = row[fields[0]]
            if identity in ids:
                raise ValueError(f"Duplicate {table} ID: {identity}")
            ids.add(identity)
    if len(data['collections']) != 1:
        raise ValueError('An archive must contain exactly one collection')
    collections = {r['collection_id'] for r in data['collections']}
    docs = {r['document_id'] for r in data['documents']}
    divs = {r['division_id']: r for r in data['divisions']}
    paras = {r['paragraph_id']: r for r in data['paragraphs']}
    for table in ('documents', 'divisions', 'paragraphs', 'source_files', 'sentences', 'tokens'):
        for row in data.get(table, []):
            if row['collection_id'] not in collections:
                raise ValueError(f'Unknown collection in {table}')
            if row.get('document_id') and row['document_id'] not in docs:
                raise ValueError(f'Unknown document in {table}')
    for row in divs.values():
        visited = {row['division_id']}
        parent = row.get('parent_division_id')
        while parent:
            if parent not in divs or parent in visited:
                raise ValueError('Invalid division parent or cycle')
            visited.add(parent)
            parent = divs[parent].get('parent_division_id')
    for row in paras.values():
        if row['division_id'] not in divs or divs[row['division_id']]['document_id'] != row['document_id']:
            raise ValueError('Invalid paragraph division')
    for row in data.get('sentences', []):
        if row['paragraph_id'] not in paras:
            raise ValueError('Unknown sentence paragraph')


def load_archive(paths: BuildPaths) -> dict:
    data = read_json(paths.intermediate / 'archive.json')
    validate_archive(data)
    data.setdefault('sentences', [])
    data.setdefault('tokens', [])
    return data


def export_intermediate_files(paths: BuildPaths, data: dict, *, export_csv: bool = False) -> dict:
    validate_archive(data)
    checkpoint = {key: value for key, value in data.items()
                  if key not in ('sentences', 'tokens') or value}
    write_json(paths.intermediate / 'archive.json', checkpoint)
    if export_csv:
        for table, fields in CSV_FIELDS.items():
            if table in ('sentences', 'tokens') and not data.get(table):
                continue
            write_csv(paths.csv / f'{table}.csv', data.get(table, []), fields)
    counts = {key: len(data.get(key, [])) for key in ('documents', 'divisions', 'paragraphs', 'sentences', 'tokens')}
    write_stage_report(paths, 'export_intermediate_files', {'ok': True, 'counts': counts})
    return {'counts': counts, 'reader_paragraphs': reader_paragraphs(data)}
