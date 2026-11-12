#!/usr/bin/env python3
"""Verify optional material selection, checks, version retention and build gates."""
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

SCRIPT = Path(__file__).with_name('textoria_build.py')


def run(*args, status=None, code=None):
    result=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
    data=json.loads(result.stdout)
    if status: assert data.get('status')==status,(result.stdout,result.stderr)
    if code is not None: assert result.returncode==code,(result.stdout,result.stderr)
    return data


def png(path, width=1600, height=2400, color=2, rgb=b'\xc8\xc8\xc8'):
    def chunk(kind,body): return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    pixels=(b'\x00'+(rgb if color==2 else b'\x80')*width)*height
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,color,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
    path.write_bytes(raw)
    return raw


def approve(root,review,*extra):
    return run('--output',root,'--task','confirm_materials','--materials-token',review['materials_token'],*extra,status='materials_confirmed',code=0)


with tempfile.TemporaryDirectory(prefix='text2ebook-materials-') as folder:
    project=Path(folder).resolve(); source=project/'正文.md'
    source.write_text('# 示例古籍\n\n作者：王甲\n\n## 卷上\n\n正文。\n')
    chapter=run(source,'--project-root',project,'--task','review_materials',status='needs_chapter_confirmation',code=2)
    root=Path(chapter['output'])
    assert not (root/'materials').exists()
    run('--output',root,'--task','confirm_chapters','--review-token',chapter['review_token'],code=0)
    meta=run('--output',root,'--task','review_materials',status='needs_metadata_confirmation',code=2)
    run('--output',root,'--task','confirm_metadata','--metadata-token',meta['metadata_token'],code=0)
    review=run('--output',root,'--task','build_sqlite',status='needs_materials',code=2)
    assert review['message'].startswith('請上傳以下素材，以便生成 EPUB 電子書使用')
    assert set(review['missing'])=={'cover','titlepage','copyright'}
    assert not (root/'materials').exists() and not (root/'sqlite').exists()
    run('--output',root,'--task','confirm_materials','--materials-token',review['materials_token'],status='needs_materials',code=2)
    skipped=run('--output',root,'--task','skip_materials',status='materials_confirmed',code=0)
    assert json.loads((root/'state.json').read_text())['reviews']['materials']['status']=='skipped'
    assert not (root/'materials').exists()
    run('--output',root,'--task','build_sqlite',code=0)
    print('PASS: materials follow chapter/metadata approval; missing assets require a decision; explicit skip creates no empty pages/directories')

    incoming=project/'incoming'; incoming.mkdir()
    cover=incoming/'封面.png'; original=png(cover)
    title=incoming/'書名頁.md'; title.write_text('# 示例古籍\n\n作者：王甲\n',encoding='utf-8-sig')
    copyright=incoming/'版權頁.txt'; copyright.write_bytes('版權頁\r\n版本：示例版本\r\n'.encode('big5'))
    assets=run('--output',root,'--task','receive_materials','--material',cover,'--material',title,'--material',copyright,status='needs_materials',code=2)
    assert set(assets['files'])=={'cover','titlepage','copyright'}
    assert assets['files']['cover']['inspection']['width']==1600
    assert assets['files']['cover']['inspection']['height']==2400
    assert (root/'materials/封面.png').read_bytes()==original
    assert (root/'materials/書名頁.md').read_bytes()==title.read_bytes()
    assert (root/'materials/版權頁.txt').read_bytes()==copyright.read_bytes()
    assert not assets['conflicts']
    approved=approve(root,assets)
    assert approved['next_step']=='generate' and not (root/'site').exists() and not (root/'export').exists()
    for p in incoming.iterdir():p.unlink()
    existing=run('--output',root,'--task','review_materials',status='materials_confirmed',code=0)
    kept=run('--output',root,'--task','skip_materials',status='materials_confirmed',code=0)
    assert kept['files']==existing['files']
    print('PASS: RGB cover and UTF-8/Big5 front matter are preserved byte-for-byte; confirmation stops before generation; later skip retains saved assets')

    cover=incoming/'封面.png'; newer=png(cover,rgb=b'\xb4\xaa\xa0')
    before=json.loads((root/'state.json').read_text())['reviews']['materials']
    run('--output',root,'--task','receive_materials','--material',cover,code=1)
    assert json.loads((root/'state.json').read_text())['reviews']['materials']==before
    assert (root/'materials/封面.png').read_bytes()==original
    replacement=run('--output',root,'--task','receive_materials','--material',cover,'--replace-material','cover',status='needs_materials',code=2)
    saved=root/replacement['files']['cover']['relative_path']
    assert saved.read_bytes()==newer and saved.name!='封面.png'
    assert (root/'materials/封面.png').read_bytes()==original
    assert json.loads((root/'state.json').read_text())['reviews']['materials']['history']
    run('--output',root,'--task','confirm_materials','--materials-token',approved['materials_token'],status='needs_materials',code=2)
    approve(root,replacement)
    print('PASS: replacement is explicit; older copies/history are retained and stale selection tokens fail')

    title=incoming/'書名頁.md'; title.write_text('# 不同書名\n\n作者：不同作者\n')
    original_meta=(root/'metadata.json').read_bytes()
    conflicting=run('--output',root,'--task','receive_materials','--material',title,'--replace-material','titlepage',status='needs_material_conflict_confirmation',code=2)
    assert len(conflicting['conflicts'])==2
    run('--output',root,'--task','confirm_materials','--materials-token',conflicting['materials_token'],status='needs_material_conflict_confirmation',code=2)
    run('--output',root,'--task','skip_materials',status='needs_material_conflict_confirmation',code=2)
    approve(root,conflicting,'--accept-material-conflicts')
    assert (root/'metadata.json').read_bytes()==original_meta
    assert '# 不同書名' in (root/conflicting['files']['titlepage']['relative_path']).read_text()
    print('PASS: front-matter identity conflicts require an explicit decision; neither metadata nor source text is rewritten')

    saved.write_bytes(b'corrupted')
    invalid=run('--output',root,'--task','build_sqlite',status='needs_materials',code=2)
    assert invalid['invalid'][0]['kind']=='cover'
    # Restore the exact saved file; the pending selection still needs explicit confirmation.
    saved.write_bytes(newer)
    restored=run('--output',root,'--task','review_materials',status='needs_materials',code=2)
    approve(root,restored,'--accept-material-conflicts')
    print('PASS: changed saved assets block downstream builds until restored and reviewed')

    # Invalid batches must not partially copy a valid cover.
    other_source=project/'other.md';other_source.write_text('# 另一本書\n\n## 正文\n\n文字。\n')
    c=run(other_source,'--project-root',project,'--task','review_chapters',code=2);other=Path(c['output'])
    run('--output',other,'--task','confirm_chapters','--review-token',c['review_token'],code=0)
    m=run('--output',other,'--task','review_metadata',code=2)
    run('--output',other,'--task','confirm_metadata','--metadata-token',m['metadata_token'],code=0)
    empty=incoming/'版權頁.txt';empty.write_bytes(b'')
    run('--output',other,'--task','receive_materials','--material',cover,'--material',empty,code=1)
    assert not (other/'materials').exists()
    wrong=incoming/'自訂封面.png';wrong.write_bytes(original)
    run('--output',other,'--task','receive_materials','--material',wrong,code=1)
    wrong_type=incoming/'封面.jpg';wrong_type.write_bytes(original)
    run('--output',other,'--task','receive_materials','--material',wrong_type,code=1)
    gray=incoming/'封面.png';png(gray,10,10,color=0)
    run('--output',other,'--task','receive_materials','--material',gray,code=1)
    png(gray,10,10); damaged=bytearray(gray.read_bytes());damaged[32]^=1;gray.write_bytes(damaged)
    run('--output',other,'--task','receive_materials','--material',gray,code=1)
    title.write_text('書名：另一本書\n')
    duplicate=incoming/'書名頁.txt';duplicate.write_text('書名：另一本書\n')
    run('--output',other,'--task','receive_materials','--material',title,'--material',duplicate,code=1)
    assert not (other/'materials').exists()
    print('PASS: invalid names, empty text, disguised/corrupt/non-RGB images and duplicate roles are rejected without partial saving')

    if shutil.which('sips'):
        # A synthetic test-image conversion verifies JPEG support without modifying user media.
        png(gray,32,48)
        jpeg=incoming/'封面.jpeg'
        result=subprocess.run(['sips','-s','format','jpeg',str(gray),'--out',str(jpeg)],capture_output=True)
        assert result.returncode==0
        value=run('--output',other,'--task','receive_materials','--material',jpeg,status='needs_materials',code=2)
        assert value['files']['cover']['inspection']['format']=='jpeg'
        assert value['files']['cover']['inspection']['width']==32
        assert value['files']['cover']['inspection']['notes']
        approve(other,value)
        assert not (other/'materials/書名頁.txt').exists() and not (other/'materials/版權頁.txt').exists()
        print('PASS: JPEG dimensions/colorspace and nonmandatory size recommendations are handled; omitted front matter stays absent')
