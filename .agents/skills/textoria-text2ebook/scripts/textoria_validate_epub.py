#!/usr/bin/env python3
"""Check generated EPUB package invariants and optionally run official EPUBCheck."""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

OPF='http://www.idpf.org/2007/opf'
DC='http://purl.org/dc/elements/1.1/'
XHTML='http://www.w3.org/1999/xhtml'
EPUB='http://www.idpf.org/2007/ops'
OCF='urn:oasis:names:tc:opendocument:xmlns:container'


def checker_command(project_root: Path, jar: Path | None = None, java: Path | None = None) -> list[str] | None:
    explicit = jar is not None or java is not None
    jar_value = jar or (Path(os.environ['TEXTORIA_EPUBCHECK_JAR']) if os.environ.get('TEXTORIA_EPUBCHECK_JAR') else None)
    java_value = java or (Path(os.environ['TEXTORIA_JAVA']) if os.environ.get('TEXTORIA_JAVA') else None)
    for namespace in ('.textoria-text2ebook','.textoria-digital-library'):
        config = project_root/namespace/'tools/epub-tools.json'
        if config.exists():
            tool=json.loads(config.read_text())
            jar_value=jar_value or Path(tool['epubcheck_jar'])
            java_value=java_value or Path(tool['java'])
    if jar_value:
        java_value=java_value or (Path(shutil.which('java')) if shutil.which('java') else None)
        if not jar_value.is_file() or java_value is None or not java_value.is_file():
            raise ValueError('EPUBCheck JAR or Java executable was not found')
        return [str(java_value),'-jar',str(jar_value)]
    command=shutil.which('epubcheck')
    if command: return [command]
    if explicit: raise ValueError('An EPUBCheck JAR is required when specifying Java')
    return None


def validate_epub(path: Path, *, project_root: Path | None = None, jar: Path | None = None,
                  java: Path | None = None, require_epubcheck: bool = False,
                  expected_spine: list[str] | None = None, paragraph_ids: list[str] | None = None) -> dict:
    errors=[]; warnings=[]; spine=[]; identifier=None; title=None; counts={}
    try:
        with zipfile.ZipFile(path) as archive:
            members=archive.infolist(); names=[i.filename for i in members]
            if not members or names[0]!='mimetype' or members[0].compress_type!=zipfile.ZIP_STORED or archive.read('mimetype')!=b'application/epub+zip':
                errors.append('mimetype must be the first uncompressed entry with its exact content')
            if len(set(names))!=len(names): errors.append('Duplicate ZIP entries')
            if any(n.startswith('/') or '..' in n.split('/') or '\\' in n for n in names): errors.append('Unsafe package path')
            if sum(i.file_size for i in members)>256*1024*1024: raise ValueError('EPUB package is too large for the internal checker')
            corrupted=archive.testzip()
            if corrupted: errors.append('ZIP CRC failed: '+corrupted)
            container=ET.fromstring(archive.read('META-INF/container.xml'))
            roots=container.findall(f'{{{OCF}}}rootfiles/{{{OCF}}}rootfile')
            if len(roots)!=1: raise ValueError('Expected one root package document')
            package_path=roots[0].attrib['full-path']; base=posixpath.dirname(package_path)
            package=ET.fromstring(archive.read(package_path))
            if package.tag!=f'{{{OPF}}}package' or package.get('version')!='3.0': errors.append('Expected EPUB 3 package document')
            metadata=package.find(f'{{{OPF}}}metadata')
            for name in ('title','language','identifier'):
                value=metadata.find(f'{{{DC}}}{name}') if metadata is not None else None
                if value is None or not (value.text or '').strip(): errors.append('Missing metadata: '+name)
                if name=='title' and value is not None: title=value.text
            unique=package.get('unique-identifier')
            ids=metadata.findall(f'{{{DC}}}identifier') if metadata is not None else []
            identifier=next((item.text for item in ids if item.get('id')==unique),None)
            if not identifier: errors.append('Unique identifier does not resolve')
            modified=metadata.find(f'{{{OPF}}}meta[@property="dcterms:modified"]') if metadata is not None else None
            if modified is None or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',modified.text or ''): errors.append('Missing UTC modification timestamp')
            manifest=package.find(f'{{{OPF}}}manifest'); items={}; by_path={}; navs=[]; covers=[]
            for item in manifest if manifest is not None else []:
                key=item.attrib['id']; href=item.attrib['href']; target=posixpath.normpath(posixpath.join(base,unquote(href)))
                if key in items or target in by_path: errors.append('Duplicate manifest identity or path')
                if target not in names: errors.append('Missing manifest resource: '+target)
                items[key]=item; by_path[target]=item
                if 'nav' in item.get('properties','').split(): navs.append(target)
                if 'cover-image' in item.get('properties','').split(): covers.append(target)
            if len(navs)!=1: errors.append('Exactly one EPUB navigation document is required')
            if len(covers)>1: errors.append('Multiple cover images declared')
            spine_element=package.find(f'{{{OPF}}}spine')
            for ref in spine_element if spine_element is not None else []:
                item=items.get(ref.get('idref'))
                if item is None: errors.append('Unknown spine item')
                elif item.get('media-type')!='application/xhtml+xml': errors.append('Non-XHTML spine item in generated book')
                else: spine.append(item.attrib['href'])
            if not spine: errors.append('Empty reading order')
            if len(spine)!=len(set(spine)): errors.append('Duplicate spine item')
            if expected_spine is not None and spine!=expected_spine: errors.append('Reading order does not match selected materials and chapters')
            documents={}; id_counts={}
            for member,item in by_path.items():
                if item.get('media-type')=='application/xhtml+xml' and member in names:
                    tree=ET.fromstring(archive.read(member)); found=set()
                    if tree.tag!=f'{{{XHTML}}}html': errors.append('XHTML namespace missing: '+member)
                    for element in tree.iter():
                        identity=element.get('id')
                        if identity:
                            if identity in found: errors.append('Duplicate XHTML ID: '+member+'#'+identity)
                            found.add(identity); id_counts[identity]=id_counts.get(identity,0)+1
                    documents[member]=(tree,found)
            for member,(tree,_) in documents.items():
                for element in tree.iter():
                    for key in ('href','src'):
                        if not element.get(key): continue
                        url=urlsplit(element.get(key))
                        local=element.tag.rsplit('}',1)[-1]
                        if url.scheme or url.netloc:
                            if local!='a' or url.scheme not in ('http','https','mailto'): errors.append('Unsupported external EPUB resource: '+element.get(key))
                            continue
                        target=posixpath.normpath(posixpath.join(posixpath.dirname(member),unquote(url.path))) if url.path else member
                        if target not in by_path: errors.append('Broken EPUB resource reference: '+member+': '+element.get(key))
                        elif url.fragment and (target not in documents or unquote(url.fragment) not in documents[target][1]): errors.append('Broken EPUB anchor: '+element.get(key))
            if paragraph_ids is not None:
                for identity in paragraph_ids:
                    if id_counts.get(identity)!=1: errors.append('Paragraph must appear exactly once: '+identity)
            for cover in covers:
                raw=archive.read(cover); mime=by_path[cover].get('media-type')
                if not ((mime=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='image/jpeg' and raw.startswith(b'\xff\xd8'))): errors.append('Cover image MIME type mismatch')
            for nav in navs:
                if nav in documents and documents[nav][0].find(f'.//{{{XHTML}}}nav[@{{{EPUB}}}type="toc"]') is None: errors.append('Navigation document lacks toc nav')
            undeclared=set(names)-set(by_path)-{'mimetype','META-INF/container.xml',package_path}
            if undeclared: errors.append('Undeclared generated resources: '+', '.join(sorted(undeclared)))
            counts={'manifest_items':len(items),'spine_items':len(spine),'paragraphs_checked':len(paragraph_ids or [])}
    except (OSError,ValueError,KeyError,ET.ParseError,zipfile.BadZipFile) as exc:
        errors.append(str(exc))
    internal_ok=not errors
    official={'status':'not_run'}
    if not errors:
        try: command=checker_command(project_root or path.parent,jar,java)
        except (ValueError,OSError,KeyError) as exc:
            command=None; errors.append(str(exc)); official={'status':'failed','message':str(exc)}
        if command:
            with tempfile.TemporaryDirectory(prefix='textoria-epubcheck-') as directory:
                report=Path(directory)/'report.json'
                try:
                    result=subprocess.run(command+['--json',str(report),'--quiet',str(path)],capture_output=True,text=True,timeout=60)
                    payload=json.loads(report.read_text()) if report.exists() else None
                    messages=payload.get('messages',[]) if isinstance(payload,dict) else []
                    failures=[m for m in messages if str(m.get('severity','')).upper() in ('ERROR','FATAL')]
                    official={'status':'passed' if result.returncode==0 and payload is not None and not failures else 'failed',
                              'return_code':result.returncode,'messages':messages,
                              'checker':payload.get('checker',{}) if isinstance(payload,dict) else {},
                              'stderr':result.stderr[-4000:]}
                    if official['status']=='failed': errors.append('EPUBCheck did not pass')
                except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
                    official={'status':'failed','message':str(exc)}; errors.append('EPUBCheck failed to run: '+str(exc))
        elif official['status']!='failed':
            official={'status':'not_available'}
            if require_epubcheck: errors.append('EPUBCheck is required but is unavailable')
            else: warnings.append('EPUBCheck unavailable; only internal package checks were performed')
    return {'ok':not errors,'internal':{'status':'passed' if internal_ok else 'failed'},
            'epubcheck':official,'errors':errors,'warnings':warnings,'counts':counts,
            'identifier':identifier,'title':title,'spine':spine,
            'compliance_verified':not errors and official['status']=='passed'}


def main():
    parser=argparse.ArgumentParser(description='Validate an EPUB without rebuilding a book')
    parser.add_argument('epub',type=Path); parser.add_argument('--project-root',type=Path)
    parser.add_argument('--epubcheck-jar',type=Path); parser.add_argument('--java',type=Path)
    parser.add_argument('--require-epubcheck',action='store_true'); args=parser.parse_args()
    result=validate_epub(args.epub,project_root=args.project_root,jar=args.epubcheck_jar,java=args.java,require_epubcheck=args.require_epubcheck)
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
