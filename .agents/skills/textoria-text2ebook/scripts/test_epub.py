#!/usr/bin/env python3
"""Verify public EPUB gates, optional pages, identity, packaging and failed-build preservation."""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from textoria_validate_epub import validate_epub, XHTML
from textoria_build_epub import _markdown
probe=ET.Element('probe');_markdown(probe,'文字 & <字元>。')
assert '&amp;' in ET.tostring(probe,encoding='unicode') and '&lt;' in ET.tostring(probe,encoding='unicode')

SCRIPT=Path(__file__).with_name('textoria_build.py')

def run(*args,status=None):
    process=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
    value=json.loads(process.stdout)
    if status:assert value.get('status')==status,(value,process.stderr)
    return value

# Use real configured tools when available; never substitute a successful mock checker.
config=Path.cwd()/'.textoria-text2ebook/tools/epub-tools.json'
tools=json.loads(config.read_text()) if config.is_file() else {}
checker=['--epubcheck-jar',tools['epubcheck_jar'],'--java',tools['java'],'--require-epubcheck'] if tools else []
with tempfile.TemporaryDirectory(prefix='text2ebook-epub-') as folder:
    project=Path(folder).resolve();source=project/'正文.md'
    source.write_text('# 測試文獻（虛構）\n\n## 卷一\n\n文字 & <字元>。\n\n### 小節\n\n第二段。\n')
    review=run(source,'--project-root',project,'--task','build_epub',status='needs_chapter_confirmation');root=Path(review['output'])
    run('--output',root,'--task','confirm_chapters','--review-token',review['review_token'],status='chapters_confirmed')
    meta=run('--output',root,'--task','edit_metadata','--metadata-patch','{"作者":"示例作者","校訂者":"示例校訂者"}',status='needs_metadata_confirmation')
    run('--output',root,'--task','confirm_metadata','--metadata-token',meta['metadata_token'],status='metadata_confirmed')
    run('--output',root,'--task','build_epub',status='needs_materials')
    run('--output',root,'--task','skip_materials',status='materials_confirmed')
    def build(*extra):return run('--output',root,'--task','build_epub',*extra)
    result=build(*checker);assert result['ok'],result
    if tools:assert result['epub_validation']['compliance_verified'],result
    epub=Path(result['epub']);identity=result['identifier']
    assert not (root/'site').exists() and not (root/'sqlite').exists()
    assert result['epub_validation']['spine']==['Text/nav.xhtml','Text/Section0001.xhtml']
    with zipfile.ZipFile(epub) as book:
        first=book.infolist()[0];assert first.filename=='mimetype' and first.compress_type==0
        nav=ET.fromstring(book.read('OEBPS/Text/nav.xhtml'))
        assert len(nav.findall('.//{'+XHTML+'}ol'))>=2
        assert len(nav.findall('.//{'+XHTML+'}a'))>=2
        body=ET.fromstring(book.read('OEBPS/Text/Section0001.xhtml'))
        assert all(p['text'] in ''.join(body.itertext()) for p in json.loads((root/'intermediate/archive.json').read_text())['paragraphs'])
        assert not any('cover' in name or 'copyright' in name or 'titlepage' in name for name in book.namelist())
    print('PASS: confirmation gates, nested navigation, escaped text and omitted optional pages; EPUB-only leaves site/SQLite absent')

    import struct,zlib
    def chunk(kind,raw):return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
    cover=project/'封面.png';raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,48,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x80\x90\xa0'*32)*48))+chunk(b'IEND',b'');cover.write_bytes(raw)
    title=project/'書名頁.md';title.write_text('# '+json.loads((root/'metadata.json').read_text())['title']+'\n\n作者：示例作者\n')
    copyright=project/'版權頁.txt';copyright.write_text('版本：測試版本（虛構）\n\n保留原有文字。\n')
    assets=run('--output',root,'--task','receive_materials','--material',cover,'--material',title,'--material',copyright,status='needs_materials')
    run('--output',root,'--task','confirm_materials','--materials-token',assets['materials_token'],status='materials_confirmed')
    result=build(*checker);assert result['ok'],result
    assert result['identifier']==identity
    assert result['epub_validation']['spine']==['Text/cover.xhtml','Text/titlepage.xhtml','Text/copyright.xhtml','Text/nav.xhtml','Text/Section0001.xhtml']
    with zipfile.ZipFile(result['epub']) as book:
        assert book.read('OEBPS/Images/cover.png')==raw
    assert cover.read_bytes()==raw and (root/'materials/書名頁.md').read_bytes()==title.read_bytes()
    epub=Path(result['epub']);before=epub.read_bytes()
    failed=build('--epubcheck-jar',project/'missing.jar','--require-epubcheck')
    assert not failed['ok'] and 'epub' not in failed and epub.read_bytes()==before,failed
    print('PASS: supplied pages in reading order, exact cover bytes, persistent identifier; failed required validation preserves existing EPUB')

    # Corrupt an internal navigation target while retaining an otherwise valid ZIP.
    broken=project/'broken.epub'
    with zipfile.ZipFile(epub) as original,zipfile.ZipFile(broken,'w') as output:
        for item in original.infolist():
            content=original.read(item.filename)
            if item.filename=='OEBPS/Text/nav.xhtml':content=content.replace(b'Section0001.xhtml',b'absent.xhtml')
            output.writestr(item,content)
    checked=validate_epub(broken,project_root=project)
    assert not checked['ok'] and checked['internal']['status']=='failed',checked
    meta=run('--output',root,'--task','edit_metadata','--metadata-patch','{"書名":"更名測試文獻（虛構）"}',status='needs_metadata_confirmation')
    run('--output',root,'--task','confirm_metadata','--metadata-token',meta['metadata_token'],status='metadata_confirmed')
    review=run('--output',root,'--task','review_materials',status='needs_material_conflict_confirmation')
    run('--output',root,'--task','confirm_materials','--materials-token',review['materials_token'],'--accept-material-conflicts',status='materials_confirmed')
    renamed=build(*checker);assert renamed['ok'] and renamed['identifier']==identity,renamed
    assert Path(renamed['epub'])!=epub and epub.read_bytes()==before
    print('PASS: broken navigation rejected; metadata rename keeps identifier and earlier named output')
    import shutil
    if shutil.which('sips'):
        jpeg=project/'封面.jpg'
        conversion=subprocess.run(['sips','-s','format','jpeg',str(cover),'--out',str(jpeg)],capture_output=True)
        assert conversion.returncode==0
        review=run('--output',root,'--task','receive_materials','--material',jpeg,'--replace-material','cover',status='needs_material_conflict_confirmation')
        run('--output',root,'--task','confirm_materials','--materials-token',review['materials_token'],'--accept-material-conflicts',status='materials_confirmed')
        jpg_result=build(*checker);assert jpg_result['ok'],jpg_result
        with zipfile.ZipFile(jpg_result['epub']) as book:
            assert book.read('OEBPS/Images/cover.jpg')==jpeg.read_bytes()
            assert b'image/jpeg' in book.read('OEBPS/content.opf')
        print('PASS: synthetic JPEG cover retains exact bytes and correct manifest MIME')
    print('Validation scope: '+('real EPUBCheck '+renamed['epub_validation']['epubcheck']['checker']['checkerVersion'] if tools else 'internal checks; EPUBCheck not configured'))
