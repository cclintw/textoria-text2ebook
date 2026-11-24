# Basic book metadata

## Values and evidence

Collect only the title, author/editor, and any explicitly evidenced annotator/reviser. The title is required; unknown optional contributors may be omitted or described as unknown in the conversation. Missing signatures do not prove anonymity. Keep contributor roles distinct and never infer book authorship solely from a preface signature.

Read the opening text, title, prefaces, colophons, and signatures. The filename is supporting evidence, not a reason to overwrite a confirmed title. Record a source path/paragraph and brief basis for each proposed value. External recollection must not override text or user-confirmed information.

The program deterministically recognizes title headings and explicit labeled lines; it does not resolve every historical signature. The agent may propose additional evidence-based values through a pending patch for user review. Do not equate an empty automatic author field with evidence that the author is unknown.

## Supported edits and imports

Users may add, delete, or edit values in the conversation, edit the metadata file, or supply CSV, XLSX, JSON, TXT, or Markdown. CSV/XLSX can contain field/value pairs or a single record with named columns. Resolve multiple records or worksheets explicitly; use `--metadata-sheet` when needed. XLSX imports read literal values with the standard library, never execute formulas, and reject ambiguous/formula-based input. Legacy XLS needs conversion to XLSX or CSV.

JSON must be a named object without duplicate keys. Reject ambiguous records or repeated fields rather than choosing the first. Preserve uploaded originals under `source/metadata/` with hashes and versioned filenames.

Canonical `metadata.json` has `title`, `creators`, `contributors`, and `extra`. People have `name` and `role`. The built-in roles remain the exact program values below:

| Meaning | Stored role | Convenience patch key |
|---|---|---|
| Author | `作者` | `author` |
| Editor | `編者` | `editor` |
| Annotator | `校註者` | `annotator` |
| Reviser | `校訂者` | `reviser` |

Do not translate these stored roles during a documentation edit. `extra` holds only additional values volunteered by the user; do not pre-create ISBN, publisher, publication date, or rights fields. A patch replaces the complete list for its specified role.

## Review and confirmation

Use the verified Python executable for `PYTHON`, the actual collection for `COLLECTION_ROOT`, and real file paths for import arguments:

```text
PYTHON "$SKILL_DIR/scripts/textoria_build.py" --output COLLECTION_ROOT --task review_metadata
PYTHON "$SKILL_DIR/scripts/textoria_build.py" --output COLLECTION_ROOT --task edit_metadata --metadata-patch '{"title":"Example Work","author":"Example Author"}'
PYTHON "$SKILL_DIR/scripts/textoria_build.py" --output COLLECTION_ROOT --task edit_metadata --metadata-file METADATA_FILE
```

The example book and author are fictional examples, not suggested values for a real source. Use `--metadata-delete` with the actual field to remove a value.

A pending review returns `needs_metadata_confirmation`, `metadata_file`, values, evidence, and `metadata_token`. Exit code 2 denotes a review checkpoint. Show actual values and evidence, provide a clickable file link, and offer Confirm/Edit choices plus free-text or file-based changes. Do not ask about materials at this stage.

After the user explicitly confirms the displayed version:

```text
PYTHON "$SKILL_DIR/scripts/textoria_build.py" --output COLLECTION_ROOT --task confirm_metadata --metadata-token METADATA_TOKEN
```

Do not combine imports/patches and confirmation in one call. Direct file edits also require showing the new values for approval; old tokens cannot approve changed values. On `metadata_confirmed`, the archive is synchronized and materials become the next step. This command does not receive materials or generate outputs.

## Preserve manual decisions

Save evidence, review hashes, imported inputs, and removals in `state.json.reviews.metadata`. The state record is not a second editable metadata file. Confirmed manual values and deletions survive rebuilding; a deleted role must not return through inference. Missing or invalid saved metadata requires resolution, not silent reconstruction from guesses.

Project approved values into archive collection/document metadata for websites and EPUB. A title-only change does not rename folders or invalidate unchanged chapter structure. Do not assign one author's identity to every document in a multi-document archive without evidence. Metadata does not invent title-page text or determine the rights of modern annotations.
