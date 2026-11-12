# Collection deletion and reset

Read this when a user asks to delete, clear, reset, or start over with a book collection. This policy concerns collection data, not ordinary source-code maintenance.

## Resolve the exact target

Discover the actual collections and resolve a single target. A request to start over normally concerns generated data for that collection, not original sources, other books, the project root, Skill files, or the runtime. Never act on a broad or ambiguous path.

The project-level `textoria-text2ebook/` directory is not a collection. Preserve the root registry and other collections, removing only the selected entry after a confirmed collection deletion. Continue legacy collections at their actual namespace rather than inferring a new target.

## Preserve irreplaceable content

Before proposing whole-collection deletion, inspect whether these files have other usable copies:

- Original external sources and saved `source/` copies.
- Editable `content/全文.md` or legacy `clean/cleaned_text.md`.
- `metadata.json` and uploaded metadata originals.
- Supplied `materials/` and their replacement history.

These can be the only copies of manual or supplied work. Do not treat them as disposable website artifacts. If the requested scope is only generated outputs, preserve them. If the only original is inside the target collection, relocate it to a safe project source folder before deleting generated data, and state the retained location in the plan. Deleting original sources requires separate explicit authorization.

Do not create an automatic backup unless requested. State that no automatic backup will be created before destructive confirmation. A Skill rename or update never authorizes deleting sources or either namespace.

## Confirm the concrete plan

Show the collection name and full path, exactly which files/folders will be removed, which sources and manual assets remain, and the backup behavior. Ask for the explicit phrase `Delete <collection_path>`, substituting the actual full path in the prompt. Do not accept a vague yes as confirmation of an unbounded target.

Execute only the displayed and confirmed plan. For whole-collection deletion, verify the path is the selected collection directory, preserve any required source copies, remove that directory, and update the appropriate registry entry. Do not delete the project root, `.agents/skills/`, `.textoria-text2ebook/`, another collection, or source files outside the confirmed scope.
