# Canonical archive and optional database schema

## Primary data contract

`intermediate/archive.json` is the shared source for websites, browser search, and EPUB. Standard builds do not create SQLite. The schema is a neutral hierarchy:

```text
collection -> document -> division -> paragraph -> sentence -> token
```

Use recursive `divisions` for variable levels such as volumes, chapters, issues, dates, cases, and headings. Do not add fixed book/chapter/section tables or unrecognized fields to the canonical arrays.

The executable field contract is `CSV_FIELDS` in `scripts/textoria_common.py`. `textoria_export.validate_archive` validates checkpoints before consumption; `load_archive` supplies empty optional sentence/token arrays. Refer to those definitions when changing the model rather than maintaining a second SQL schema in documentation.

| Array | Purpose and relationships |
|---|---|
| `collections` | Exactly one collection with its identity, title, slug, language, timestamps, and serialized metadata. |
| `documents` | Bibliographic units belonging to the collection. |
| `divisions` | Ordered recursive divisions belonging to a document; `parent_division_id` identifies the parent when present. |
| `paragraphs` | Text units assigned to an existing division in the same document, with paragraph order and source offsets. |
| `source_files` | Original/prepared/extracted source provenance, format, encoding, size, hash, and order. |
| `metadata` | Subject-table/subject-ID key/value metadata records. |
| `sentences` | Optional ordered segments linked to paragraphs; segmentation is off by default. |
| `tokens` | Optional token records; ordinary book production does not add this layer. |

The first six arrays are required even if an optional collection-level list is empty. IDs must be unique within each array. Collection/document links must resolve. Division parents must exist without cycles, and paragraphs must belong to divisions in their own document. Extra checks may be performed by downstream consumers; do not present the general archive validator as enforcing every possible semantic rule.

Use existing `metadata_json` strings and the metadata array for the defined projection. Basic editable bibliographic values live in `metadata.json`, not a new canonical top-level author table. See [metadata.md](metadata.md) and [file-contracts.md](file-contracts.md).

## Browser index

The site builder assigns each division to its top-level reading page. The search index adds division titles/paths and relative paragraph hrefs to reader paragraphs, then writes a single classic-script `site/data/search_index.js` assigning `window.TEXTORIA_SEARCH_INDEX`.

Default validation compares search paragraph IDs, count, and text against the archive and checks that result anchors exist. A database is not involved in HTTP or direct-file browser search.

## Optional SQLite task

Only after a separately confirmed technical request, `build_sqlite` / `rebuild_database` can generate `sqlite/library.sqlite` from the same validated checkpoint. The implementation is `scripts/textoria_build_sqlite.py`; its SQL, indexes, and FTS declarations are authoritative for actual database output.

The optional database contains the eight canonical tables plus `paragraphs_fts`. It currently does not create a sentence FTS table. Paragraph FTS uses `unicode61` and includes document/division context. Database presence does not change the website's static search implementation.

Only these explicit checks require SQLite FTS5:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py --check-sqlite
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT --check-sqlite
```

The second command also validates the website. Database checks include integrity, table/FTS counts, paragraph linkage, archive-count agreement, and a sample FTS query. Existing databases are neither required nor updated by normal website/EPUB tasks.
