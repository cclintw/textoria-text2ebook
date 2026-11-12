#!/usr/bin/env python3
"""Exercise chapter approval and source retention through the public CLI."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name('textoria_build.py')


def call(*args, status=None):
    result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    value = json.loads(result.stdout)
    if status:
        assert value.get('status') == status, (result.stdout, result.stderr)
    assert result.returncode in (0, 1, 2), result.stderr
    return value, result.returncode


def approve(root, token):
    return call('--output', root, '--task', 'confirm_chapters', '--review-token', token)


with tempfile.TemporaryDirectory(prefix='text2ebook-chapters-') as folder:
    project = Path(folder).resolve()
    source = project / '示例.md'
    source.write_text('# 示例文獻\n\n## 卷上\n\n甲段正文。\n\n### 第一節\n\n乙段正文。\n\n## 卷下\n\n丙段正文。\n')
    original = source.read_bytes()
    result, code = call(source, '--project-root', project, '--collection-name', '示例文獻', status='needs_chapter_confirmation')
    assert code == 2 and result['structure_confidence'] == 'high'
    root = Path(result['output'])
    working, outline = Path(result['cleaned_text']), Path(result['outline'])
    assert working == root/'content/全文.md'
    assert outline == root/'content/章節目錄.md'
    assert (root/'source/示例.md').read_bytes() == original == source.read_bytes()
    assert '  - 第一節' in outline.read_text()
    assert result['links']['全文'] == str(working)
    assert '# 全書標題' in result['heading_example']
    assert all(not (root/p).exists() for p in ['intermediate/archive.json', 'sqlite', 'site'])
    call(source, '--project-root', project, status='needs_chapter_confirmation')
    assert len(list((project/'textoria-text2ebook/collections').iterdir())) == 1
    call('--output', root, '--task', 'build_sqlite', status='needs_chapter_confirmation')
    call('--output', root, '--task', 'confirm_chapters', status='needs_chapter_confirmation')
    assert json.loads((root/'state.json').read_text())['reviews']['chapters']['status'] == 'pending'
    print('PASS: default/high-confidence and direct database builds stop; both links and immutable source are saved')

    outline.write_text(outline.read_text()+'\n額外標題\n')
    invalid, code = approve(root, result['review_token'])
    assert code == 2
    assert '額外標題' not in outline.read_text()
    old_token = result['review_token']
    working.write_text(working.read_text().replace('### 第一節', '## 第一節'))
    revised, code = approve(root, old_token)
    assert code == 2 and revised['review_token'] != old_token
    assert '\n- 第一節' in outline.read_text()
    assert not (root/'intermediate/archive.json').exists()
    accepted, code = approve(root, revised['review_token'])
    assert code == 0 and accepted['next_step'] == 'metadata'
    archive = root/'intermediate/archive.json'
    assert archive.exists() and not (root/'site').exists()
    print('PASS: heading edits refresh the outline; stale approval is rejected; current approval proceeds only to metadata')

    metadata, code = call('--output', root, '--task', 'build_sqlite', status='needs_metadata_confirmation')
    assert code == 2
    accepted, code = call('--output', root, '--task', 'confirm_metadata', '--metadata-token', metadata['metadata_token'])
    assert code == 0
    material_review, code = call('--output', root, '--task', 'build_sqlite', status='needs_materials')
    assert code == 2
    skipped, code = call('--output', root, '--task', 'skip_materials')
    assert code == 0
    db_result, code = call('--output', root, '--task', 'build_sqlite')
    assert code == 0 and (root/'sqlite/library.sqlite').exists()
    db_before = (root/'sqlite/library.sqlite').read_bytes()
    archive_before = archive.read_bytes()
    working.write_text(working.read_text().replace('甲段正文', '甲段校正'))
    body, code = call('--output', root, '--task', 'review_chapters')
    assert code == 0 and body['status'] == 'chapters_confirmed'
    assert '甲段校正' in archive.read_text()
    # Moving unchanged paragraphs between divisions must invalidate approval even if counts stay the same.
    working.write_text(working.read_text().replace('甲段校正', 'SWAP').replace('乙段正文', '甲段校正').replace('SWAP', '乙段正文'))
    moved, code = call('--output', root, '--task', 'build_sqlite', status='needs_chapter_confirmation')
    assert code == 2 and (root/'sqlite/library.sqlite').read_bytes() == db_before
    assert archive.read_bytes() != archive_before  # The accepted body correction is already canonical.
    pending_archive = archive.read_bytes()
    again, _ = call('--output', root, '--task', 'build_sqlite', status='needs_chapter_confirmation')
    assert archive.read_bytes() == pending_archive
    accepted, code = approve(root, again['review_token'])
    assert code == 0
    assert archive.read_bytes() != pending_archive
    source.unlink()
    restored, code = call('--output', root, '--task', 'reclean_text')
    assert code == 0 and working.read_bytes() == original
    call('--output', root, '--task', 'review_chapters', status='needs_chapter_confirmation')
    print('PASS: body-only correction retains approval; paragraph relocation reopens it; saved source supports recleaning without the upload')

    source.write_bytes(original)
    newer = original.replace('甲段正文'.encode(), '不同版本'.encode())
    source.write_bytes(newer)
    call('--output', root, '--task', 'reclean_text')
    assert (root/'source/示例.md').read_bytes() == original
    assert len(list((root/'source').glob('示例*.md'))) == 2
    assert any(p.read_bytes() == newer for p in (root/'source').glob('*.md'))
    print('PASS: a changed original creates another saved source version without replacing the first')

    # A missing temporary upload can use its saved copy, but a corrupted saved copy cannot.
    source.unlink()
    state = json.loads((root/'state.json').read_text())
    Path(state['source']['saved_path']).write_text('損壞的來源')
    error, code = call('--output', root, '--task', 'reclean_text')
    assert code == 1 and 'modified' in error['error']

    fenced = project/'fenced.md'
    fenced.write_text('# 示例\n\n## 正文\n\n文字。\n\n```markdown\n## 假章節\n```\n')
    result, _ = call(fenced, '--project-root', project, status='needs_chapter_confirmation')
    assert '- 假章節' not in Path(result['outline']).read_text()
    assert '## 假章節' in Path(result['cleaned_text']).read_text()
    low_source = project/'low.txt'
    low_source.write_text('沒有章節標題。\n\n另一段。\n')
    low, _ = call(low_source, '--project-root', project, status='needs_chapter_confirmation')
    assert low['structure_confidence'] == 'low' and Path(low['outline']).exists()
    rejected, code = approve(Path(low['output']), low['review_token'])
    assert code == 2
    low_work = Path(low['cleaned_text'])
    low_work.write_text('# 全書\n\n## 正文\n\n' + low_work.read_text())
    low, _ = call('--output', low['output'], '--task', 'review_chapters', status='needs_chapter_confirmation')
    assert approve(Path(low['output']), low['review_token'])[1] == 0
    print('PASS: code examples do not become chapters; low-confidence text needs heading repair before confirmation')

    medium = project/'medium.txt'
    medium.write_text('卷上\n\n上卷正文。\n\n卷下\n\n下卷正文。\n')
    result, code = call(medium, '--project-root', project, status='needs_chapter_confirmation')
    assert code == 2 and result['structure_confidence'] == 'medium'
    assert approve(Path(result['output']), result['review_token'])[1] == 0

    multi = project/'multi.md'
    multi.write_text('# 文件一\n\n第一篇正文。\n\n# 文件二\n\n第二篇正文。\n')
    value, _ = call(multi, '--project-root', project, status='needs_chapter_confirmation')
    assert approve(Path(value['output']), value['review_token'])[1] == 0

    # Legacy work files remain authoritative, and discovery does not create a duplicate book.
    legacy = project/'textoria-digital-library/collections/legacy'
    legacy.mkdir(parents=True)
    (legacy/'clean').mkdir()
    (legacy/'clean/cleaned_text.md').write_bytes(original)
    (legacy/'config').mkdir()
    legacy_source = project/'legacy.md'; legacy_source.write_bytes(original)
    (legacy/'config/textoria.json').write_text(json.dumps({'source_file': str(legacy_source), 'collection_name':'舊書','collection_slug':'legacy'}))
    # An untracked legacy working text is adopted without recleaning it.
    from textoria_utf8_converter import inspect_input
    facts = inspect_input(legacy_source)
    (legacy/'state.json').write_text(json.dumps({'source': facts,'stages': {}}))
    (project/'textoria-digital-library/registry.json').write_text(json.dumps({'collections':[{'collection_id':'legacy','slug':'legacy','path':'textoria-digital-library/collections/legacy','source_files':['legacy.md']}]}))
    result, code = call(legacy_source,'--project-root',project,status='needs_chapter_confirmation')
    assert result['output'] == str(legacy)
    assert Path(result['cleaned_text']) == legacy/'clean/cleaned_text.md'
    assert not (legacy/'content/全文.md').exists()
    assert not (project/'textoria-text2ebook/collections/legacy').exists()
    adopted = json.loads((legacy/'state.json').read_text())['stages']['clean_text']
    assert adopted['adopted_working_text']
    legacy_source.write_text('# 不同來源\n\n不同正文。\n')
    error, code = call('--output', legacy, '--task', 'review_chapters')
    assert code == 1 and (legacy/'clean/cleaned_text.md').read_bytes() == original
    print('PASS: multi-document linkage and legacy work paths/registry are preserved')
