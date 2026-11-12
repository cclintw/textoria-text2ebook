# Textoria Text2Ebook

Developer repository for the `textoria-text2ebook` Codex Skill. It turns text into a local HTTP reader, a static reader that also works with `file://`, and EPUB ebooks.

General usage documentation is maintained in the [Traditional Chinese guide](https://cclin.cc/textoria-text2ebook.md). This README covers the implementation, development setup, and maintenance contracts.

- Author: Chance Chun-Cheng Lin (cclintw)
- Type: Codex Skill
- Version: 1.0.1
- Runtime: Python 3.10 or later; Codex for the guided workflow
- License: GNU GPL v3 or later

## Architecture

The workflow preserves original sources, prepares editable full text, and records separate approvals for chapters, basic metadata, and optional materials. Confirmed content is projected into one canonical `archive.json` used by website, browser-search, and EPUB builders.

Website and EPUB tasks do not create or depend on SQLite. Database/FTS5 scripts remain available only for separately confirmed technical requests. Source text, book interface language, and the accepted Chinese filenames/metadata roles are not translated by English documentation.

```text
.agents/skills/textoria-text2ebook/
  SKILL.md       Agent workflow and authorization boundaries
  agents/        Codex interface metadata
  scripts/       Processing, build, runtime, and output validation commands
  references/    Focused operational and data-contract documentation
  themes/        Static reader templates/assets and EPUB styles
  LICENSE        Full GPL license
```

The root `.gitignore` allows only this Skill directory, `README.md`, and `.gitignore`. Generated books, environments, deployment state, credentials, local policies, and the local Traditional Chinese Markdown/HTML guides are excluded. Development test scripts are not distributed or retained in a separate `tests/` directory.

## Development setup

Clone the repository with an account that has access, and use a project-local environment:

```sh
git clone https://github.com/cclintw/textoria-text2ebook.git
cd textoria-text2ebook
python3 -m venv .textoria-text2ebook/venv
.textoria-text2ebook/venv/bin/python -m pip install charset-normalizer beautifulsoup4 jinja2 markdown-it-py pypinyin
.textoria-text2ebook/venv/bin/python .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py
```

The commands above are for a developer deliberately setting up the checkout. During guided Skill execution, obtain explicit approval before installing missing dependencies. Use an existing compatible environment when available. Java and the complete EPUBCheck distribution are required only for official EPUBCheck verification, not for internal EPUB validation.

### Install the Skill through Codex

Open the target working project in Codex and submit:

```text
$skill-installer --repo cclintw/textoria-text2ebook --path .agents/skills/textoria-text2ebook --dest .agents/skills
```

Start using `$textoria-text2ebook` on the next turn. Private repository access is required.

### Install manually

Open the [repository](https://github.com/cclintw/textoria-text2ebook), choose **Code → Download ZIP**, and extract it. Copy the complete `.agents/skills/textoria-text2ebook/` directory into the target project's `.agents/skills/`, including scripts, references, themes, interface metadata, and license. Enable hidden-file visibility if necessary. Compare an existing destination before replacing it.

## Interfaces and maintenance contracts

- The CLI entry is `scripts/textoria_build.py`. It accepts one positional source or `--output` for continuation. Accepted body formats are TXT, Markdown, HTML/HTM, and CSV with an explicit text column; metadata XLSX is a separate input path.
- New books are saved under `textoria-text2ebook/collections/<slug>/`. Keep the source copies, editable text, basic metadata, materials, hashes, and review state. Do not create duplicate authoritative text files.
- Chapter, metadata, and material decisions are ordered and version-bound. A review token is technical state, not user approval. Do not automate confirmation just to make a build proceed.
- Use `rebuild_site` for website-only work, `build_epub` for EPUB-only work, and `build_fulltext_archive` for both. The builders enforce pending review checkpoints.
- Keep website changes in `themes/default/` and EPUB styles in `themes/epub/`. Preserve relative assets, classic-script search loading, routes, paragraph anchors, and sidebar/search state.
- Optional cover/title/copyright materials are rendered in EPUB; the current static website does not render these front-matter pages.
- Local generation does not authorize hosting. Extra operations require explicit scope confirmation, and a completed website has a final optional Sites publication choice. Publish only after the required decision.

## Verification

Use the actual collection path in place of `COLLECTION_ROOT` and the actual EPUB path in place of `BOOK.epub`:

```text
.textoria-text2ebook/venv/bin/python .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT
.textoria-text2ebook/venv/bin/python .agents/skills/textoria-text2ebook/scripts/textoria_validate_epub.py BOOK.epub --project-root .
```

The website validator checks the canonical archive, expected chapter pages, relative references, search-index IDs/text, loading order, and result anchors. Internal EPUB checks cover packaging, XML, resources, navigation, reading order, and paragraph completeness. Add `--require-epubcheck` to the EPUB validator only with a configured official checker when compliance verification is required. Report the validation scope accurately.

For specifically authorized database work, `textoria_runtime_check.py --check-sqlite` and `textoria_validate.py COLLECTION_ROOT --check-sqlite` add the optional FTS5/database checks. Normal builds and validation neither require nor update existing databases.

## Technical documentation

- [Skill instructions](.agents/skills/textoria-text2ebook/SKILL.md)
- [Workflow and command checkpoints](.agents/skills/textoria-text2ebook/references/workflow.md)
- [Input resolution](.agents/skills/textoria-text2ebook/references/input-resolution.md)
- [Encoding and text preparation](.agents/skills/textoria-text2ebook/references/text-cleaning.md)
- [Saved files and state](.agents/skills/textoria-text2ebook/references/file-contracts.md)
- [Canonical schema and optional database](.agents/skills/textoria-text2ebook/references/schema.md)
- [Metadata](.agents/skills/textoria-text2ebook/references/metadata.md)
- [Optional EPUB materials](.agents/skills/textoria-text2ebook/references/materials.md)
- [Reader theme](.agents/skills/textoria-text2ebook/references/theme-system.md)
- [EPUB generation and validation](.agents/skills/textoria-text2ebook/references/epub.md)
- [Runtime setup](.agents/skills/textoria-text2ebook/references/runtime.md)
- [Task boundaries](.agents/skills/textoria-text2ebook/references/intent-policy.md)
- [Collection deletion](.agents/skills/textoria-text2ebook/references/delete-policy.md)

## Changelog

### 1.0.1 — 2026-10-24 17:08 (UTC+8)

- Preserve expanded TOC branches across chapter navigation and highlight the current reading section.
- Update theme rules: use the bundled default template for every collection, remove the project-level theme override, and maintain developer UI changes in the default template.
- Standardize builds to include both the website and SQLite/FTS5 database, without custom-UI preservation confirmation, and open the homepage by default.

## Author and citation

Developed by **Chance Chun-Cheng Lin** ([cclintw](https://github.com/cclintw)).

Suggested citation:

> Chance Chun-Cheng Lin. *textoria-text2ebook: Textoria Text2Ebook*. Software.

Include the version or Git commit used when documenting research methods.

## Copyright and license

Copyright © 2026 Chance Chun-Cheng Lin.

Released under the [GNU General Public License, version 3 or any later version](.agents/skills/textoria-text2ebook/LICENSE) (`GPL-3.0-or-later`). Source texts, third-party software, and supplied materials retain their respective rights and licenses.

## Contributing and issue reports

Describe the affected processing stage, input format, reproducible behavior, relevant error messages, and runtime. Remove private source text and credentials from diagnostics. Keep shared changes in the Skill instead of patching only a generated book. See the linked technical contracts before changing data or approval behavior.
