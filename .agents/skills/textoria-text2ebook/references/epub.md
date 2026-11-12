# EPUB generation and validation

## Entry points

Use confirmed text, chapters, metadata, and material decisions. Generation commands do not bypass the review checkpoints. Replace `PYTHON` with the verified interpreter and `COLLECTION_ROOT` with the actual collection path:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub
```

`build_epub` generates only EPUB. `build_fulltext_archive` generates the website and, after successful website checks, EPUB. `rebuild_site` generates only the website. All use the canonical archive without creating SQLite.

A successful result includes the actual EPUB path and validation result. A failed candidate does not replace an existing ebook.

## Content and packaging

- Reading order is cover, title page, copyright page, visible contents, and body. Include optional items only from supplied confirmed materials; do not invent pages or publication facts.
- Keep the original JPEG/PNG cover bytes, correct MIME declaration, and image proportions, with a visible cover page.
- Use hierarchical navigation, valid XHTML, and paragraph anchors. TXT and Markdown front matter are supported. Markdown inline images in body/front matter are currently rejected; resolve them explicitly rather than losing them or downloading resources silently.
- The ZIP container begins with an uncompressed `mimetype` and includes container/package documents, manifest, spine, navigation, resources, and styles. Output uses `.epub`.
- Keep the persistent identifier in `state.json` across rebuilds and title changes. Language and modification timestamps are managed internally; do not ask users to fill technical fields.
- Write a candidate first. Publish it only after successful validation and verifying that inputs have not changed. Preserve untracked or externally modified EPUBs; use a safe hash-suffixed output name rather than silently overwriting them.

## EPUBCheck resolution

The validator resolves explicit `--epubcheck-jar` / `--java` parameters, `TEXTORIA_EPUBCHECK_JAR` / `TEXTORIA_JAVA`, project `.textoria-text2ebook/tools/epub-tools.json`, and available PATH tools in the implemented order. The configuration's `java` and `epubcheck_jar` values must be actual usable paths.

If tools are already available, use them. New installation requires the [runtime approval](runtime.md); keep a complete official EPUBCheck distribution and dependencies in the project tool directory without changing system Java settings.

To require official checking during generation:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub --require-epubcheck
```

To validate an existing ebook independently:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate_epub.py BOOK.epub --project-root PROJECT --require-epubcheck
```

Internal checks cover packaging, XML, resource declarations/references, reading order, navigation, supported image formats, and paragraph completeness. Official checker output and compliance status are reported separately. `compliance_verified` is true only after successful EPUBCheck execution. An internally validated ebook may be produced without configured EPUBCheck when it is not required, but report that official compliance was not verified. Never claim full EPUB 3 compliance from internal checks alone.
