# Textoria Text2Ebook

Turn text into a web ebook with a table of contents and full-text search, and generate EPUB ebooks.

- Author: Chance Chun-Cheng Lin (cclintw)
- Chinese name: Textoria 電子書製作工具
- Type: Codex Skill
- Version: 1.0.1
- Requirements: Codex, Python 3.10 or later
- License: GNU GPL v3 or later

## Description

Textoria Text2Ebook (`textoria-text2ebook`) is a Codex Skill for creating web and EPUB ebooks from historical documents and general texts. It prepares text, identifies chapters, and confirms basic book metadata and optional materials before generating the requested outputs. Original files and editable working files are preserved for review and rebuilding.

The repository name is `textoria-text2ebook`; the Skill entrypoint is `.agents/skills/textoria-text2ebook/SKILL.md`.

## Features

- **Text preparation:** Normalize supported text to UTF-8 and retain processing records and source copies.
- **Chapter review:** Save editable full-text Markdown and a separate chapter outline; require confirmation before continuing.
- **Book metadata:** Confirm the title and supported contributor roles, with manual edits or CSV, XLSX, JSON, TXT, and Markdown input.
- **Optional materials:** Preserve supplied JPEG/PNG covers and TXT/Markdown title and copyright pages; omit materials that are skipped.
- **Web reading and search:** Navigate chapters and search the entire book from the reader, with links to matching paragraphs.
- **EPUB output:** Generate ebooks from confirmed content, metadata, and materials, with internal checks and optional EPUBCheck validation.
- **Rebuilding:** Retain structured data, settings, and review states to continue work without losing manual edits.

### Text cleaning

The default `cc_text_cleaner` workflow applies these transformations:

- **Encoding and characters:** Normalize text to UTF-8 in memory, remove BOM characters, standardize line endings, and apply Unicode NFKC normalization to compatibility characters. Remove specified control characters and mark undecodable bytes and replacement characters (`�`) with `■`.
- **Punctuation:** Convert selected vertical punctuation to horizontal forms, such as `﹁﹂` to `「」`. Map half-width punctuation in prose to full-width forms, such as `,` to `，` and `.` to `。`, and convert straight and curly double quotes to `「」`.
- **Whitespace:** Remove half-width spaces and tabs in prose, retaining single spaces between ASCII letters or digits. Trim trailing whitespace, collapse three or more consecutive line breaks to two, and trim whitespace at the start and end of the text.
- **Markdown handling:** Skip prose whitespace and punctuation conversion on heading lines, table rows, footnote-definition lines, and lines containing image links. Unicode normalization and selected vertical-punctuation conversion still apply to these lines.
- **HTML extraction:** Remove `script`, `style`, `head`, `svg`, `nav`, and comments, and extract headings, paragraphs, lists, quotations, tables, and image links as Markdown.

NFKC normalization and punctuation and whitespace conversion alter textual representation. Originals remain at their source paths; cleaned text is saved as `content/全文.md`. The `state.json` file records processing rules, character and line counts, and the latest stage status. The default workflow does not convert simplified and traditional Chinese or automatically delete notes, page numbers, headers, or footers; punctuation and whitespace within them are still processed.

## How it works

1. **Provide text.** Upload a supported file or supply its local path; confirm merge order for multiple files.
2. **Confirm chapters.** Review the editable full text and separate chapter outline, request corrections, and confirm the structure.
3. **Confirm metadata.** Review the title and identified contributors; edit or import book metadata as needed.
4. **Choose materials.** Supply a cover, title page, or copyright page, or explicitly skip these optional materials.
5. **Generate and review.** Open the web reader and download the EPUB when generated. Retained working files support corrections and rebuilding.

```text
Use $textoria-text2ebook to turn the uploaded text into a web ebook and an EPUB ebook.
```

## Installation

### Method 1: Install through Codex

Open the target working project in the Codex app and send this instruction. Access to the private [GitHub repository](https://github.com/cclintw/textoria-text2ebook) is required.

```text
$skill-installer --repo cclintw/textoria-text2ebook --path .agents/skills/textoria-text2ebook --dest .agents/skills
```

After installation, start using `$textoria-text2ebook` on your next turn.

### Method 2: Download and install manually

1. Sign in to GitHub with access to the [repository](https://github.com/cclintw/textoria-text2ebook), select **Code → Download ZIP**, and extract the archive. Locate `.agents/skills/textoria-text2ebook/`; enable hidden-file visibility if needed.
2. Create `.agents/skills/` in the target working project if it does not exist.
3. Copy the entire `textoria-text2ebook` folder, including its bundled files and subfolders, into that directory. The entrypoint should be:

```text
<working-project>/.agents/skills/textoria-text2ebook/SKILL.md
```

When working directly in this source project, the Skill is already in place.

### Requirements

- Codex with local Skill support.
- Python 3.10 or newer. SQLite/FTS5 is required only for explicitly requested database tasks.
- Python packages: `charset-normalizer`, `beautifulsoup4`, `jinja2`, `markdown-it-py`, and `pypinyin`.
- Java and EPUBCheck for official EPUB validation; these are separate from the Python runtime.

Codex checks the runtime before processing and requests approval before installing missing dependencies in `.textoria-text2ebook/venv/`. Existing compatible environments can be reused.

## Frequently asked questions

### Which input formats are supported?

TXT, Markdown, HTML/HTM, and CSV with a specified text column. Convert PDF, DOCX, and images to a supported text format and check the conversion before importing.

### Where are the results saved?

Each book is stored under `textoria-text2ebook/collections/<slug>/`. It retains source copies, `content/全文.md`, `content/章節目錄.md`, `metadata.json`, supplied materials, structured data, settings, and review states. The web reader is generated in `site/` and EPUB files in `export/`. `textoria-text2ebook/registry.json` records the books. Legacy books keep their existing working paths unless migration is explicitly requested.

### Can the website be opened directly as an HTML file?

Yes. Open `site/index.html` directly in a browser; the search index loads through a relative JavaScript file and supports `file://` as well as HTTP. Keep the complete `site/` folder together. The website can also use the local HTTP URL provided by Codex or be deployed to static hosting.

### Are a cover and publication details required?

Only the book title is required for basic metadata. Covers, title pages, and copyright pages are optional. Skipped materials are omitted; the Skill does not invent missing publication details or generate these pages automatically.

### What does EPUB validation cover?

Internal checks cover packaging, XML, resources, reading order, navigation, and paragraph completeness. Official EPUBCheck validation requires Java and EPUBCheck. A successful internal check alone does not establish EPUBCheck compliance; the actual validation status is reported with the output.

### Does the Skill include entity annotation or an EPUB import reader?

Semantic entity annotation, custom research metadata extraction, and EPUB/KPUB import reading are outside the default ebook workflow. Website, search-index and EPUB generation use the canonical archive directly and do not create SQLite databases. Explicit database tasks and data exports remain separate technical capabilities.

## Documentation

- [Skill instructions](.agents/skills/textoria-text2ebook/SKILL.md)
- [Workflow](.agents/skills/textoria-text2ebook/references/workflow.md)
- [Files and saved state](.agents/skills/textoria-text2ebook/references/file-contracts.md)
- [Metadata](.agents/skills/textoria-text2ebook/references/metadata.md)
- [Optional materials](.agents/skills/textoria-text2ebook/references/materials.md)
- [EPUB generation and validation](.agents/skills/textoria-text2ebook/references/epub.md)
- [Runtime setup](.agents/skills/textoria-text2ebook/references/runtime.md)

Websites use the bundled `themes/default/` theme. Changes to content, structure, or templates require rebuilding the affected outputs.

## Changelog

### 1.0.1 — 2026-10-24 17:08 (UTC+8)

- Preserve expanded TOC branches across chapter navigation and highlight the current reading section.
- Update theme rules: use the bundled default template for every collection, remove the project-level theme override, and maintain developer UI changes in the default template.
- Standardize builds to include both the website and SQLite/FTS5 database, without custom-UI preservation confirmation, and open the homepage by default.

## Author and citation

Developed by **Chance Chun-Cheng Lin** ([cclintw](https://github.com/cclintw)).

Suggested citation:

> Chance Chun-Cheng Lin. *textoria-text2ebook: Textoria 電子書製作工具*. Software.

Include the version or Git commit used when documenting research methods.

## Copyright and license

Copyright © 2026 Chance Chun-Cheng Lin.

Released under the [GNU General Public License, version 3 or any later version](.agents/skills/textoria-text2ebook/LICENSE) (`GPL-3.0-or-later`). Source texts, third-party software, and other materials retain their respective rights and licenses.

## Support

Bug reports should include the input format, reproduction steps, relevant error messages, and runtime details. Remove private source text before sharing diagnostic information.
