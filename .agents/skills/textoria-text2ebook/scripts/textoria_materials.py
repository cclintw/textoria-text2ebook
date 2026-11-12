#!/usr/bin/env python3
"""Receive optional ebook assets and preserve explicit selection/skip decisions."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

from textoria_common import now_iso, read_json, write_json
from textoria_utf8_converter import detect_encoding

LABELS = {'cover': '封面', 'titlepage': '書名頁', 'copyright': '版權頁'}
PROMPT = ('請上傳以下素材，以便生成 EPUB 電子書使用；也可以提供本機檔案路徑。\n'
          '封面：封面.jpg／封面.jpeg／封面.png，RGB，建議 1600 × 2400 px。\n'
          '書名頁：書名頁.txt 或 書名頁.md。\n'
          '版權頁：版權頁.txt 或 版權頁.md。\n'
          '以上皆為選用，未提供的項目就不加入，不自動生成或補寫。'
          '上傳完成後請回覆「素材已提供」；若不加入任何素材，請回覆「略過素材」。')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def classify(path: Path) -> str:
    for kind, label in LABELS.items():
        if path.stem == label:
            suffixes = ('.jpg', '.jpeg', '.png') if kind == 'cover' else ('.txt', '.md')
            if path.suffix.lower() in suffixes:
                return kind
    raise ValueError('素材檔名必須為封面.jpg／jpeg／png、書名頁.txt／md 或版權頁.txt／md：' + path.name)


def _png(raw: bytes) -> tuple[int, int, str]:
    offset = 8
    header = None
    payload = bytearray()
    ended = False
    while offset + 12 <= len(raw):
        size = struct.unpack('>I', raw[offset:offset+4])[0]
        kind = raw[offset+4:offset+8]
        end = offset + 12 + size
        if end > len(raw): raise ValueError('PNG 圖片內容不完整。')
        body = raw[offset+8:end-4]
        if zlib.crc32(kind + body) & 0xffffffff != struct.unpack('>I',raw[end-4:end])[0]:
            raise ValueError('PNG 圖片校驗失敗。')
        if header is None and kind != b'IHDR': raise ValueError('PNG 缺少起始 IHDR。')
        if kind == b'IHDR':
            if header is not None or size != 13: raise ValueError('PNG IHDR 不正確。')
            header = struct.unpack('>IIBBBBB', body)
        if kind == b'IDAT': payload.extend(body)
        if kind == b'IEND':
            if size or end != len(raw): raise ValueError('PNG 結尾不正確。')
            ended = True
            break
        offset = end
    if not header or not ended or not payload: raise ValueError('PNG 缺少必要內容。')
    width, height, depth, color, compression, filtering, interlace = header
    if not width or not height or width * height > 40_000_000:
        raise ValueError('封面像素尺寸無效或過大。')
    if color not in (2, 6): raise ValueError('封面須使用 RGB 圖片，請先轉存為 RGB PNG 或 JPEG。')
    if depth not in (8,16) or compression or filtering or interlace not in (0,1):
        raise ValueError('PNG 編碼不正確。')
    channels = 3 if color == 2 else 4
    passes = [(0,0,1,1)] if not interlace else [(0,0,8,8),(4,0,8,8),(0,4,4,8),(2,0,4,4),(0,2,2,4),(1,0,2,2),(0,1,1,2)]
    scanlines = []
    for x,y,dx,dy in passes:
        w, h = max(0,(width-x+dx-1)//dx), max(0,(height-y+dy-1)//dy)
        if w and h: scanlines.append((h, (w*channels*depth+7)//8))
    expected = sum(h * (n+1) for h,n in scanlines)
    if expected > 64*1024*1024: raise ValueError('封面解碼資料過大，請先縮小圖片。')
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(bytes(payload), expected+1)
    except zlib.error as exc:
        raise ValueError('PNG 像素資料無法解碼。') from exc
    if len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('PNG 像素資料長度不正確。')
    position = 0
    for count, row_bytes in scanlines:
        for _ in range(count):
            if pixels[position] > 4: raise ValueError('PNG 列過濾器無效。')
            position += row_bytes+1
    return width, height, 'RGB' if color == 2 else 'RGBA'


def _jpeg(raw: bytes) -> tuple[int,int,str]:
    if not raw.endswith(b'\xff\xd9'): raise ValueError('JPEG 圖片內容不完整。')
    pos = 2
    while pos < len(raw)-2:
        if raw[pos] != 255: raise ValueError('JPEG 標記不正確。')
        while pos < len(raw) and raw[pos] == 255: pos += 1
        marker = raw[pos]; pos += 1
        if marker in (0xd8,0xd9) or 0xd0 <= marker <= 0xd7: continue
        if pos+2 > len(raw): break
        size = int.from_bytes(raw[pos:pos+2], 'big')
        if size < 2 or pos+size > len(raw): break
        if marker in (0xc0,0xc1,0xc2):
            body = raw[pos+2:pos+size]
            if len(body) < 6: break
            height, width, components = int.from_bytes(body[1:3],'big'), int.from_bytes(body[3:5],'big'), body[5]
            if not width or not height or width*height > 40_000_000: raise ValueError('封面像素尺寸無效或過大。')
            if components != 3: raise ValueError('封面須使用 RGB 圖片，請先轉存為 RGB JPEG。')
            if len(body) != 6 + 3*components: break
            return width, height, 'RGB-compatible JPEG'
        if marker == 0xda: break
        pos += size
    raise ValueError('JPEG 缺少可辨識的尺寸與色彩標記。')


def _cover(raw: bytes, path: Path) -> dict:
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        actual = 'png'; width,height,color = _png(raw)
        verification = 'PNG container CRC, decoded scanline size and filters'
    elif raw.startswith(b'\xff\xd8'):
        actual = 'jpeg'; width,height,color = _jpeg(raw)
        verification = 'JPEG container and frame header; pixels not fully decoded'
    else: raise ValueError('封面內容不是 JPEG 或 PNG。')
    if (path.suffix.lower() == '.png') != (actual == 'png'):
        raise ValueError('封面副檔名與實際圖片格式不一致。')
    native = shutil.which('sips')
    if native:
        try:
            result = subprocess.run([native,'-g','format','-g','pixelWidth','-g','pixelHeight','-g','space',str(path)],capture_output=True,text=True,timeout=15)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise ValueError('系統圖片資訊檢查無法完成。') from exc
        fields = {}
        for line in result.stdout.splitlines():
            key, separator, value = line.strip().partition(': ')
            if separator: fields[key] = value
        if result.returncode or fields.get('format') != actual or fields.get('pixelWidth') != str(width) or fields.get('pixelHeight') != str(height):
            raise ValueError('系統無法讀取一致的封面圖片資訊。')
        if fields.get('space') not in ('RGB','rgb'): raise ValueError('封面須使用 RGB 色彩模式。')
        verification += '; native image format/dimensions/colorspace checked'
    notes = []
    if min(width,height) < 1400: notes.append('短邊小於 1400 px；保留原圖，不自動放大。')
    if width*height > 5_600_000: notes.append('超過 Apple Books 內嵌圖片參考像素上限；不宣稱符合其上架要求。')
    return {'format':actual,'width':width,'height':height,'color_mode':color,'verification':verification,
            'recommended_size':[1600,2400],'notes':notes}


def inspect_material(kind: str, path: Path, raw: bytes | None = None) -> tuple[dict,str | None]:
    raw = path.read_bytes() if raw is None else raw
    if not raw or len(raw) > 32*1024*1024: raise ValueError('素材為空或超過 32 MB。')
    if kind == 'cover': return _cover(raw,path), None
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else detect_encoding(raw)[0]
    try: text = raw.decode(encoding).lstrip('\ufeff')
    except (UnicodeError, LookupError) as exc: raise ValueError('素材文字編碼無法可靠讀取。') from exc
    if not text.strip() or '\x00' in text or '\ufffd' in text or re.search(r'[\x01-\x08\x0b\x0c\x0e-\x1f]',text):
        raise ValueError('書名頁／版權頁須為可讀取的非空文字檔。')
    return {'format':path.suffix.lower().lstrip('.'),'encoding':encoding,'characters':len(text),
            'verification':'decoded text; original bytes preserved'}, text


def conflicts(kind: str, text: str | None, metadata: dict) -> list[dict]:
    if text is None: return []
    fields = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if fence:
            if marker and marker[1][0]==fence[0] and len(marker[1])>=fence[1] and not marker[2].strip(): fence=None
            continue
        if marker:
            fence=(marker[1][0],len(marker[1])); continue
        match = re.fullmatch(r'\s*(書名|作者|編者|校註者|校訂者)\s*[：:]\s*(.*?)\s*',line)
        if match: fields.append((match[1],match[2]))
        elif kind == 'titlepage':
            heading = re.fullmatch(r'#\s+(.+?)\s*',line)
            if heading and heading[1] != '書名頁': fields.append(('書名',heading[1]))
    result=[]
    for field,value in fields:
        if field=='書名': expected=metadata['title']; different=value.strip()!=expected
        else:
            expected=[p['name'] for p in metadata['creators']+metadata['contributors'] if p['role']==field]
            different=set(x.strip() for x in re.split('[、;；]',value) if x.strip())!=set(expected)
        if different: result.append({'kind':kind,'field':field,'metadata_value':expected,'material_value':value})
    return result


def _save(root: Path, source: Path, raw: bytes) -> Path:
    target=root/'materials'/source.name
    if target.exists() and digest(target.read_bytes())!=digest(raw): target=target.with_name(f'{target.stem}-{digest(raw)[:12]}{target.suffix}')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=raw: raise ValueError('素材保存檔名衝突，未覆寫原檔。')
    else:
        with target.open('xb') as stream: stream.write(raw)
    return target


def process_materials(root: Path, metadata: dict, *, sources: list[Path] | None = None,
                      replacements: list[str] | None = None, token: str | None = None,
                      skip: bool = False, accept_conflicts: bool = False) -> dict:
    state_path=root/'state.json'; state=read_json(state_path)
    meta=state.get('reviews',{}).get('metadata',{})
    if meta.get('status')!='confirmed': raise ValueError('Metadata confirmation is required before receiving materials')
    previous=state.get('reviews',{}).get('materials',{})
    files=dict(previous.get('files',{})); history=list(previous.get('history',[]))
    pending={}
    for source in sources or []:
        kind=classify(source)
        if kind in pending: raise ValueError('同一素材有多個候選檔案，請先選定：'+LABELS[kind])
        raw=source.read_bytes(); info,text=inspect_material(kind,source,raw)
        if kind in files and files[kind]['sha256']!=digest(raw) and kind not in (replacements or []):
            raise ValueError('更換既有'+LABELS[kind]+'須明確指定 --replace-material '+kind+'；舊副本會保留。')
        pending[kind]=(source,raw,info,text)
    if set(replacements or []) - set(pending):
        raise ValueError('更換參數須對應本次提供的素材。')
    if token and (sources or skip): raise ValueError('先接收素材，再確認目前版本，不可在確認指令同時修改。')
    # Validate every new item before writing any copy.
    for kind,(source,raw,info,text) in pending.items():
        if source.read_bytes()!=raw: raise ValueError('素材於檢查後已變更，請重新接收。')
        saved=_save(root,source,raw)
        record={'name':source.name,'original_path':str(source.resolve()),'relative_path':str(saved.relative_to(root)),
                'sha256':digest(raw),'inspection':info}
        if kind in files and files[kind] != record and files[kind] not in history: history.append(files[kind])
        files[kind]=record
    invalid=[]; differences=[]
    for kind,item in files.items():
        path=(root/item['relative_path']).resolve()
        if not path.is_relative_to((root/'materials').resolve()): raise ValueError('素材保存路徑超出 materials 目錄。')
        if not path.is_file() or digest(path.read_bytes())!=item['sha256']:
            invalid.append({'kind':kind,'message':'保存的素材遺失或內容已變更；請恢復原檔或明確更換。'})
            continue
        info,text=inspect_material(kind,path)
        item['inspection']=info
        differences.extend(conflicts(kind,text,metadata))
    payload=[meta['input_hash'],[[kind,files[kind]['relative_path'],files[kind]['sha256']] for kind in sorted(files)]]
    review_token=digest(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode())
    current=(previous.get('status') in ('confirmed','skipped') and previous.get('review_token')==review_token and not invalid)
    conflict_approval=(previous.get('conflicts_acknowledged')==review_token)
    accepted=bool(token and token==review_token and token==previous.get('review_token') and not invalid)
    error=None
    if token and not files and not current:
        accepted=False
        error='尚未收到素材；若不加入任何素材，請明確回覆略過素材。'
    if token and not accepted and error is None: error='素材版本已變更或尚未呈現，請先檢查目前檔案再確認。'
    if differences and not (conflict_approval or (accepted and accept_conflicts)):
        current=False; accepted=False
        error='素材中的書名或署名與已確認 metadata 不同，請先決定修正哪一份，或明確保留兩者差異。'
    ready=(current or accepted or skip) and not invalid and not error
    record={'status':('confirmed' if files else 'skipped') if ready else 'pending','files':files,'history':history,
            'review_token':review_token,'metadata_hash':meta['input_hash'],'conflicts':differences,'invalid':invalid,
            'skipped':[kind for kind in LABELS if kind not in files] if ready else [],'updated_at':now_iso()}
    if differences and (conflict_approval or (accepted and accept_conflicts)): record['conflicts_acknowledged']=review_token
    if ready: record['confirmed_at']=previous.get('confirmed_at',now_iso()) if current else now_iso()
    state.setdefault('reviews',{})['materials']=record; state['updated_at']=now_iso(); write_json(state_path,state)
    status='materials_confirmed' if ready else ('needs_material_conflict_confirmation' if differences and not conflict_approval and not invalid else 'needs_materials')
    return {'ok':bool(ready),'status':status,'output':str(root.resolve()),'materials_token':review_token,
            'files':files,'missing':[kind for kind in LABELS if kind not in files], 'conflicts':differences,'invalid':invalid,
            'links':{LABELS[kind]:str((root/item['relative_path']).resolve()) for kind,item in files.items() if (root/item['relative_path']).is_file()},
            'message':error or ('素材選擇已保存；未提供的項目省略。' if ready else
                ('保存素材有問題：'+'；'.join(LABELS[item['kind']]+'：'+item['message'] for item in invalid) if invalid else PROMPT)),
            'next_step':'generate' if ready else 'review_materials'}
