# Input and collection resolution

## Classify the request and files

Distinguish discussion, Skill maintenance, and actual book production. A capability question does not authorize writing collection data. For book tasks, inspect `textoria-text2ebook/registry.json` and, when present, `textoria-digital-library/registry.json`. Reuse the identified collection. If several books could match, resolve the target rather than merging them.

| Input role | Supported input |
|---|---|
| Body text | TXT, Markdown, HTML/HTM, or CSV with an explicit body-text column |
| Basic metadata | Conversation, CSV, XLSX, JSON, TXT, or Markdown |
| Cover | JPEG or PNG with the accepted material filename |
| Title/copyright page | TXT or Markdown with the accepted material filename |

Metadata and front-matter attachments never join the body-text merge. Their presence does not skip the ordered review checkpoints.

Suggest a temporary collection name from the filename or opening heading; ask about identity only when ambiguous. Confirm the final title during metadata review. Slugs are technical lowercase pinyin/Latin strings with hyphens and collision suffixes, not user fields. A metadata title change does not rename the folder.

## Multiple body files

Display and confirm merge order before combining files. Use the user's explicit order first, then numbered filenames, volume/chapter markers, and natural sorting as evidence. Preserve each source and its inspection, ordering, and boundary records, while keeping one editable full-text file. File boundaries do not automatically define document or chapter levels.

The current CLI accepts one positional source, not a list. Do not invent a multi-file flag. Resolve and preserve multiple inputs before constructing the single working source used by the CLI; maintain provenance for every original rather than presenting a merged file as the only source.

## Structural review

Explicit Markdown or extracted HTML headings give strong evidence; repeated plain-text markers may also identify chapters. Confidence describes the evidence only. Every new chapter version still requires the review and heading-edit guidance in [SKILL.md](../SKILL.md#1-prepare-text-and-review-chapters).

Link both the editable full text and derived outline, show the inferred hierarchy, and wait for explicit confirmation. Apply changes to working headings, regenerate the outline, and review the new version. Do not modify the original or supply a temporary link while asking the user to edit a different file.
