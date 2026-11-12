#!/usr/bin/env python3
"""Exercise compact checkpoint continuation, edit protection and optional exports."""
import hashlib,json,sqlite3,subprocess,tempfile,sys
from pathlib import Path

script=Path(__file__).resolve().parent/'textoria_build.py'
python=Path(sys.executable)

def call(*args, ok=True):
    r=subprocess.run([str(python),str(script),*map(str,args)],capture_output=True,text=True)
    data=json.loads(r.stdout)
    if ok and data.get('status') == 'needs_chapter_confirmation':
        confirmation=subprocess.run([str(python),str(script),'--output',data['output'],
                                     '--task','confirm_chapters','--review-token',data['review_token']],
                                    capture_output=True,text=True)
        assert confirmation.returncode==0,(confirmation.stdout,confirmation.stderr)
        r=subprocess.run([str(python),str(script),*map(str,args)],capture_output=True,text=True)
        data=json.loads(r.stdout)
    if ok and data.get('status') == 'needs_metadata_confirmation':
        confirmation=subprocess.run([str(python),str(script),'--output',data['output'],
                                     '--task','confirm_metadata','--metadata-token',data['metadata_token']],
                                    capture_output=True,text=True)
        assert confirmation.returncode==0,(confirmation.stdout,confirmation.stderr)
        r=subprocess.run([str(python),str(script),*map(str,args)],capture_output=True,text=True)
        data=json.loads(r.stdout)
    if ok and data.get('status') == 'needs_materials':
        selection=subprocess.run([str(python),str(script),'--output',data['output'],
                                  '--task','skip_materials'],capture_output=True,text=True)
        assert selection.returncode==0,(selection.stdout,selection.stderr)
        r=subprocess.run([str(python),str(script),*map(str,args)],capture_output=True,text=True)
        data=json.loads(r.stdout)
    assert (r.returncode==0)==ok,(r.stdout,r.stderr)
    return data

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

with tempfile.TemporaryDirectory(prefix='textoria-regression-') as tmp:
    project=Path(tmp).resolve()
    source=project/'source.md'
    source.write_text('# 測試文獻\n\n## 卷一\n\n洛陽永寧寺。\n\n## 卷二\n\n白馬寺在洛陽。\n',encoding='utf-8')
    original=digest(source)
    first=call(source,'--project-root',project,'--collection-name','測試文獻','--task','clean_text')
    root=Path(first['output'])
    assert root.parent.parent.name=='textoria-text2ebook'
    assert not (project/'textoria').exists()
    clean=root/'content/全文.md'
    assert clean.exists() and not (root/'intermediate').exists()
    assert (root/'source/source.md').read_bytes()==source.read_bytes()
    clean.write_text(clean.read_text()+'\n人工校訂保存。\n',encoding='utf-8')
    edited=digest(clean)
    call('--output',root,'--task','structure_text')
    archive=root/'intermediate/archive.json'
    data=json.loads(archive.read_text())
    assert not data.get('sentences') and not data.get('tokens')
    assert any('人工校訂保存' in p['text'] for p in data['paragraphs'])
    call('--output',root,'--task','build_fulltext_search')
    assert not (root/'sqlite').exists()
    website=call('--output',root,'--task','rebuild_site')
    assert 'sqlite' not in website and not (root/'sqlite').exists()
    call('--output',root,'--task','validate_output')
    from textoria_common import ensure_dirs
    from textoria_validate import validate_outputs
    paths=ensure_dirs(root)
    index=root/'site/data/search_index.js'
    original_index=index.read_text()
    from textoria_build_search import read_browser_search_index, write_browser_search_index
    corrupted=read_browser_search_index(index)
    corrupted['paragraphs'][0]['text']='不相符的搜尋正文'
    write_browser_search_index(paths,corrupted)
    assert any('Stale search text' in e for e in validate_outputs(paths)['errors'])
    index.write_text(original_index)
    page=root/'site/read'/f"{data['divisions'][0]['division_id']}.html"
    saved_page=page.read_bytes();page.unlink()
    assert not validate_outputs(paths)['ok']
    page.write_bytes(saved_page)
    assert validate_outputs(paths)['ok']
    assert not (root/'sqlite').exists()
    subprocess.run(['node', str(script.with_name('test_search.cjs')), str(root/'site')], check=True)
    print('PASS: search, website and validation without SQLite; stale search text and missing pages rejected')
    from unittest.mock import patch
    from textoria_runtime_check import check_runtime
    with patch.dict(sys.modules, {'sqlite3': None}):
        assert check_runtime()['ready']
        assert not check_runtime(check_sqlite=True)['ready']
        from textoria_build import build_fulltext_archive
        settings=json.loads((root/'config/textoria.json').read_text())
        no_sqlite=build_fulltext_archive(source,project,root,None,settings['collection_name'],
                                       settings['collection_slug'],task='rebuild_site')
        assert no_sqlite['ok'] and not (root/'sqlite').exists()
    print('PASS: website build and default runtime work when sqlite3 is unavailable')
    call('--output',root,'--task','build_sqlite')
    db=root/'sqlite/library.sqlite'
    assert validate_outputs(paths,db)['ok']
    with sqlite3.connect(db) as c:
        assert c.execute("SELECT count(*) FROM paragraphs WHERE text LIKE '%人工校訂保存%'").fetchone()[0]==1
    checkpoint_hash=digest(archive)
    database_hash=digest(db)
    call('--output',root,'--task','rebuild_site')
    assert digest(db)==database_hash
    assert edited==digest(clean) and checkpoint_hash==digest(archive)
    forbidden=('raw','prepared','csv','json','search','logs','site/md')
    assert all(not (root/p).exists() for p in forbidden)
    assert [p.name for p in (root/'site/data').iterdir()]==['search_index.js']
    assert {p.name for p in (root/'intermediate').iterdir()}=={'archive.json'}
    print('PASS: staged clean -> manual edit -> structure -> SQLite -> website; no redundant outputs')
    assert digest(source)==original
    source.unlink()
    call('--output',root,'--task','rebuild_database')
    call('--output',root,'--task','rebuild_site')
    print('PASS: downstream continuation without original source')
    data=json.loads(archive.read_text())
    data['paragraphs'][0]['text']='結構化人工修訂。'
    archive.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    call('--output',root,'--task','rebuild_database')
    with sqlite3.connect(db) as c:
        assert c.execute('SELECT text FROM paragraphs ORDER BY paragraph_index LIMIT 1').fetchone()[0]=='結構化人工修訂。'
    data['paragraphs'][0]['division_id']='missing'
    archive.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    dbhash=digest(db)
    call('--output',root,'--task','rebuild_database',ok=False)
    assert digest(db)==dbhash
    print('PASS: edited canonical archive is used; invalid links stop before replacing database')
    source.write_text('# 測試文獻\n\n## 卷一\n\n新的來源。\n',encoding='utf-8')
    call('--output',root,'--task','build_fulltext_archive',ok=False)
    assert digest(clean)==edited
    call('--output',root,'--task','reclean_text')
    call('--output',root,'--task','build_fulltext_archive')
    print('PASS: manual cleaned text protected from source changes; explicit reclean resumes')
    optional=project/'optional'
    call(source,'--project-root',project,'--output',optional,'--collection-name','匯出測試',
         '--enable-sentences','--export-csv','--export-markdown')
    assert (optional/'csv/paragraphs.csv').exists() and list((optional/'site/md').glob('*.md'))
    assert (optional/'export').exists() and not (optional/'sqlite').exists()
    assert json.loads((optional/'intermediate/archive.json').read_text())['sentences']
    call('--output',optional,'--task','rebuild_site')
    assert list((optional/'site/md').glob('*.md'))
    print('PASS: requested CSV/Markdown/sentences and saved options')
    converted=project/'converted'
    call(source,'--project-root',project,'--output',converted,'--task','convert_encoding')
    assert (converted/'prepared/source.utf8.md').exists()
    extracted=project/'extracted'
    call(source,'--project-root',project,'--output',extracted,'--task','extract_plain_text')
    assert (extracted/'intermediate/plain_text.md').exists()
    print('PASS: explicit conversion and extraction deliverables')
    plain=project/'plain.txt';plain.write_text('沒有可靠標題。\n\n只有段落。',encoding='utf-8')
    low=project/'low'
    call(plain,'--project-root',project,'--output',low,ok=False)
    assert (low/'content/全文.md').exists() and not (low/'intermediate/archive.json').exists()
    assert not (low/'sqlite').exists() and not (low/'site').exists()
    print('PASS: low confidence stops without downstream artifacts')
    csvsrc=project/'input.csv';csvsrc.write_bytes('正文\n洛陽，測試。\n'.encode('big5'))
    call(csvsrc,'--project-root',project,'--output',project/'csvinput','--task','clean_text','--text-column','正文')
    assert '洛陽' in (project/'csvinput/content/全文.md').read_text()
    print('PASS: non-UTF8 CSV uses normalized buffer')

    migration_project=project/'migration'
    migration_project.mkdir()
    migration_source=migration_project/'source.md'
    migration_source.write_text('# 遷移測試\n\n## 第一卷\n\ntextoria/不可改動正文。\n',encoding='utf-8')
    modern=Path(call(migration_source,'--project-root',migration_project,'--collection-name','遷移測試')['output'])
    call('--output',modern,'--task','build_sqlite')
    with sqlite3.connect(modern/'sqlite/library.sqlite') as con:
        original_paragraph=con.execute('SELECT text FROM paragraphs').fetchone()[0]
    namespace=modern.parent.parent
    namespace.rename(migration_project/'textoria')
    legacy_registry=migration_project/'textoria/registry.json'
    value=json.loads(legacy_registry.read_text())
    for row in value['collections']:
        row['path']=row['path'].replace('textoria-text2ebook/','textoria/',1)
    legacy_registry.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    runtime=migration_project/'.textoria'
    (runtime/'logs').mkdir(parents=True)
    (runtime/'logs/runtime_check.json').write_text(json.dumps({'required_packages':['charset_normalizer','bs4','jinja2','markdown_it','pypinyin']}))
    (runtime/'venv/bin').mkdir(parents=True)
    launcher=runtime/'venv/bin/example'
    launcher.write_text('#!'+str(runtime/'venv/bin/python')+'\n')
    migration_script=script.with_name('textoria_migrate_paths.py')
    def migration(*extra,ok=True):
        result=subprocess.run([str(python),str(migration_script),'--project-root',str(migration_project),*extra],capture_output=True,text=True)
        assert (result.returncode==0)==ok,(result.stdout,result.stderr)
        return json.loads(result.stdout)
    migration()
    assert (migration_project/'textoria').exists() and not namespace.exists()
    call(migration_source,'--project-root',migration_project,'--task','structure_text',ok=False)
    migration('--apply')
    assert namespace.exists() and not (migration_project/'textoria').exists()
    assert (migration_project/'.textoria-text2ebook/venv/bin/example').read_text().startswith('#!'+str(migration_project/'.textoria-text2ebook/venv'))
    call('--output',modern,'--task','rebuild_site')
    with sqlite3.connect(modern/'sqlite/library.sqlite') as con:
        assert con.execute('SELECT text FROM paragraphs').fetchone()[0]==original_paragraph
    assert len(json.loads((namespace/'registry.json').read_text())['collections'])==1
    assert migration('--apply')['changed_files']==0
    print('PASS: namespace migration, runtime launchers, unchanged paragraph text and resumed registry')
    namespace.rename(migration_project/'textoria')
    namespace.mkdir()
    sentinel=namespace/'another-skill.txt'
    sentinel.write_text('existing destination')
    migration('--apply',ok=False)
    assert sentinel.read_text()=='existing destination' and (migration_project/'textoria').exists()
    print('PASS: occupied namespace refuses migration without merging or deleting')

    from textoria_common import ensure_dirs
    from textoria_build_search import write_browser_search_index, read_browser_search_index
    payload={'paragraphs':[{'text':'白馬寺 </script><script>alert(1)</script> " \\ \u2028 \u2029 & < >'}]}
    index=write_browser_search_index(ensure_dirs(project/'serialized'),payload)
    assert read_browser_search_index(index)==payload
    assert '</script>' not in index.read_text()
    assert '\u2028' not in index.read_text() and '\u2029' not in index.read_text()
    print('PASS: classic-script index round-trips markup, quotes, slashes and Unicode separators')
