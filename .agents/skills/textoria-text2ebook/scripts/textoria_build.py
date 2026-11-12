#!/usr/bin/env python3
"""Run the Textoria v1 full archive workflow.

This file is intentionally thin. Stage logic lives in separate modules so each
pipeline step can be edited, tested, and rebuilt independently.
"""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path

from textoria_build_search import build_search_index
from textoria_build_site import build_static_site
from textoria_clean_text import clean_text
from textoria_common import (
    SKILL_NAMESPACE,
    default_collection_name,
    default_collection_output,
    default_collection_slug,
    ensure_dirs,
    now_iso,
    write_json,
    read_json,
)
from textoria_export import export_intermediate_files, load_archive, reader_paragraphs
from textoria_extract_text import extract_plain_text
from textoria_structure import build_structure, write_structure_review
from textoria_utf8_converter import prepare_utf8, inspect_input
from textoria_validate import validate_outputs
from textoria_chapter_review import working_text_path, preserve_source, prepare_review
from textoria_metadata import process_metadata, project_metadata
from textoria_materials import process_materials
from textoria_build_epub import build_epub


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path)


def read_project_registry(project_root: Path) -> dict:
    collections = []
    for namespace in (SKILL_NAMESPACE, "textoria-digital-library"):
        registry_path = project_root / namespace / "registry.json"
        if registry_path.exists():
            registry = read_json(registry_path)
            collections.extend(registry.get("collections", []))
    if not collections and (project_root / "textoria" / "registry.json").exists():
        raise ValueError("Legacy textoria/ archive detected; run textoria_migrate_paths.py before continuing")
    return {"collections": collections}


def resolve_collection_slug(project_root: Path, source: Path, collection_name: str) -> str:
    base_slug = default_collection_slug(source, collection_name)
    registry = read_project_registry(project_root)
    source_path = relative_to_project(source, project_root)
    used_slugs = set()
    for entry in registry.get("collections", []):
        entry_slug = entry.get("slug") or entry.get("collection_id") or entry.get("archive_id")
        if not entry_slug:
            continue
        if source_path in entry.get("source_files", []):
            return entry_slug
        used_slugs.add(entry_slug)
    if base_slug not in used_slugs:
        return base_slug
    suffix = 2
    while f"{base_slug}-{suffix}" in used_slugs:
        suffix += 1
    return f"{base_slug}-{suffix}"


def retag_collection(data: dict, collection_slug: str) -> None:
    old_collection_id = data["collections"][0]["collection_id"]
    data["collections"][0]["collection_id"] = collection_slug
    data["collections"][0]["slug"] = collection_slug
    for table in ("documents", "divisions", "paragraphs", "sentences", "tokens", "source_files"):
        for row in data.get(table, []):
            if row.get("collection_id") == old_collection_id:
                row["collection_id"] = collection_slug


def update_project_registry(project_root: Path, output: Path, source: Path, data: dict, collection_slug: str) -> None:
    textoria_root = output.parent.parent if output.parent.name == "collections" else project_root / SKILL_NAMESPACE
    textoria_root.mkdir(parents=True, exist_ok=True)
    registry_path = textoria_root / "registry.json"
    registry = read_json(registry_path) if registry_path.exists() else {"collections": []}

    collection = data["collections"][0]
    archive_path = relative_to_project(output, project_root)
    collection_id = collection_slug

    entry = {
        "collection_id": collection_id,
        "archive_id": collection_id,
        "slug": collection_id,
        "name": collection["name"],
        "title": collection["title"],
        "path": archive_path,
        "source_files": [relative_to_project(source, project_root)],
        "updated_at": now_iso(),
    }

    collections = registry.get("collections", [])
    replaced = False
    for index, existing in enumerate(collections):
        if existing.get("path") == archive_path or existing.get("collection_id") == collection_id:
            collections[index] = {**existing, **entry}
            replaced = True
            break
    if not replaced:
        collections.append(entry)
    registry["collections"] = collections
    write_json(registry_path, registry)


TASKS = {
    'inspect_input': 0, 'convert_encoding': 1, 'extract_plain_text': 2,
    'review_chapters': 4, 'confirm_chapters': 4,
    'review_metadata': 4, 'edit_metadata': 4, 'confirm_metadata': 4,
    'review_materials': 4, 'receive_materials': 4, 'confirm_materials': 4, 'skip_materials': 4,
    'clean_text': 3, 'reclean_text': 3, 'structure_text': 4, 'restructure_text': 4,
    'export_intermediate_files': 4, 'build_sqlite': 5, 'rebuild_database': 5,
    'build_fulltext_search': 6, 'build_static_site': 7, 'rebuild_site': 7,
    'build_reader_page': 7, 'build_browse_page': 7,
    'build_fulltext_archive': 7, 'build_epub': 7, 'validate_output': 8,
}


MATERIAL_TASKS = ('review_materials', 'receive_materials', 'confirm_materials', 'skip_materials')

def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def producer_hash(names: tuple[str, ...]) -> str:
    root = Path(__file__).parent
    return hashlib.sha256(b''.join((root / name).read_bytes() for name in names)).hexdigest()


def build_fulltext_archive(source: Path, project_root: Path, output: Path,
                           text_column: str | None, collection_name: str, collection_slug: str,
                           confirm_inferred_structure: bool = False, *,
                           task: str = 'build_fulltext_archive', enable_sentences: bool = False,
                           export_csv: bool = False, export_markdown: bool = False,
                           review_token: str | None = None, metadata_token: str | None = None,
                           metadata_file: Path | None = None, metadata_patch: dict | None = None,
                           metadata_deletes: list[str] | None = None, metadata_sheet: str | None = None,
                           material_files: list[Path] | None = None, material_replacements: list[str] | None = None,
                           materials_token: str | None = None, accept_material_conflicts: bool = False,
                           epubcheck_jar: Path | None = None, java: Path | None = None, require_epubcheck: bool = False) -> dict:
    paths = ensure_dirs(output)
    config = {
        'schema_version': 2, 'collection_name': collection_name, 'collection_slug': collection_slug,
        'source_file': str(source), 'text_column': text_column,
        'cleaning_profile': 'cc_text_cleaner',
        'confirm_inferred_structure': confirm_inferred_structure,
        'enable_sentences': enable_sentences,
        'export_csv': export_csv, 'export_markdown': export_markdown,
    }
    write_json(paths.config / 'textoria.json', config)
    state_path = paths.root / 'state.json'
    state = read_json(state_path) if state_path.exists() else {}
    previous_source = state.get('source', {})
    source_input = source
    if not source.exists() and previous_source.get('saved_path'):
        saved_path = Path(previous_source['saved_path'])
        if saved_path.exists():
            saved_inspection = inspect_input(saved_path)
            if saved_inspection['sha256'] != previous_source.get('sha256'):
                raise ValueError('Saved source was modified; restore the original preserved source before continuing')
            source_input = saved_path
    inspection = inspect_input(source_input) if source_input.exists() else previous_source
    if inspection and inspection.get('sha256') == previous_source.get('sha256'):
        inspection = {**previous_source, **inspection}
    inspection = {**inspection, 'source_file': str(source)} if inspection else {}
    if not inspection:
        raise ValueError(f'Source file does not exist: {source}')
    if not inspection['readable']:
        raise ValueError('Source contains no readable text')
    limit = TASKS[task]
    from textoria_common import write_stage_report
    if limit == 0:
        write_stage_report(paths, 'inspect_input', {'ok': True, 'source_manifest': inspection})
        return {'ok': True, 'inspection': inspection, 'output': str(output)}

    clean_path = working_text_path(paths.root)
    archive_path = paths.intermediate / 'archive.json'
    clean_producer = producer_hash(('textoria_utf8_converter.py', 'textoria_extract_text.py', 'textoria_clean_text.py'))
    old_clean = state.get('stages', {}).get('clean_text', {})
    source_changed = bool(old_clean.get('source_hash') and (
        old_clean['source_hash'] != inspection.get('sha256') or
        old_clean.get('source_file') != str(source)))
    extraction_changed = bool(old_clean and old_clean.get('text_column') != text_column)
    need_clean = (not clean_path.exists() or source_changed or extraction_changed or task == 'reclean_text')
    if need_clean and clean_path.exists() and old_clean.get('output_hash'):
        if (old_clean.get('adopted_working_text') or file_hash(clean_path) != old_clean['output_hash']) and task != 'reclean_text':
            raise ValueError('Cleaned text has manual edits; use reclean_text explicitly to replace it')
    if limit >= 3 and source_input.exists():
        inspection = preserve_source(source_input, paths.root, inspection)
        write_stage_report(paths, 'inspect_input', {'ok': True, 'source_manifest': inspection})
    if limit <= 2 or need_clean:
        if not source_input.exists():
            raise ValueError('Original source is required for conversion, extraction or cleaning')
        prepared = prepare_utf8(source_input, paths, persist=task == 'convert_encoding')
        if limit == 1:
            return {'ok': True, 'prepared_file': str(prepared['prepared_path']), 'output': str(output)}
        extracted = extract_plain_text(source_input, prepared['text'], text_column, paths,
                                       persist=task == 'extract_plain_text')
        if limit == 2:
            return {'ok': True, 'plain_text': str(extracted['plain_path']), 'output': str(output)}
        clean_text(extracted['text'], source, paths, inspection['detected_encoding'])
        write_stage_report(paths, 'inspect_input', {'ok': True, 'source_manifest': inspection})
        write_stage_report(paths, 'clean_text', {
            **read_json(state_path)['stages']['clean_text'],
            'producer_hash': clean_producer, 'text_column': text_column,
            'source_hash': inspection['sha256'], 'source_file': str(source),
            'output_hash': file_hash(clean_path),
        })
    if limit >= 3 and clean_path.exists() and not old_clean and not need_clean:
        write_stage_report(paths, 'clean_text', {
            'ok': True, 'adopted_working_text': True, 'output_file': str(clean_path),
            'source_hash': inspection['sha256'], 'source_file': str(source),
            'output_hash': file_hash(clean_path), 'text_column': text_column,
        })
    if limit == 3:
        return {'ok': True, 'cleaned_text': str(clean_path), 'output': str(output)}

    state = read_json(state_path)
    old_structure = state.get('stages', {}).get('structure_text', {})
    structure_producer = producer_hash(('textoria_structure.py', 'textoria_export.py'))
    structure_options = [collection_name, enable_sentences, confirm_inferred_structure]
    need_structure = (need_clean or not archive_path.exists() or task == 'restructure_text' or
                      old_structure.get('ok') is not True or
                      old_structure.get('canonical_current') is not True or
                      old_structure.get('input_hash') != file_hash(clean_path) or
                      old_structure.get('producer_hash') != structure_producer or
                      old_structure.get('options') != structure_options)
    if need_structure:
        data = build_structure(clean_path.read_text(encoding='utf-8'), str(source), source.stem,
                               collection_name=collection_name,
                               confirm_candidate_headings=confirm_inferred_structure,
                               enable_sentences=enable_sentences)
        retag_collection(data, collection_slug)
        data['source_files'][0].update({
            'prepared_path': '', 'extracted_text_path': '',
            'detected_encoding': inspection['detected_encoding'],
            'byte_size': inspection['byte_size'], 'line_count': inspection['line_count'],
            'sha256': inspection['sha256'],
        })
        write_structure_review(paths, data)
        write_stage_report(paths, 'structure_text', {
            **read_json(state_path)['stages']['structure_text'],
            'input_hash': file_hash(clean_path), 'producer_hash': structure_producer,
            'options': structure_options, 'canonical_current': False,
        })
    else:
        data = load_archive(paths)
    if data['source_files']:
        extra = json.loads(data['source_files'][0].get('metadata_json') or '{}')
        extra['saved_source'] = inspection.get('saved_path', previous_source.get('saved_path', ''))
        data['source_files'][0]['metadata_json'] = json.dumps(extra, ensure_ascii=False)
    update_project_registry(project_root, output, source, data, collection_slug)
    review = prepare_review(paths.root, clean_path, data,
                            confirm_token=review_token if task == 'confirm_chapters' else None)
    data['structure_report'].update(needs_user_confirmation=not review['ok'], review_status=review['status'])
    write_stage_report(paths, 'structure_text', {
        **read_json(state_path)['stages']['structure_text'],
        'needs_user_confirmation': not review['ok'], 'review_status': review['status'],
    })
    if task == 'confirm_chapters' and not review_token:
        review.update(ok=False, status='needs_chapter_confirmation',
                      message='A current --review-token is required after the user reviews and confirms the chapter files')
        return review
    if not review['ok']:
        return review
    if need_structure or export_csv:
        export_intermediate_files(paths, data, export_csv=export_csv)
        write_stage_report(paths, 'structure_text', {
            **read_json(state_path)['stages']['structure_text'], 'canonical_current': True,
        })
    if task in ('review_chapters', 'confirm_chapters'):
        return review
    data = load_archive(paths)
    if task in ('review_metadata', 'edit_metadata', 'confirm_metadata') or task in MATERIAL_TASKS or limit > 4:
        metadata_result = process_metadata(
            paths.root, clean_path, data,
            token=metadata_token if task == 'confirm_metadata' else None,
            source_file=metadata_file, patch=metadata_patch, deletes=metadata_deletes,
            sheet=metadata_sheet)
        if task == 'confirm_metadata' and not metadata_token:
            metadata_result.update(ok=False, status='needs_metadata_confirmation',
                                   message='A current --metadata-token is required after explicit user confirmation')
            return metadata_result
        if not metadata_result['ok']:
            return metadata_result
        if project_metadata(data, metadata_result['metadata']):
            export_intermediate_files(paths, data, export_csv=export_csv)
            update_project_registry(project_root, output, source, data, collection_slug)
        if task in ('review_metadata', 'edit_metadata', 'confirm_metadata'):
            return metadata_result
    if task in MATERIAL_TASKS or limit > 4:
        materials_result = process_materials(
            paths.root, metadata_result['metadata'], sources=material_files,
            replacements=material_replacements,
            token=materials_token if task == 'confirm_materials' else None,
            skip=task == 'skip_materials', accept_conflicts=accept_material_conflicts)
        if task == 'confirm_materials' and not materials_token:
            materials_result.update(ok=False, status='needs_materials',
                                    message='A current --materials-token is required after explicit user completion')
            return materials_result
        if not materials_result['ok'] or task in MATERIAL_TASKS:
            return materials_result
    if task == 'build_epub':
        return build_epub(paths.root, data, metadata_result['metadata'], materials_result, project_root,
                          epubcheck_jar=epubcheck_jar, java=java, require_epubcheck=require_epubcheck)
    result = {
        'ok': True, 'collection_name': collection_name, 'output': str(output),
        'cleaned_text': str(clean_path), 'outline': review['outline'],
        'chapter_review': review['status'], 'archive': str(archive_path),
        'structure_confidence': data['structure_report']['confidence'],
        'structure_evidence': data['structure_report']['evidence'],
        'division_count': len(data['divisions']),
        'division_sample': [r['path'] for r in data['divisions'][:12]],
    }
    if limit == 4:
        return result
    if task in ('build_sqlite', 'rebuild_database'):
        db_path = paths.sqlite / 'library.sqlite'
        db_producer = producer_hash(('textoria_build_sqlite.py',))
        old_db = read_json(state_path).get('stages', {}).get('build_sqlite', {})
        if (not db_path.exists() or old_db.get('input_hash') != file_hash(archive_path) or
                old_db.get('producer_hash') != db_producer or task == 'rebuild_database'):
            from textoria_build_sqlite import build_sqlite_stage
            build_sqlite_stage(paths)
            write_stage_report(paths, 'build_sqlite', {
                'ok': True, 'input_hash': file_hash(archive_path), 'producer_hash': db_producer,
            })
        result['sqlite'] = str(db_path)
        return result
    rows = reader_paragraphs(data)
    if limit == 6:
        build_search_index(paths, rows)
        return result
    if task != 'validate_output':
        build_static_site(paths, data, rows, export_markdown=export_markdown)
    result['site'] = str(paths.site)
    validation = validate_outputs(paths)
    result.update(ok=validation['ok'], validation=validation)
    if task == 'build_fulltext_archive' and validation['ok']:
        epub_result = build_epub(paths.root, data, metadata_result['metadata'], materials_result, project_root,
                                 epubcheck_jar=epubcheck_jar, java=java, require_epubcheck=require_epubcheck)
        result.update(ok=epub_result['ok'], status='book_built' if epub_result['ok'] else epub_result['status'],
                      epub_validation=epub_result['epub_validation'])
        if epub_result.get('epub'):
            result['epub'] = epub_result['epub']
            result['identifier'] = epub_result['identifier']
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Build or resume a compact Textoria archive.')
    parser.add_argument('source', nargs='?')
    parser.add_argument('--project-root')
    parser.add_argument('--output')
    parser.add_argument('--collection-name')
    parser.add_argument('--task', choices=TASKS, default='build_fulltext_archive')
    parser.add_argument('--text-column')
    parser.add_argument('--epubcheck-jar', type=Path)
    parser.add_argument('--java', type=Path)
    parser.add_argument('--require-epubcheck', action='store_true')
    parser.add_argument('--material', type=Path, action='append', default=[])
    parser.add_argument('--replace-material', choices=('cover','titlepage','copyright'), action='append', default=[])
    parser.add_argument('--materials-token')
    parser.add_argument('--accept-material-conflicts', action='store_true')
    parser.add_argument('--metadata-token')
    parser.add_argument('--metadata-file', type=Path)
    parser.add_argument('--metadata-sheet')
    parser.add_argument('--metadata-patch', type=json.loads)
    parser.add_argument('--metadata-delete', action='append', default=[])
    parser.add_argument('--review-token', help='Token from the current chapter review, used only after explicit user confirmation')
    for flag in ('confirm-inferred-structure', 'enable-sentences', 'export-csv', 'export-markdown'):
        parser.add_argument('--' + flag, action=argparse.BooleanOptionalAction, default=None)
    args = parser.parse_args()
    if (args.material or args.replace_material) and args.task != 'receive_materials':
        parser.error('Material inputs require receive_materials; confirm in a separate command')
    if args.replace_material and not args.material:
        parser.error('--replace-material requires --material')
    if (args.materials_token or args.accept_material_conflicts) and args.task != 'confirm_materials':
        parser.error('Material confirmation flags require confirm_materials')
    metadata_input = args.metadata_file is not None or args.metadata_patch is not None or args.metadata_delete
    if metadata_input and args.task not in ('review_metadata', 'edit_metadata'):
        parser.error('Metadata updates require review_metadata or edit_metadata; review before confirming')
    if args.metadata_token and args.task != 'confirm_metadata':
        parser.error('--metadata-token is only valid with confirm_metadata')
    if args.metadata_sheet and args.metadata_file is None:
        parser.error('--metadata-sheet requires --metadata-file')
    if not args.source and not args.output:
        parser.error('Provide a source file or --output for an existing archive')
    output = Path(args.output).resolve() if args.output else None
    config_path = output / 'config/textoria.json' if output else None
    saved = read_json(config_path) if config_path and config_path.exists() else {}
    source_value = args.source or saved.get('source_file')
    if not source_value:
        parser.error('Source path is not recorded; provide the original source file')
    source = Path(source_value).resolve()
    project_root = Path(args.project_root).resolve() if args.project_root else (
        output.parent.parent.parent if output and output.parent.name == 'collections' else source.parent)
    if output is None:
        source_path = relative_to_project(source, project_root)
        for entry in read_project_registry(project_root).get('collections', []):
            if source_path in entry.get('source_files', []):
                stored = Path(entry['path'])
                output = stored if stored.is_absolute() else project_root / stored
                config_path = output / 'config/textoria.json'
                saved = read_json(config_path) if config_path.exists() else {}
                break
    name = args.collection_name or saved.get('collection_name') or default_collection_name(source)
    slug = saved.get('collection_slug') or resolve_collection_slug(project_root, source, name)
    output = output or default_collection_output(project_root, source, name, slug)
    if not saved and (output / 'config/textoria.json').exists():
        saved = read_json(output / 'config/textoria.json')
        name = args.collection_name or saved.get('collection_name') or name
        slug = saved.get('collection_slug') or slug
    def option(key):
        value = getattr(args, key)
        return value if value is not None else saved.get(key, False)
    try:
        result = build_fulltext_archive(
            source, project_root, output, args.text_column or saved.get('text_column'), name, slug,
            option('confirm_inferred_structure'), task=args.task,
            enable_sentences=option('enable_sentences'), export_csv=option('export_csv'),
            export_markdown=option('export_markdown'), review_token=args.review_token,
            metadata_token=args.metadata_token, metadata_file=args.metadata_file,
            metadata_patch=args.metadata_patch, metadata_deletes=args.metadata_delete, metadata_sheet=args.metadata_sheet,
            material_files=args.material, material_replacements=args.replace_material,
            materials_token=args.materials_token, accept_material_conflicts=args.accept_material_conflicts,
            epubcheck_jar=args.epubcheck_jar, java=args.java, require_epubcheck=args.require_epubcheck)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 2


if __name__ == '__main__':
    try:
        status = main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        status = 1
    raise SystemExit(status)
