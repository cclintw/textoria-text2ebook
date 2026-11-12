# Textoria Runtime and Dependency Setup

Use this reference before running any Textoria task that executes local scripts.

## Principle

Textoria should prepare its runtime during installation or explicit initialization when possible. Do not wait until the middle of a workflow to discover that Python or required packages are missing.

If everything required is already installed, proceed without asking. If anything must be installed, explain what is missing and request user approval before installing, creating a virtual environment, or modifying the local environment.

Ask only one user-facing question at a time. Runtime approval must not be combined with task confirmation, file selection, merge-order confirmation, or structure review.

Present runtime approval with the interactive choice interface defined in [SKILL.md](../SKILL.md#確認與選項介面). Include the actual environment path and missing requirements in the question, with explicit install and decline options. Do not use a tool that prohibits approval requests. If no suitable tool is available, list the choices in text. Wait for an explicitly submitted choice or a clear text reply before installation; a preselected option is not approval.

## 改名後的環境選擇

優先使用已存在的 `.textoria-text2ebook/venv/`；若不存在而 `.textoria-digital-library/venv/` 已就緒，沿用舊環境並執行同一 runtime check。Skill 改名不授權搬移 venv 或重新安裝套件。下文的新目錄適用於首次建立環境。

## Required Runtime

- Python 3.10 or newer.
- Standard website and EPUB tasks do not require SQLite or FTS5. The `sqlite3` module with FTS5 is needed only for explicitly requested database tasks.
- Project-local Textoria virtual environment at `.textoria-text2ebook/venv/`.
- Required Python packages:
  - `charset-normalizer`
  - `beautifulsoup4`
  - `jinja2`
  - `markdown-it-py`
  - `pypinyin`

Optional packages are not installed unless the user enables a feature that needs them:

- `jieba`
- `opencc`
- `pytest`

## Runtime Check

Use this during installation or explicit initialization:

```text
function install_or_initialize_textoria(project_root, config) {
    runtime = call ensure_textoria_runtime(config)

    if runtime.status == "ready" {
        return {
            status: "ready",
            message: "Textoria runtime is ready."
        }
    }

    return ask_runtime_permission(runtime)
}
```

Use this during task execution only after intent, input file selection, merge order, and structure-review blockers have been resolved:

```text
function ensure_textoria_runtime(config) {
    python = call detect_python(">=3.10")

    if python.exists == false {
        installer = call detect_system_installer()

        if installer.exists == false {
            return ask_user_for_python_installation_path()
        }

        return ask_permission_to_install_python(installer)
    }

    venv = call ensure_venv("<project_root>/.textoria-text2ebook/venv", python)

    required_packages = [
        "charset-normalizer",
        "beautifulsoup4",
        "jinja2",
        "markdown-it-py",
        "pypinyin"
    ]

    missing = call check_packages(venv.python, required_packages)

    if missing.count > 0 {
        return ask_permission_to_install_packages(venv, missing)
    }

    return {
        status: "ready",
        python: venv.python,
        venv: venv.path
    }
}
```

If dependency installation is approved and succeeds as part of an already confirmed task, continue the original task automatically. Do not stop after installation unless the user only asked to install, initialize, or check the runtime.

## Permission Messages

When Python is missing:

```text
Textoria needs Python 3.10+ to run local text processing. I could not find a compatible python3. Do you want me to try installing Python with an available system package manager?
```

When packages are missing:

```text
The Textoria runtime is not ready yet. Before running this task, Textoria needs to install required dependencies into this project's Textoria virtual environment:

.textoria-text2ebook/venv/

Missing requirements:

<missing_requirements>

Do you want me to create/update .textoria-text2ebook/venv/ and install them?
```

Do not explain package purposes in the permission message unless the user asks what a package is for.

## Installation Rules

- Do not install Python without explicit user approval.
- Do not install packages without explicit user approval.
- Do not install packages into the system Python. Use `.textoria-text2ebook/venv/` in the current project.
- Do not ask for approval when Python, venv, and packages are already ready. Standard runtime checks do not probe SQLite; use `textoria_runtime_check.py --check-sqlite` only for a database task.
- Record runtime checks in `.textoria-text2ebook/logs/runtime_check.json` when scripts are implemented.

## Package Manager Policy

Prefer project-local Textoria venv package installation:

```text
.textoria-text2ebook/venv/bin/python -m pip install charset-normalizer beautifulsoup4 jinja2 markdown-it-py pypinyin
```

System Python installation is platform-specific and should be conservative:

- macOS: if Homebrew exists, ask before using `brew install python`.
- Linux: ask before using `apt`, `dnf`, `yum`, `pacman`, or `brew`.
- Windows: ask before using `winget` or other package managers.

If no safe installer is detected, ask the user for a Python installation path or ask them to approve a specific installation method.

## Legacy runtimes

For a verified legacy `.textoria/venv/`, use the namespace migration helper described in [workflow.md](workflow.md). Do not simply rename a virtual environment without repairing its activation scripts and absolute launcher paths. Reuse installed packages after a successful migration and runtime check; no dependency reinstall is required for this in-project namespace change.

## EPUB 驗證環境

生成程式本身使用既有 Python 套件。官方 EPUB 格式驗證另需 Java 與完整 EPUBCheck 發行包。優先使用專案 `.textoria-text2ebook/tools/epub-tools.json` 設定的本機工具，不修改系統 Java。缺少工具時先取得安裝授權，再從官方發行來源下載、比對雜湊並保存授權文件。工具已就緒或已有本次安裝授權時，直接接續任務，不重複詢問。執行方式與驗證範圍見 [epub.md](epub.md)。
