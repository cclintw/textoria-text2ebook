# Runtime and dependencies

Read this before executing local Textoria processing scripts.

## Requirements

- Python 3.10 or newer.
- A project-local environment, normally `.textoria-text2ebook/venv/`.
- Python packages: `charset-normalizer`, `beautifulsoup4`, `jinja2`, `markdown-it-py`, and `pypinyin`.
- Java and the complete EPUBCheck distribution only for official EPUBCheck validation.

Standard website and EPUB tasks do not require SQLite or FTS5. Do not install optional tokenization, script-conversion, or testing packages for ordinary builds.

Prefer an existing compatible `.textoria-text2ebook/venv/`. If absent, a verified `.textoria-digital-library/venv/` may be reused in place. Renaming the Skill does not authorize moving or recreating an environment. A legacy `.textoria/venv/` requires the explicit migration workflow; do not simply rename it because launchers contain absolute paths.

## Check before processing

Replace `PYTHON` with the selected environment executable and set `SKILL_DIR` to the absolute path of the directory containing the loaded `SKILL.md`.

```text
PYTHON "$SKILL_DIR/scripts/textoria_runtime_check.py"
```

A ready environment needs no further permission. The check reports Python and package availability; it does not create an environment, install packages, or write a separate runtime log. Only for a specifically authorized database task, add `--check-sqlite` to require SQLite FTS5.

## Missing requirements

Before installing Python, creating an environment, or installing packages, display the actual missing requirements and destination, then request explicit approval using the [interactive choices](../SKILL.md#interactive-choices). Ask one question; do not combine runtime approval with chapter or metadata review. Do not use a question tool that prohibits approval requests.

If approval is given, create the environment with the confirmed Python executable and install packages there, never into system Python. For the default path:

```text
python3 -m venv .textoria-text2ebook/venv
.textoria-text2ebook/venv/bin/python -m pip install charset-normalizer beautifulsoup4 jinja2 markdown-it-py pypinyin
```

Use these commands only after authorization. When Python itself is missing, identify a suitable installer or ask for an available Python path; do not install it automatically. Do not repeatedly ask for permission already given for the same installation. After successful setup, resume the original task automatically unless setup alone was requested.

## EPUBCheck tools

Prefer the actual paths configured in `.textoria-text2ebook/tools/epub-tools.json`. Do not modify system Java settings. If installation is needed, request permission, obtain the complete official EPUBCheck release and dependencies, verify the downloaded artifact against its official checksum when available, and retain license files in the project tool directory.

Use already available or already authorized tools without another equivalent approval request. See [epub.md](epub.md) for resolution order, commands, and validation claims.
