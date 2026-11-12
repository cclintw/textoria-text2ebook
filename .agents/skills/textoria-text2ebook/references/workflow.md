# Processing workflow

## Order and checkpoints

Resolve the requested outputs using [intent-policy.md](intent-policy.md), then follow:

```text
Inspect and preserve sources -> prepare working text and outline
-> confirm chapters -> confirm basic metadata -> choose optional materials
-> build requested outputs -> validate and deliver
-> offer optional Sites publication for a completed website
```

Use the [interactive choice interface](../SKILL.md#interactive-choices). Keep chapter, metadata, and material decisions separate. Existing explicit confirmations remain valid only while their corresponding content is unchanged.

In command examples, `PYTHON` is the verified environment executable, `SOURCE` an actual input path, `PROJECT` the project root, and `COLLECTION_ROOT` the actual saved book directory. Replace symbolic arguments before execution. Technical review tokens come from command results, not from fields the user must fill in.

## Inspect and review chapters

Check [runtime.md](runtime.md) and [text-cleaning.md](text-cleaning.md), then run:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --task inspect_input
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --collection-name NAME --task review_chapters
```

The chapter-review command preserves the source, writes the editable full text and outline, and returns `needs_chapter_confirmation` with exit code 2 while awaiting review. This is a checkpoint, not a build failure. Convert its `links` paths into real clickable conversation links to both files. Show the detected outline and the heading example required by SKILL.md; ask the user to inspect hierarchy and order at every confidence level.

Unconfirmed chapters block canonical archive publication and downstream outputs. Existing outputs are preserved. High confidence or `--confirm-inferred-structure` never substitutes for user approval.

After explicit confirmation of the current version:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_chapters --review-token REVIEW_TOKEN
```

This saves the approved structure and returns `chapters_confirmed` with metadata as the next step. It does not generate a website, SQLite database, or EPUB.

When the working text changes, run `review_chapters` again. A changed heading, hierarchy, order, paragraph count, or paragraph assignment requires a new review. An old token cannot approve a new version. Body wording changes that retain structure and paragraph membership can retain chapter approval. Low-confidence text without usable headings needs correction before confirmation.

The outline is derived from the working full text. Apply requested outline changes to the full-text headings first; never maintain conflicting structures. Ignore heading examples inside fenced code blocks.

## Preserve manual edits

Do not re-clean an existing manually edited working file automatically. Changed source bytes or extraction options that would overwrite it require an explicit decision to run `reclean_text`. A missing original can be replaced by its verified saved copy for supported continuation; a modified saved copy blocks processing.

Use `content/全文.md` for new books. If a legacy collection uses `clean/cleaned_text.md`, keep that file as its sole editable text. If both exist, stop and resolve which one is authoritative instead of choosing by timestamp.

## Metadata and materials

Follow [metadata.md](metadata.md) after chapter approval. `review_metadata` and `edit_metadata` prepare pending values; only `confirm_metadata --metadata-token` records explicit approval and projects the values into the archive. Rebuilding preserves manual values and removals. Do not ask about materials in the metadata question.

Then follow [materials.md](materials.md). `review_materials` lists saved assets; `receive_materials --material` saves provided files. On explicit completion, use the current `confirm_materials --materials-token`; on an explicit skip, use `skip_materials`. A skip never deletes previous assets. Resolve identity conflicts before confirmation.

The downstream build commands also enforce these checkpoints; they are not shortcuts around them.

## Build and validate

| Requested result | Task |
|---|---|
| Local HTTP or direct-file website | `rebuild_site` |
| EPUB only | `build_epub` |
| Website and EPUB | `build_fulltext_archive` |
| Validate an existing website | `validate_output` or the standalone validator below |

For a confirmed collection:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task rebuild_site
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT
```

Website generation, browser search, and default validation read `archive.json`, not SQLite. Validation checks archive structure, expected chapter pages, relative resources, search-index paragraph IDs and text, script order, and result anchors. The browser index is a classic script so both HTTP and direct-file reading work. See [theme-system.md](theme-system.md).

Only separately authorized `build_sqlite` or `rebuild_database` tasks create/update a database. Existing databases are not changed by website work. `textoria_validate.py COLLECTION_ROOT --check-sqlite` adds optional database checks. See [schema.md](schema.md).

For EPUB generation and official validation, follow [epub.md](epub.md). Report the checks actually performed, not assumed compliance.

## Deliver and optionally publish

Use the [completion format](../SKILL.md#completion-delivery): identify completed features, provide the actual local URL and service status, HTML and EPUB absolute paths when generated, and explain how each is used. Also link the working text, outline, and metadata. Do not claim missing outputs or leave template variables in the response.

After local website delivery, always ask the [final Sites publication question](../SKILL.md#optional-sites-publication). A yes authorizes the separate publishing workflow; report a real reading URL only after terminal success. Do not create a website solely to offer hosting after an EPUB-only task.

## Legacy paths

Read both current and `textoria-digital-library` registries. Continue a known collection with its actual `--output`; do not silently change its slug, move it, re-clean it, or reinstall its runtime. `textoria_migrate_paths.py` handles a verified legacy `textoria/` namespace with its own safeguards; it is not a general-purpose collection rename command.
