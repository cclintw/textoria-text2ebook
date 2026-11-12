#!/usr/bin/env python3
"""Preserve source files and bind chapter approval to a reviewed text version."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from textoria_common import now_iso, read_json, write_json


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def working_text_path(root: Path) -> Path:
    modern = root / 'content' / '全文.md'
    legacy = root / 'clean' / 'cleaned_text.md'
    if modern.exists() and legacy.exists():
        raise ValueError('Both content/全文.md and clean/cleaned_text.md exist; select one authoritative working text before continuing')
    return legacy if legacy.exists() else modern


def preserve_source(source: Path, root: Path, inspection: dict) -> dict:
    """Keep immutable source versions; never overwrite a different saved source."""
    data = source.read_bytes()
    if digest_bytes(data) != inspection['sha256']:
        raise ValueError('Source changed after inspection; inspect it again before saving')
    target = root / 'source' / source.name
    if target.exists() and digest_file(target) != inspection['sha256']:
        target = target.with_name(f'{target.stem}-{inspection["sha256"][:12]}{target.suffix}')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if digest_file(target) != inspection['sha256']:
            raise ValueError('Saved-source filename collision; existing source was preserved')
    elif source.resolve() != target.resolve():
        # Exclusive creation protects a saved version from concurrent replacement.
        with target.open('xb') as stream:
            stream.write(data)
        shutil.copystat(source, target)
    if digest_file(target) != inspection['sha256']:
        raise ValueError('Saved-source verification failed')
    return {**inspection, 'saved_path': str(target.resolve()), 'original_path': inspection['source_file']}


def structural_title(row: dict) -> str:
    extra = json.loads(row.get('metadata_json') or '{}')
    return extra.get('text2ebook_structure_title', row['title'])


def _outline(data: dict) -> str:
    lines = [f'# {structural_title(data["collections"][0])} 章節目錄', '']
    for document in data['documents']:
        lines.extend([f'## {structural_title(document)}', ''])
        for division in data['divisions']:
            if division['document_id'] == document['document_id']:
                label = ' '.join(division['title'].splitlines())
                lines.append('  ' * (int(division['level']) - 1) + '- ' + label)
        lines.append('')
    if data['structure_report']['confidence'] == 'low':
        lines.extend(['章節標題辨識依據不足；目前目錄依段落歸集，尚未完成章節辨識。', ''])
    return '\n'.join(lines).rstrip() + '\n'


def _structure(data: dict) -> tuple[str, list[dict]]:
    documents = [[d['document_id'], structural_title(d)] for d in data['documents']]
    divisions = [[d['division_id'], d['document_id'], d['parent_division_id'], d['level'], d['title']]
                 for d in data['divisions']]
    assignments = [{'text_hash': digest_bytes(p['text'].encode()), 'document_id': p['document_id'],
                    'division_id': p['division_id']} for p in data['paragraphs']]
    # Body wording changes alone do not change the chapter topology.
    topology = [documents, divisions, [[p['document_id'], p['division_id']] for p in data['paragraphs']]]
    return digest_bytes(json.dumps(topology, ensure_ascii=False, sort_keys=True).encode()), assignments


def _moved_paragraphs(before: list[dict], after: list[dict]) -> bool:
    def locations(rows):
        result = {}
        for row in rows:
            result.setdefault(row['text_hash'], []).append((row['document_id'], row['division_id']))
        return result
    old, new = locations(before), locations(after)
    return any(old[key] != new[key] for key in old.keys() & new.keys())


def prepare_review(root: Path, text_path: Path, data: dict, *, confirm_token: str | None = None) -> dict:
    """Write the outline first; approval requires a previously issued current token."""
    state_path = root / 'state.json'
    state = read_json(state_path) if state_path.exists() else {'schema_version': 2, 'stages': {}}
    previous = state.get('reviews', {}).get('chapters', {})
    outline_path = root / 'content' / '章節目錄.md'
    content = _outline(data)
    outline_hash = digest_bytes(content.encode())
    outline_changed = outline_path.exists() and digest_file(outline_path) != outline_hash
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    if not outline_path.exists() or outline_changed:
        outline_path.write_text(content, encoding='utf-8')
    topology_hash, assignments = _structure(data)
    input_hash = digest_file(text_path)
    review_token = digest_bytes(json.dumps([input_hash, outline_hash, topology_hash]).encode())
    current = (data['structure_report']['confidence'] != 'low'
               and previous.get('status') == 'confirmed'
               and previous.get('heading_hash') == topology_hash
               and previous.get('outline_hash') == outline_hash
               and not outline_changed
               and not _moved_paragraphs(previous.get('assignments', []), assignments))
    record = {'status': 'confirmed' if current else 'pending', 'input_hash': input_hash,
              'outline_hash': outline_hash, 'heading_hash': topology_hash,
              'review_token': review_token, 'assignments': assignments,
              'working_text': str(text_path.resolve()), 'outline': str(outline_path.resolve()),
              'confidence': data['structure_report']['confidence'], 'updated_at': now_iso()}
    if current:
        record['confirmed_at'] = previous['confirmed_at']
        record['confirmed_input_hash'] = previous.get('confirmed_input_hash', previous.get('input_hash'))
    accepted = bool(confirm_token and confirm_token == review_token
                    and previous.get('review_token') == confirm_token and not outline_changed)
    error = None
    if confirm_token and not accepted:
        error = 'Chapter review changed or has not been presented; inspect the current files and confirm the new review token'
    if accepted and data['structure_report']['confidence'] == 'low':
        accepted = False
        error = 'Chapter headings are not usable yet; mark the working text with #, ##, ### and review again'
    if accepted:
        record.update(status='confirmed', confirmed_at=now_iso(), confirmed_input_hash=input_hash)
    state.setdefault('reviews', {})['chapters'] = record
    state['updated_at'] = now_iso()
    write_json(state_path, state)
    ready = record['status'] == 'confirmed' and error is None
    guidance = ('請先檢查章節層級與順序。可在對話中說明修正，或開啟全文工作檔，'
                '以 # 表示全書標題、## 表示主要章節、### 表示下層章節；標題獨立一行，空行分段。'
                '修正後需重新整理目錄；確認前不生成資料庫、網站或 EPUB。')
    return {'ok': ready, 'status': 'chapters_confirmed' if ready else 'needs_chapter_confirmation',
            'output': str(root.resolve()), 'cleaned_text': str(text_path.resolve()),
            'outline': str(outline_path.resolve()), 'review_token': review_token,
            'structure_confidence': data['structure_report']['confidence'],
            'structure_evidence': data['structure_report']['evidence'],
            'candidate_heading_samples': data['structure_report'].get('candidate_heading_samples', []),
            'division_count': len(data['divisions']),
            'division_sample': [d['path'] for d in data['divisions'][:12]],
            'links': {'全文': str(text_path.resolve()), '章節目錄': str(outline_path.resolve())},
            'message': error or ('章節已確認；下一步整理基本書籍 metadata。' if ready else guidance),
            'heading_example': '# 全書標題\n\n## 卷上\n\n卷上正文。\n\n### 第一節\n\n第一節正文。\n\n## 卷下\n\n卷下正文。\n',
            'next_step': 'metadata' if ready else 'review_chapters'}
