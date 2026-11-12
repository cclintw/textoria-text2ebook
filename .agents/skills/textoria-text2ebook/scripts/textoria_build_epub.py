#!/usr/bin/env python3
"""Adapt Textoria EPUB packaging to confirmed Text2Ebook content and optional assets."""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

from markdown_it import MarkdownIt
from textoria_common import read_json, write_json, write_stage_report, ensure_dirs
from textoria_export import validate_archive
from textoria_validate_epub import OPF, DC, XHTML, EPUB, OCF, validate_epub

ET.register_namespace('',XHTML)
ET.register_namespace('epub',EPUB)
ET.register_namespace('opf',OPF)
ET.register_namespace('dc',DC)
ET.register_namespace('ocf',OCF)
XML='http://www.w3.org/XML/1998/namespace'


def _element(parent, namespace, tag, text=None, **attrs):
    node=ET.SubElement(parent,f'{{{namespace}}}{tag}',attrs)
    if text is not None:node.text=str(text)
    return node


def _serialize(node):
    return ET.tostring(node,encoding='utf-8',xml_declaration=True)


def _page(title,language,body_class=''):
    page=ET.Element(f'{{{XHTML}}}html',{'lang':language,f'{{{XML}}}lang':language})
    head=_element(page,XHTML,'head')
    _element(head,XHTML,'meta',charset='utf-8')
    _element(head,XHTML,'title',title)
    _element(head,XHTML,'link',rel='stylesheet',type='text/css',href='../Styles/reader.css')
    body=_element(page,XHTML,'body',**({'class':body_class} if body_class else {}))
    return page,body


def _markdown(parent,text):
    parser=MarkdownIt('commonmark',{'html':False,'xhtmlOut':True}).enable('table')
    tokens=parser.parse(text)
    def inspect(items):
        for token in items:
            if token.type=='image':raise ValueError('EPUB 目前只接收獨立封面；正文或文字頁的 Markdown 內嵌圖片尚未支援，請先明確處理圖片標記。')
            inspect(token.children or [])
    inspect(tokens)
    rendered=parser.renderer.render(tokens,parser.options,{})
    wrapper=ET.fromstring(f'<div xmlns="{XHTML}">'+rendered+'</div>')
    for child in wrapper:parent.append(child)


def _text_page(title,language,kind,text,markdown):
    page,body=_page(title,language,'frontmatter')
    section=_element(body,XHTML,'section',id=kind)
    section.set(f'{{{EPUB}}}type','titlepage' if kind=='titlepage' else 'copyright-page')
    if markdown:_markdown(section,text)
    else:
        for block in re.split(r'\n\s*\n',text.replace('\r\n','\n').replace('\r','\n').strip()):
            paragraph=_element(section,XHTML,'p')
            for index,line in enumerate(block.splitlines()):
                if index==0:paragraph.text=line
                else:_element(paragraph,XHTML,'br').tail=line
    return _serialize(page)


def _filename(title):
    value=re.sub(r'[\\/:*?"<>|\x00-\x1f]','_',title).strip(' .') or 'book'
    while len(value.encode('utf-8'))>180:value=value[:-1]
    return value+'.epub'


def build_epub(root: Path,data: dict,metadata: dict,materials: dict,project_root: Path,*,
               epubcheck_jar: Path | None = None,java: Path | None = None,require_epubcheck: bool = False) -> dict:
    validate_archive(data)
    state_path=root/'state.json';state=read_json(state_path)
    identity=state.setdefault('epub_identity',{})
    if not identity.get('identifier'):
        existing=data['documents'][0].get('identifier') if len(data['documents'])==1 else None
        identity['identifier']=existing or 'urn:uuid:'+str(uuid.uuid4())
        write_json(state_path,state)
    identifier=identity['identifier'];title=metadata['title']
    language=data['collections'][0].get('language') or 'zh-Hant'
    if not re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*',language):raise ValueError('Book language tag is invalid')
    modified=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    checks={root/'intermediate/archive.json':hashlib.sha256((root/'intermediate/archive.json').read_bytes()).hexdigest(),
            root/'metadata.json':hashlib.sha256((root/'metadata.json').read_bytes()).hexdigest()}
    for item in materials['files'].values():checks[root/item['relative_path']]=item['sha256']
    files={};manifest=[];spine=[];front=[]
    def add(key,href,mime,raw,properties=''):
        files['OEBPS/'+href]=raw
        manifest.append({'id':key,'href':href,'media-type':mime,**({'properties':properties} if properties else {})})
    if 'cover' in materials['files']:
        item=materials['files']['cover'];image=root/item['relative_path'];actual=item['inspection']['format']
        extension='png' if actual=='png' else 'jpg';image_href='Images/cover.'+extension
        add('cover-image',image_href,'image/png' if actual=='png' else 'image/jpeg',image.read_bytes(),'cover-image')
        page,body=_page(title,language,'cover')
        section=_element(body,XHTML,'section',id='cover');section.set(f'{{{EPUB}}}type','cover')
        _element(section,XHTML,'img',src='../'+image_href,alt=title+'封面')
        add('cover','Text/cover.xhtml','application/xhtml+xml',_serialize(page));spine.append('cover');front.append(('封面','cover','Text/cover.xhtml'))
    for kind,label in [('titlepage','書名頁'),('copyright','版權頁')]:
        if kind in materials['files']:
            item=materials['files'][kind];source=root/item['relative_path']
            text=source.read_bytes().decode(item['inspection']['encoding']).lstrip('\ufeff')
            href=f'Text/{kind}.xhtml'
            add(kind,href,'application/xhtml+xml',_text_page(label,language,kind,text,source.suffix.lower()=='.md'))
            spine.append(kind);front.append((label,kind,href))
    # The navigation document is also a visible table-of-contents page.
    spine.append('nav')
    divisions={d['division_id']:d for d in data['divisions']};children={};paragraphs={}
    for division in data['divisions']:
        parent=division['parent_division_id']
        if parent and divisions[parent]['document_id']!=division['document_id']:raise ValueError('Division parent belongs to another document')
        children.setdefault(parent or '',[]).append(division)
    for group in children.values():group.sort(key=lambda d:int(d['sort_order']))
    for paragraph in data['paragraphs']:paragraphs.setdefault(paragraph['division_id'],[]).append(paragraph)
    for group in paragraphs.values():group.sort(key=lambda p:int(p['paragraph_index']))
    page_for={};roots=[]
    for document in data['documents']:
        roots.extend(d for d in children.get('',[]) if d['document_id']==document['document_id'])
    def section(parent,division,href,depth):
        identity=division['division_id']
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*',identity):raise ValueError('Division identifier is not safe for EPUB anchors')
        page_for[identity]=href+'#'+quote(identity)
        node=_element(parent,XHTML,'section',id=identity)
        _element(node,XHTML,'h'+str(min(depth,6)),division['title'])
        for paragraph in paragraphs.get(identity,[]):
            unit=_element(node,XHTML,'div',id=paragraph['paragraph_id'],**{'class':'text-unit'})
            _markdown(unit,paragraph['text'])
        for child in children.get(identity,[]):section(node,child,href,depth+1)
    for number,division in enumerate(roots,start=1):
        href=f'Text/Section{number:04d}.xhtml';key=f'chapter-{number:04d}'
        page,body=_page(division['title'],language);body.set(f'{{{EPUB}}}type','bodymatter')
        section(body,division,href,1)
        add(key,href,'application/xhtml+xml',_serialize(page));spine.append(key)
    if len(page_for)!=len(divisions):raise ValueError('Some divisions are unreachable in the ebook hierarchy')
    nav,body=_page('目錄',language)
    toc=_element(body,XHTML,'nav',id='toc');toc.set(f'{{{EPUB}}}type','toc')
    _element(toc,XHTML,'h1','目錄');listing=_element(toc,XHTML,'ol')
    for label,kind,href in front:_element(_element(listing,XHTML,'li'),XHTML,'a',label,href=posixpath.basename(href))
    def nav_item(parent,division):
        item=_element(parent,XHTML,'li')
        target=page_for[division['division_id']].removeprefix('Text/')
        _element(item,XHTML,'a',division['title'],href=target)
        if children.get(division['division_id']):
            nested=_element(item,XHTML,'ol')
            for child in children[division['division_id']]:nav_item(nested,child)
    for document in data['documents']:
        document_roots=[d for d in roots if d['document_id']==document['document_id']]
        if not document_roots:raise ValueError('Document has no divisions to export: '+document['title'])
        parent=listing
        if len(data['documents'])>1:
            group=_element(listing,XHTML,'li');_element(group,XHTML,'span',document['title']);parent=_element(group,XHTML,'ol')
        for division in document_roots:nav_item(parent,division)
    add('nav','Text/nav.xhtml','application/xhtml+xml',_serialize(nav),'nav')
    css=Path(__file__).resolve().parents[1]/'themes/epub/reader.css'
    add('css','Styles/reader.css','text/css',css.read_bytes())
    package=ET.Element(f'{{{OPF}}}package',{'version':'3.0','unique-identifier':'pub-id'})
    info=_element(package,OPF,'metadata');_element(info,DC,'identifier',identifier,id='pub-id')
    _element(info,DC,'title',title);_element(info,DC,'language',language)
    roles={'作者':'aut','編者':'edt','校註者':'ann','校訂者':'edt'}
    for tag,people in [('creator',metadata['creators']),('contributor',metadata['contributors'])]:
        for index,person in enumerate(people,start=1):
            key=f'{tag}-{index}';_element(info,DC,tag,person['name'],id=key)
            if person['role'] in roles:_element(info,OPF,'meta',roles[person['role']],refines='#'+key,property='role',scheme='marc:relators')
    _element(info,OPF,'meta',modified,property='dcterms:modified')
    entries=_element(package,OPF,'manifest')
    for item in manifest:_element(entries,OPF,'item',**item)
    order=_element(package,OPF,'spine')
    for key in spine:_element(order,OPF,'itemref',idref=key)
    container=ET.Element(f'{{{OCF}}}container',{'version':'1.0'})
    _element(_element(container,OCF,'rootfiles'),OCF,'rootfile',**{'full-path':'OEBPS/content.opf','media-type':'application/oebps-package+xml'})
    files['META-INF/container.xml']=_serialize(container);files['OEBPS/content.opf']=_serialize(package)
    expected=[next(item['href'] for item in manifest if item['id']==key) for key in spine]
    input_hash=hashlib.sha256(json.dumps([[str(path.relative_to(root)),value] for path,value in checks.items()],ensure_ascii=False).encode()).hexdigest()
    directory=root/'export';directory.mkdir(parents=True,exist_ok=True)
    target=directory/_filename(title);owned=state.get('epub_outputs',{})
    if target.exists() and owned.get(str(target.relative_to(root)))!=hashlib.sha256(target.read_bytes()).hexdigest():
        target=target.with_name(target.stem+'-'+input_hash[:12]+'.epub')
        if target.exists() and owned.get(str(target.relative_to(root)))!=hashlib.sha256(target.read_bytes()).hexdigest():
            raise ValueError('EPUB destination contains an untracked or modified file; existing files were preserved')
    with tempfile.TemporaryDirectory(prefix='.epub-build-',dir=directory) as temporary:
        candidate=Path(temporary)/'candidate.epub'
        with zipfile.ZipFile(candidate,'w') as archive:
            archive.writestr('mimetype',b'application/epub+zip',compress_type=zipfile.ZIP_STORED)
            for path,raw in files.items():archive.writestr(path,raw,compress_type=zipfile.ZIP_DEFLATED)
        validation=validate_epub(candidate,project_root=project_root,jar=epubcheck_jar,java=java,
                                 require_epubcheck=require_epubcheck,expected_spine=expected,
                                 paragraph_ids=[p['paragraph_id'] for p in data['paragraphs']])
        if not validation['ok']:
            write_stage_report(ensure_dirs(root),'build_epub',{'ok':False,'validation':validation,'input_hash':input_hash})
            return {'ok':False,'status':'epub_validation_failed','output':str(root),'epub_validation':validation}
        if any(not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=value for path,value in checks.items()):
            raise ValueError('Book inputs changed during EPUB generation; prior outputs were preserved')
        candidate.replace(target)
    state=read_json(state_path)
    state.setdefault('epub_outputs',{})[str(target.relative_to(root))]=hashlib.sha256(target.read_bytes()).hexdigest()
    state['epub_identity']['last_output']=str(target.relative_to(root));state['updated_at']=modified
    write_json(state_path,state)
    write_stage_report(ensure_dirs(root),'build_epub',{
        'ok':True,'epub':str(target.resolve()),'identifier':identifier,'input_hash':input_hash,
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'validation':validation})
    return {'ok':True,'status':'epub_built','output':str(root.resolve()),'epub':str(target.resolve()),
            'identifier':identifier,'epub_validation':validation,'links':{'EPUB':str(target.resolve())}}
