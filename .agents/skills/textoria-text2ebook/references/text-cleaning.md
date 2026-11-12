# Encoding, extraction, and text cleaning

Read this before conversion, extraction, cleaning, or re-cleaning. The current CLI uses the `cc_text_cleaner` implementation; it does not offer a selectable conservative cleaning profile.

## Source preservation and persistence

Inspect each actual input and preserve its source copy for book production. A new book's editable text is `content/全文.md`; reuse `clean/cleaned_text.md` only for an existing legacy collection. See [file-contracts.md](file-contracts.md).

Ordinary book builds keep UTF-8 preparation and extracted Markdown in memory. An explicit conversion task writes `prepared/<stem>.utf8.<ext>`; an explicit extraction task writes `intermediate/plain_text.md`. Do not add duplicate conversion/extraction report files to ordinary builds. Stage details are stored in `state.json`.

Existing manually edited text is not re-cleaned automatically. If changed source bytes or options would overwrite it, request an explicit re-clean decision first. Cleaning completion does not confirm chapters.

## Encoding behavior

`textoria_utf8_converter.py` tries UTF-8 BOM/UTF-8, then Big5-HKSCS, Big5, Shift JIS, and GB2312. If those strict probes fail, it consults `charset-normalizer`, then falls back to Big5. Big5 decoding prefers HKSCS. Strict decoding success is not a guarantee that an ambiguous encoding was semantically identified correctly; inspect questionable text rather than claiming certainty from a successful probe.

Decoded text normalizes CRLF/CR to LF, removes BOM characters and specified controls, replaces the Unicode replacement character with `■`, and applies NFKC. Do not claim that private-use characters or every kind of mojibake are detected or restored. The current implementation has no automatic original-glyph reconstruction.

NFKC affects compatibility characters and punctuation even in lines later protected from prose conversion. Preserve original files so users can compare the changed representation.

## Extraction by format

| Format | Implemented extraction |
|---|---|
| TXT / Markdown | Use the prepared text as the working stream. |
| HTML / HTM | Remove script/style/head/svg/nav elements and comments; extract headings, paragraphs, list items, quotations, tables, and image references. |
| CSV | Require `--text-column` naming an existing column; join nonempty values in row order with blank lines. |

HTML extraction emits Markdown headings, simple list/quotation syntax, tables with a separator after the first row, and image references. Inline text is flattened; original link targets, rich styling, arbitrary nested markup, and detailed typography are not guaranteed to survive. HTML extraction is not a promise of full-fidelity HTML conversion or comprehensive sanitization of every possible URL.

Metadata spreadsheets are handled separately; CSV body columns are not metadata imports. XML/XHTML, PDF, DOCX, and image OCR are not supported body inputs.

## Default cleaning behavior

`textoria_clean_text.py` normalizes text and converts selected vertical punctuation:

| Input | Output |
|---|---|
| `﹃` / `﹄` | `『` / `』` |
| `﹁` / `﹂` | `「` / `」` |
| `︿` / `﹀` | `〈` / `〉` |
| `︽` / `︾` | `《` / `》` |

For prose lines, it converts half-width punctuation through `HALFWIDTH_PUNCT`, including commas, periods, colons, parentheses, brackets, slashes, and other ASCII punctuation. Straight double quotes alternate opening/closing corner quotes within a line, and curly double quotes become corner quotes. Half-width spaces/tabs are removed except for a single space between ASCII letters/digits. Trailing whitespace is stripped, excess blank lines are collapsed, and the result ends with one newline.

Fenced code, Markdown heading lines, pipe-table rows, footnote definitions, and lines containing Markdown image syntax are protected from the prose punctuation/space conversion. Earlier normalization still applies. Do not describe this protection as a byte-preserving Markdown round trip.

The implementation does not automatically convert between simplified/traditional scripts, remove footnotes or page furniture, repair historical punctuation, or recognize every literal marker as corruption. Do not silently add these editorial transformations.

## Review and recorded facts

The cleaning stage records the selected profile, detected encoding, normalization, rules, character/line statistics, and marker counts. These are processing diagnostics, not evidence that every character is correct. Present a meaningful issue when it affects the next decision, and retain the source for comparison. Continue with [chapter review](workflow.md#inspect-and-review-chapters), not directly to final generation.
