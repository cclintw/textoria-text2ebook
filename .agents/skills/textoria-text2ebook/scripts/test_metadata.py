#!/usr/bin/env python3
"""Verify metadata review ordering, edits, imports and canonical projection."""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SCRIPT = Path(__file__).with_name('textoria_build.py')


def run(*args, status=None, code=None):
    result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    value = json.loads(result.stdout)
    if status: assert value.get('status') == status, (result.stdout, result.stderr)
    if code is not None: assert result.returncode == code, (result.stdout, result.stderr)
    return value


def confirm(root, value):
    return run('--output', root, '--task', 'confirm_metadata', '--metadata-token', value['metadata_token'],
               status='metadata_confirmed', code=0)


def workbook(path, sheets, formula=False):
    # Minimal synthetic OOXML fixture with real worksheet relationships and shared strings.
    values = []
    payloads = []
    for number, (name, rows) in enumerate(sheets, start=1):
        lines = []
        for r, row in enumerate(rows, start=1):
            cells = []
            for c, value in enumerate(row):
                values.append(value)
                cells.append(f'<c r="{chr(65+c)}{r}" t="s">'+('<f>1+1</f>' if formula else '')+f'<v>{len(values)-1}</v></c>')
            lines.append(f'<row r="{r}">'+''.join(cells)+'</row>')
        payloads.append(''.join(lines))
    with zipfile.ZipFile(path, 'w') as out:
        out.writestr('xl/sharedStrings.xml','<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'+''.join('<si><t>'+escape(v)+'</t></si>' for v in values)+'</sst>')
        out.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'+''.join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(sheets,start=1))+'</sheets></workbook>')
        out.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1))+'</Relationships>')
        for i,payload in enumerate(payloads,start=1):
            out.writestr(f'xl/worksheets/sheet{i}.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+payload+'</sheetData></worksheet>')


with tempfile.TemporaryDirectory(prefix='text2ebook-metadata-') as directory:
    project = Path(directory).resolve()
    source = project/'示例.md'
    source.write_text('# 示例古籍\n\n作者：王甲\n\n校訂者：李乙\n\n## 序\n\n序言作者：陳丙\n\n## 卷一\n\n正文。\n')
    chapters = run(source,'--project-root',project,'--task','review_metadata',status='needs_chapter_confirmation',code=2)
    root = Path(chapters['output'])
    assert not (root/'metadata.json').exists()
    run('--output',root,'--task','confirm_chapters','--review-token',chapters['review_token'],status='chapters_confirmed',code=0)
    suggested = run('--output',root,'--task','build_sqlite',status='needs_metadata_confirmation',code=2)
    value = suggested['metadata']
    assert value['title'] == '示例古籍'
    assert value['creators'] == [{'name':'王甲','role':'作者'}]
    assert value['contributors'] == [{'name':'李乙','role':'校訂者'}]
    assert not value['extra'] and '陳丙' not in json.dumps(value,ensure_ascii=False)
    assert all(term not in suggested['message'] for term in ['ISBN','封面','版權頁','書名頁'])
    assert not (root/'sqlite').exists()
    run('--output',root,'--task','confirm_metadata',status='needs_metadata_confirmation',code=2)
    print('PASS: chapters precede metadata; explicit signatures are distinguished from preface authors; database builds wait')

    archive = root/'intermediate/archive.json'
    before = archive.read_bytes()
    edited = run('--output',root,'--task','edit_metadata','--metadata-patch',json.dumps({'書名':'修訂書名','編者':'趙丁'},ensure_ascii=False), '--metadata-delete','校訂者',status='needs_metadata_confirmation',code=2)
    assert archive.read_bytes() == before
    assert edited['metadata']['contributors'] == []
    stale = run('--output',root,'--task','confirm_metadata','--metadata-token',suggested['metadata_token'],status='needs_metadata_confirmation',code=2)
    accepted = confirm(root,stale)
    assert accepted['next_step'] == 'materials' and not (root/'materials').exists()
    canonical = json.loads(archive.read_text())
    assert canonical['collections'][0]['title'] == '修訂書名'
    assert canonical['documents'][0]['creator'] == '王甲、趙丁'
    assert json.loads(canonical['documents'][0]['metadata_json'])['book_metadata']['contributors'] == []
    state = json.loads((root/'state.json').read_text())
    assert '校訂者' in state['reviews']['metadata']['removed_fields']
    # Metadata title edits must not reopen the already approved document/chapter heading review.
    run('--output',root,'--task','review_chapters',status='chapters_confirmed',code=0)
    again = run('--output',root,'--task','review_metadata',status='metadata_confirmed',code=0)
    assert again['metadata'] == edited['metadata']
    run('--output',root,'--task','build_sqlite',status='needs_materials',code=2)
    run('--output',root,'--task','skip_materials',status='materials_confirmed',code=0)
    run('--output',root,'--task','build_sqlite',code=0)
    print('PASS: dialogue changes/deletions persist; stale tokens fail; approved book titles update canonical data without reopening chapter review')

    path = root/'metadata.json'
    raw = json.loads(path.read_text()); raw['title'] = '直接修正'
    path.write_text(json.dumps(raw,ensure_ascii=False))
    altered = run('--output',root,'--task','confirm_metadata','--metadata-token',again['metadata_token'],status='needs_metadata_confirmation',code=2)
    confirm(root,altered)
    assert json.loads(archive.read_text())['collections'][0]['title'] == '直接修正'
    raw = json.loads(path.read_text()); raw['creators'] = []
    path.write_text(json.dumps(raw,ensure_ascii=False))
    removed = run('--output',root,'--task','review_metadata',status='needs_metadata_confirmation',code=2)
    confirm(root,removed)
    assert {'作者','編者','creators'} <= set(json.loads((root/'state.json').read_text())['reviews']['metadata']['removed_fields'])
    original_metadata = path.read_bytes()
    run('--output',root,'--task','edit_metadata','--metadata-delete','書名',code=1)
    assert path.read_bytes() == original_metadata
    print('PASS: direct JSON edits require renewed approval and required titles cannot be deleted')

    csvfile = project/'書目.csv'
    csvfile.write_text('欄位,內容\n書名,CSV書名\n作者,陳甲、陳乙\n校註者,丁丙\n',encoding='utf-8-sig')
    imported = run('--output',root,'--task','edit_metadata','--metadata-file',csvfile,status='needs_metadata_confirmation',code=2)
    saved = root/'source/metadata/書目.csv'
    assert saved.read_bytes() == csvfile.read_bytes()
    assert [p['name'] for p in imported['metadata']['creators'] if p['role']=='作者'] == ['陳甲','陳乙']
    csvfile.write_text('書名,作者\n第二版本,新作者\n')
    imported = run('--output',root,'--task','edit_metadata','--metadata-file',csvfile,status='needs_metadata_confirmation',code=2)
    assert len(list((root/'source/metadata').glob('書目*.csv'))) == 2
    assert saved.read_text(encoding='utf-8-sig').startswith('欄位,內容')
    confirm(root,imported)
    ambiguous = project/'多筆.csv'; ambiguous.write_text('書名,作者\n甲書,甲\n乙書,乙\n')
    before = path.read_bytes()
    run('--output',root,'--task','edit_metadata','--metadata-file',ambiguous,code=1)
    assert path.read_bytes() == before and not (root/'source/metadata/多筆.csv').exists()
    duplicate = project/'重複.json'; duplicate.write_text('{"title":"甲","title":"乙"}')
    run('--output',root,'--task','edit_metadata','--metadata-file',duplicate,code=1)
    assert path.read_bytes() == before
    print('PASS: CSV role imports preserve uploaded originals/version history; ambiguous tables and duplicate JSON keys are rejected without overwriting')

    book = project/'metadata.xlsx'
    workbook(book,[('書目',[['欄位','內容'],['書名','Excel書名'],['作者','Excel作者']])])
    excel = run('--output',root,'--task','edit_metadata','--metadata-file',book,status='needs_metadata_confirmation',code=2)
    assert excel['metadata']['title'] == 'Excel書名'
    assert (root/'source/metadata/metadata.xlsx').read_bytes() == book.read_bytes()
    workbook(book,[('甲',[['書名','作者'],['甲書','甲人']]),('乙',[['書名','作者'],['乙書','乙人']])])
    before = path.read_bytes()
    run('--output',root,'--task','edit_metadata','--metadata-file',book,code=1)
    assert path.read_bytes() == before
    selected = run('--output',root,'--task','edit_metadata','--metadata-file',book,'--metadata-sheet','乙',status='needs_metadata_confirmation',code=2)
    assert selected['metadata']['title'] == '乙書'
    workbook(book,[('公式',[['書名','作者'],['甲書','甲人']])],formula=True)
    run('--output',root,'--task','edit_metadata','--metadata-file',book,code=1)
    print('PASS: XLSX shared strings, worksheet selection and formula rejection work without new dependencies')

    text = project/'書籍資料.md'; text.write_text('書名：文字書名\n作者：文字作者\n校訂者：文字校訂\n')
    text_value = run('--output',root,'--task','edit_metadata','--metadata-file',text,status='needs_metadata_confirmation',code=2)
    assert text_value['metadata']['title'] == '文字書名'
    full = project/'書籍資料.json'
    full.write_text(json.dumps({'title':'結構化書名','creators':[{'name':'結構作者','role':'作者'}],'contributors':[],'extra':{'自訂欄位':'值'}},ensure_ascii=False))
    full_value = run('--output',root,'--task','edit_metadata','--metadata-file',full,status='needs_metadata_confirmation',code=2)
    confirm(root,full_value)
    stable = path.read_bytes()
    # The saved value wins over later source-level signature suggestions.
    work = root/'content/全文.md'; work.write_text(work.read_text().replace('作者：王甲','作者：原文改署名'))
    current = run('--output',root,'--task','review_metadata',status='metadata_confirmed',code=0)
    assert path.read_bytes() == stable and current['metadata']['contributors'] == []
    path.unlink()
    missing = run('--output',root,'--task','review_metadata',code=1)
    assert 'missing' in missing['error'] and not path.exists()
    print('PASS: labeled text and canonical JSON imports work; later source edits never refill deleted people; missing metadata is not replaced with guesses')
