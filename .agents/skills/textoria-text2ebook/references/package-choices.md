# Textoria Package Choices

Use conservative dependencies. The first-version archive must be easy to run locally and suitable for GitHub installation.

## Required Runtime

- Python 3.10 or newer.
- SQLite with FTS5 is optional and needed only for explicitly requested database tasks.
- Project-local Textoria virtual environment at `.textoria-text2ebook/venv/`.
- Required Python packages:
  - `charset-normalizer`
  - `beautifulsoup4`
  - `jinja2`
  - `markdown-it-py`
  - `pypinyin`

Run the checks in [runtime.md](runtime.md) before executing local scripts. If a required component is missing, ask the user for approval before installation. If all components are present, proceed without asking.

## Core Python Standard Library

Use these whenever possible:

- `argparse` for command-line interfaces.
- `csv` for CSV export/import.
- `datetime` for build timestamps.
- `html.parser` for basic HTML extraction when sufficient.
- `json` for JSON outputs.
- `logging` for build logs.
- `pathlib` for filesystem paths.
- `re` for rule-based structure detection.
- `shutil` for safe copying.
- `sqlite3` only for explicitly requested database and FTS5 tasks.
- `unicodedata` for Unicode normalization.

## Required Third-Party Packages

These are required for Textoria v1:

- `charset-normalizer`: encoding detection when standard-library decoding is insufficient.
- `beautifulsoup4`: robust HTML extraction.
- `jinja2`: static HTML templates.
- `markdown-it-py`: Markdown parsing when heading extraction is not enough.
- `pypinyin`: generate English pinyin slugs from Chinese collection names.

Install them only inside the current project's `.textoria-text2ebook/venv/`; do not install into system Python.

## Optional Later Packages

Do not require these in the first-version core workflow:

- `jieba`: optional Chinese tokenization.
- `opencc`: optional simplified/traditional conversion.
- `pytest`: optional tests for scripts and workflow validation.

## Frontend Policy

Use static HTML, CSS, and JavaScript by default. Do not require a backend server. Do not introduce React, Vue, Svelte, Next.js, Vite, or server frameworks unless the user explicitly asks to build a separate application beyond Textoria v1 static output.

The static site loads `site/data/search_index.js` as a classic script, supporting HTTP and direct `file://` access without fetching JSON. The index is generated from `archive.json`; standard website and EPUB tasks do not create or use SQLite.

