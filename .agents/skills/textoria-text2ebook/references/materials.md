# Optional EPUB materials

## Ask after metadata confirmation

Only after chapter and metadata approval, list optional materials and offer Provide/Skip choices. State that materials can be attached or supplied as local file paths; text-only question tools must not request uploads.

| Material | Accepted filenames | Requirements |
|---|---|---|
| Cover | `封面.jpg`, `封面.jpeg`, `封面.png` | RGB-compatible JPEG/PNG; recommended 1600 × 2400 pixels |
| Title page | `書名頁.txt`, `書名頁.md` | Readable nonempty text |
| Copyright page | `版權頁.txt`, `版權頁.md` | Readable nonempty text |

These filenames are exact program contracts, with case-insensitive extensions. Resolve similar names or multiple candidates instead of guessing. A material must not be empty or exceed the program's 32 MiB limit. Missing optional items are omitted; do not generate covers, blank pages, or publication text. Accepted materials currently appear in EPUB, not the static reader pages.

Existing assets remain available even if not attached again. Show saved choices for reuse or replacement. Ask the user to indicate when supplying materials is complete; choosing Provide alone does not mean receipt is complete.

## Receive and preserve

Use the verified interpreter for `PYTHON` and actual paths for the other symbolic arguments:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_materials
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --material TITLEPAGE_PATH --material COPYRIGHT_PATH
```

Pass only actually supplied files; omit unused arguments. The command validates the entire batch before saving copies under `materials/`. Preserve original bytes, formats, names, source/saved paths, SHA-256, and inspections. A same-name changed file gets a versioned saved name rather than overwriting a copy.

`receive_materials` returns files, missing items, checks, links, and `materials_token`; exit code 2 normally means awaiting the completion decision. Report only checks actually performed. Attachment temporary paths are not permanent storage.

## Confirm or skip

After explicit completion and successful inspection:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_materials --materials-token MATERIALS_TOKEN
```

Use the current token, bound to the saved files and metadata. If the user has clearly said to finish with the supplied batch, do not add another equivalent question. If completion is unclear, keep it pending. No supplied files plus a completion statement is not an implicit skip.

On an explicit skip:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task skip_materials
```

A first-time skip creates no empty material folder. On an existing collection it means no additions and retains saved choices; it does not remove pages or assets. Partial receipt with explicit completion omits other missing items. Confirmation saves the selection but does not generate an EPUB by itself.

## Replacements and conflicts

A changed choice requires an explicit replacement instruction, for example:

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --replace-material cover
```

Other replacement keys are `titlepage` and `copyright`. Preserve old copies and selection history.

The title-page H1 and explicitly labeled bibliographic lines are compared with confirmed metadata, ignoring fenced examples. The current line matcher uses the program's Chinese field labels. Display any discrepancy without rewriting the source or metadata. Resolve it, or obtain an explicit instruction to retain the difference before using `--accept-material-conflicts` with current confirmation. Skipping cannot bypass unresolved conflicts.

Saved file loss/change or changed metadata invalidates the bound selection and blocks downstream output replacement until resolved.

## Inspection limits

PNG inspection verifies signature, chunk CRC, dimensions, RGB/RGBA color type, decompressed rows, and filters. JPEG inspection checks the container and frame dimensions/channels; it does not itself fully decode every pixel. When available, macOS `sips` additionally checks format, dimensions, and color space. Report the actual verification scope and never claim full image decoding or store submission compliance without the corresponding checks.

Preserve image proportions; do not crop, upscale, convert, or replace a supplied cover automatically. Recommended dimensions are not the only valid EPUB dimensions. Do not claim current store-specific requirements from this recommendation.

Text materials support UTF-8, BOM-marked UTF-16, and other reliably decoded encodings. Retain original bytes and extension; UTF-8 layout conversion happens during EPUB generation. Reject unreadable, empty, or control-corrupted text.
