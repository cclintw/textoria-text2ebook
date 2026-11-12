#!/usr/bin/env python3
"""Prepare, edit and approve basic ebook metadata without inferring publication facts."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from textoria_common import now_iso, read_json, write_json
from textoria_utf8_converter import detect_encoding, decode_to_text

ROLES = {'作者': 'creators', '編者': 'creators', '校註者': 'contributors', '校訂者': 'contributors'}
ALIASES = {'書名': 'title', 'title': 'title', '作者': '作者', 'author': '作者', 'creator': '作者',
           '編者': '編者', 'editor': '編者', '校註者': '校註者', 'annotator': '校註者',
           '校訂者': '校訂者', '校對者': '校訂者', 'reviser': '校訂者',
           'creators': 'creators', 'contributors': 'contributors', 'extra': 'extra'}
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def unique_json(text: str):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate metadata JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique)


def _label(value: str) -> str:
    return ALIASES.get(value.strip(), value.strip())


def _people(value, role: str | None = None) -> list[dict]:
    if value is None or value == '':
        return []
    if isinstance(value, str):
        value = [x.strip() for x in re.split('[、;；]', value) if x.strip()]
    if not isinstance(value, list):
        raise ValueError('Person fields must contain a name, a list of names, or name/role objects')
    result = []
    for person in value:
        if isinstance(person, str) and role:
            row = {'name': person.strip(), 'role': role}
        elif isinstance(person, dict) and isinstance(person.get('name'), str):
            row = {'name': person['name'].strip(), 'role': person.get('role', role)}
        else:
            raise ValueError('Each person must have a name and role')
        if not row['name'] or not isinstance(row['role'], str) or not row['role'].strip():
            raise ValueError('Person names and roles must not be empty')
        row['role'] = row['role'].strip()
        if row not in result:
            result.append(row)
    return result


def normalize(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError('Metadata must be a single named object')
    unknown = set(value) - {'title', 'creators', 'contributors', 'extra'}
    if unknown:
        raise ValueError('Unrecognized canonical metadata keys: ' + ', '.join(sorted(unknown)))
    title = value.get('title', '')
    if not isinstance(title, str) or not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('書名為必要欄位，不可刪除或留空。')
    extra = value.get('extra', {})
    if not isinstance(extra, dict):
        raise ValueError('extra must be a named object')
    creators = _people(value.get('creators', []))
    contributors = _people(value.get('contributors', []))
    if any(p['role'] not in ('作者', '編者') for p in creators):
        raise ValueError('creators supports 作者／編者; use contributors for other roles')
    if any(p['role'] in ('作者', '編者') for p in contributors):
        raise ValueError('作者／編者 must be stored in creators')
    return {'title': title.strip(), 'creators': creators, 'contributors': contributors, 'extra': extra}


def apply_patch(value: dict, patch: dict, deletes: list[str]) -> tuple[dict, list[str]]:
    if not isinstance(patch, dict):
        raise ValueError('Metadata patch must be a JSON object')
    result = json.loads(json.dumps(value, ensure_ascii=False))
    changed_fields = []
    seen = set()
    keys = {_label(key) for key in patch}
    if ('creators' in keys and keys & {'作者', '編者'}) or ('contributors' in keys and keys & {'校註者', '校訂者'}):
        raise ValueError('Use either a person-list field or role fields in one update, not both')
    for key, item in patch.items():
        key = _label(key)
        if key in seen:
            raise ValueError('Conflicting duplicate metadata field: ' + key)
        seen.add(key)
        changed_fields.append(key)
        if key in ROLES:
            group = ROLES[key]
            result[group] = [p for p in result.get(group, []) if p['role'] != key] + _people(item, key)
        elif key == 'title':
            result['title'] = item
        elif key in ('creators', 'contributors'):
            result[key] = _people(item)
        elif key == 'extra':
            if not isinstance(item, dict):
                raise ValueError('extra must be an object')
            for field, extra_value in item.items():
                if extra_value is None:
                    result.setdefault('extra', {}).pop(field, None)
                else:
                    result.setdefault('extra', {})[field] = extra_value
                changed_fields.append('extra.' + field)
        else:
            field = key.removeprefix('extra.')
            if item is None:
                result.setdefault('extra', {}).pop(field, None)
            else:
                result.setdefault('extra', {})[field] = item
    for label in deletes:
        key = _label(label)
        changed_fields.append(key)
        if key == 'title':
            raise ValueError('書名為必要欄位，不可刪除或留空。')
        if key in ROLES:
            group = ROLES[key]
            result[group] = [p for p in result.get(group, []) if p['role'] != key]
        elif key in ('creators', 'contributors'):
            result[key] = []
        else:
            result.setdefault('extra', {}).pop(key.removeprefix('extra.'), None)
    return normalize(result), changed_fields


def infer(text: str, data: dict, path: Path) -> tuple[dict, list[dict]]:
    """Only explicit labeled lines are deterministic person evidence."""
    title = data['documents'][0]['title'] if data['documents'] else data['collections'][0]['title']
    value = {'title': title, 'creators': [], 'contributors': [], 'extra': {}}
    evidence = [{'field': 'title', 'source': str(path), 'basis': 'document heading or source filename', 'value': title}]
    labeled = {}
    fence = None
    # Do not search body prose for arbitrary names or treat preface signatures as book authors.
    for number, line in enumerate(text.splitlines()[:160], start=1):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = (marker[1][0], len(marker[1]))
            continue
        if re.match(r'^##\s', line):
            break
        match = re.fullmatch(r'\s*(書名|作者|編者|校註者|校訂者)\s*[：:]\s*(\S.{0,99})\s*', line)
        if match:
            key, item = match.groups()
            if key in labeled and labeled[key] != item:
                # Ambiguous labels remain evidence for dialogue, not an arbitrary overwrite.
                evidence.append({'field': _label(key), 'source': str(path), 'line': number,
                                 'value': item, 'basis': 'conflicting explicit label; requires review'})
                continue
            labeled[key] = item
            evidence.append({'field': _label(key), 'source': str(path), 'line': number, 'value': item, 'basis': 'explicit label'})
    value, _ = apply_patch(value, labeled, [])
    return value, evidence


def _table(rows: list[list]) -> dict:
    rows = [row for row in rows if any(str(v).strip() for v in row)]
    if not rows:
        raise ValueError('Metadata table is empty')
    header = [str(v).strip() for v in rows[0]]
    if len(header) == 2 and header[0] in ('欄位', 'field', 'key') and header[1] in ('內容', '值', 'value'):
        pairs = [row + [''] if len(row) == 1 else row for row in rows[1:]]
    else:
        if len(rows) != 2:
            raise ValueError('Metadata table has multiple records; select one book or use a field/value table')
        if len(rows[1]) < len(header): rows[1] += [''] * (len(header) - len(rows[1]))
        if len(header) != len(rows[1]):
            raise ValueError('Metadata header and value columns do not match')
        pairs = list(zip(header, rows[1]))
    result = {}
    for row in pairs:
        if len(row) != 2 or not str(row[0]).strip():
            raise ValueError('Every metadata row must have a field and value')
        key = _label(str(row[0]))
        if key in result:
            raise ValueError('Duplicate metadata field; combine multiple names in one field: ' + key)
        result[key] = str(row[1]).strip()
    return result


def _xlsx(raw: bytes, sheet: str | None) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(item.file_size for item in archive.infolist()) > 32 * 1024 * 1024:
            raise ValueError('Metadata workbook is too large for the metadata importer')
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(node.text or '' for node in item.findall('.//s:t', NS))
                       for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {r.attrib['Id']: r.attrib['Target'] for r in relationships}
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        choices = []
        for entry in workbook.find('s:sheets', NS):
            name = entry.attrib['name']
            if sheet is not None and name != sheet:
                continue
            relation = entry.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = targets[relation]
            member = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            rows = []
            for row in ET.fromstring(archive.read(member)).findall('.//s:sheetData/s:row', NS):
                cells = {}
                for cell in row.findall('s:c', NS):
                    if cell.find('s:f', NS) is not None:
                        raise ValueError('Metadata formulas are not evaluated; replace them with literal values')
                    column = re.match(r'[A-Z]+', cell.attrib.get('r', ''))
                    if not column:
                        raise ValueError('Workbook cells require column addresses')
                    index = 0
                    for char in column[0]: index = index * 26 + ord(char) - 64
                    if index > 16384: raise ValueError('Metadata worksheet has invalid column addresses')
                    node = cell.find('s:v', NS)
                    value = node.text or '' if node is not None else ''
                    if cell.attrib.get('t') == 's': value = strings[int(value)]
                    elif cell.attrib.get('t') == 'inlineStr': value = ''.join(node.text or '' for node in cell.findall('s:is//s:t', NS))
                    cells[index - 1] = value
                if cells: rows.append([cells.get(i, '') for i in range(max(cells) + 1)])
            if any(any(str(v).strip() for v in row) for row in rows): choices.append((name, rows))
        if len(choices) != 1:
            raise ValueError('Select one nonempty metadata worksheet with --metadata-sheet')
        return _table(choices[0][1])


def read_import(path: Path, sheet: str | None = None) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    suffix = path.suffix.lower()
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError('Metadata file is too large for the metadata importer')
    if suffix == '.xlsx':
        try:
            return _xlsx(raw, sheet), raw
        except (zipfile.BadZipFile, ET.ParseError, IndexError, AttributeError, KeyError) as exc:
            raise ValueError('Invalid metadata XLSX structure: ' + str(exc)) from exc
    if suffix == '.xls':
        raise ValueError('Legacy .xls is not parsed; save it as .xlsx or CSV first')
    if suffix not in ('.json', '.csv', '.txt', '.md'):
        raise ValueError('Metadata input accepts JSON, CSV, XLSX, TXT or MD')
    encoding, _ = detect_encoding(raw)
    text = decode_to_text(raw, encoding).lstrip('\ufeff')
    if suffix == '.json':
        value = unique_json(text)
        if not isinstance(value, dict): raise ValueError('Metadata JSON must contain one object')
        return value, raw
    if suffix == '.csv': return _table(list(csv.reader(io.StringIO(text)))), raw
    pairs = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(?:[-*]\s+)?([^：:]+)[：:]\s*(.*?)\s*', line)
        if match: pairs.append([match[1].strip(), match[2]])
    if not pairs: raise ValueError('Text metadata needs labeled lines such as 書名：…、作者：…')
    return _table([['欄位', '內容']] + pairs), raw


def _save_import(root: Path, source: Path, raw: bytes) -> dict:
    target = root / 'source' / 'metadata' / source.name
    if target.exists() and _hash(target.read_bytes()) != _hash(raw):
        target = target.with_name(f'{target.stem}-{_hash(raw)[:12]}{target.suffix}')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw: raise ValueError('Metadata source filename collision')
    else:
        with target.open('xb') as stream: stream.write(raw)
    return {'original_path': str(source.resolve()), 'saved_path': str(target.resolve()),
            'sha256': _hash(raw), 'format': source.suffix.lower()}


def project_metadata(data: dict, value: dict) -> bool:
    """Project approved values while preserving the original chapter-review title."""
    before = json.dumps(data, ensure_ascii=False, sort_keys=True)
    collection = data['collections'][0]
    extra = json.loads(collection.get('metadata_json') or '{}')
    extra.setdefault('text2ebook_structure_title', collection['title'])
    extra['book_metadata'] = value
    collection.update(title=value['title'], name=value['title'], metadata_json=json.dumps(extra, ensure_ascii=False))
    # The current book contract has one metadata record; do not assign one author's identity to multiple documents.
    if len(data['documents']) == 1:
        document = data['documents'][0]
        extra = json.loads(document.get('metadata_json') or '{}')
        extra.setdefault('text2ebook_structure_title', document['title'])
        extra['book_metadata'] = value
        document.update(title=value['title'], creator='、'.join(p['name'] for p in value['creators']),
                        metadata_json=json.dumps(extra, ensure_ascii=False))
    changed = before != json.dumps(data, ensure_ascii=False, sort_keys=True)
    if changed: collection['updated_at'] = now_iso()
    return changed


def process_metadata(root: Path, text_path: Path, data: dict, *, token: str | None = None,
                     source_file: Path | None = None, patch: dict | None = None,
                     deletes: list[str] | None = None, sheet: str | None = None) -> dict:
    if patch is not None and not isinstance(patch, dict):
        raise ValueError('Metadata patch must be a JSON object')
    path, state_path = root / 'metadata.json', root / 'state.json'
    state = read_json(state_path)
    chapter = state.get('reviews', {}).get('chapters', {})
    if chapter.get('status') != 'confirmed':
        raise ValueError('Chapter confirmation is required before metadata work')
    previous = state.get('reviews', {}).get('metadata', {})
    if path.exists():
        value = normalize(unique_json(path.read_text(encoding='utf-8')))
        evidence = previous.get('evidence', [])
    elif previous:
        raise ValueError('Saved metadata.json is missing; restore it rather than overwriting approved edits with guesses')
    else:
        value, evidence = infer(text_path.read_text(encoding='utf-8'), data, text_path)
    fields = []
    imported = None
    if source_file is not None:
        imported, raw = read_import(source_file, sheet)
        value, changed = apply_patch(value, imported, [])
        fields += changed
    if patch or deletes:
        value, changed = apply_patch(value, patch or {}, deletes or [])
        fields += changed
    # A confirmation never mutates the values being approved at the same time.
    if token and (source_file is not None or patch or deletes):
        raise ValueError('Review metadata changes first, then confirm their issued token in a separate command')
    value = normalize(value)
    encoded = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    current_hash = _hash(encoded)
    # Bind approval to bytes too, so direct edits cannot reuse an earlier review token.
    existing_hash = _hash(path.read_bytes()) if path.exists() else None
    if not (source_file or patch or deletes) and existing_hash is not None:
        review_hash = existing_hash
    else:
        review_hash = current_hash
    review_token = _hash(json.dumps([review_hash, value], ensure_ascii=False, sort_keys=True).encode())
    current = previous.get('status') == 'confirmed' and previous.get('input_hash') == review_hash
    accepted = bool(token and token == previous.get('review_token') and token == review_token)
    error = None
    if token and not accepted:
        error = 'Metadata changed or has not been reviewed; present the current values and confirm their new token'
    inputs = previous.get('inputs', [])
    if source_file is not None:
        saved = _save_import(root, source_file, raw)
        if saved not in inputs: inputs.append(saved)
        evidence.append({'field': fields, 'source': saved['saved_path'], 'basis': 'user metadata file'})
    if patch or deletes:
        evidence.append({'field': fields, 'basis': 'dialogue-proposed update; requires confirmation'})
    if not path.exists() or source_file is not None or patch or deletes:
        path.write_bytes(encoded)
    removed = set(previous.get('removed_fields', []))
    for key in fields:
        if key in ROLES:
            present = any(p['role'] == key for p in value[ROLES[key]])
        elif key in ('creators', 'contributors'):
            present = bool(value[key])
        elif key.startswith('extra.'):
            present = key[6:] in value['extra']
        else:
            present = key == 'title' or key in value['extra']
        if present: removed.discard(key)
        else: removed.add(key)
    last = previous.get('last_values', {})
    for key in ('creators', 'contributors', *ROLES):
        group = ROLES.get(key, key)
        present = bool(value[group]) if key == group else any(p['role'] == key for p in value[group])
        was_present = bool(last.get(group)) if key == group else any(p['role'] == key for p in last.get(group, []))
        if present: removed.discard(key)
        elif was_present: removed.add(key)
    for key in set(last.get('extra', {})) | set(value['extra']):
        if key in value['extra']:
            removed.discard('extra.' + key)
            removed.discard(key)
        else:
            removed.add('extra.' + key)
    record = {'status': 'confirmed' if (current or accepted) and not error else 'pending',
              'input_hash': review_hash, 'review_token': review_token, 'evidence': evidence,
              'removed_fields': sorted(removed), 'inputs': inputs, 'last_values': value, 'updated_at': now_iso()}
    if accepted: record['confirmed_at'] = now_iso()
    elif current: record['confirmed_at'] = previous['confirmed_at']
    state.setdefault('reviews', {})['metadata'] = record
    state['updated_at'] = now_iso()
    write_json(state_path, state)
    ready = record['status'] == 'confirmed'
    return {'ok': ready, 'status': 'metadata_confirmed' if ready else 'needs_metadata_confirmation',
            'output': str(root.resolve()), 'metadata_file': str(path.resolve()), 'metadata': value,
            'metadata_token': review_token, 'evidence': evidence,
            'links': {'書籍資料': str(path.resolve())},
            'message': error or ('基本書籍資料已確認；下一步詢問選用素材。' if ready else
                '請確認基本書籍資料。可回覆「確認」，或在對話中新增、刪除、修改；亦可提供 CSV、XLSX、JSON、TXT／MD 檔案。'),
            'next_step': 'materials' if ready else 'review_metadata'}
