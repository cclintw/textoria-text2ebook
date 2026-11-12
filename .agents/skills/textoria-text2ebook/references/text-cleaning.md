# Textoria Encoding and Text Cleaning

Use this reference before implementing or running `convert_encoding`, `extract_plain_text`, `clean_text`, or `reclean_text`.

The rules are adapted from the CC UTF-8 Converter and CC Text Cleaner plugins, but Textoria does not inherit WordPress upload handling, public forms, size limits, temporary-download behavior, or `.xml/.xhtml` support.

## 製書保存與相容腳本

來源保存、全文及章節審查依 [file-contracts.md](file-contracts.md) 與 [workflow.md](workflow.md)。新書唯一人工作業檔使用 `content/全文.md`；既有 `clean/cleaned_text.md` 沿用原位。下文的舊路徑範例適用於已有該工作檔的書籍；實際寫入由 `working_text_path` 決定。同一本書不得維持兩個不同的可編輯全文。清理完成不等於章節已確認。

## Minimal persistence

Convert each inspected source to canonical UTF-8 before extraction. During cleaning/full builds, keep UTF-8 and extracted Markdown in memory. 低階清理程式產生的結果與報告依現有相容路徑保存；製書流程另外依檔案契約保存來源與必需的章節審查目錄，不能以精簡輸出為由省略。

Write `prepared/<stem>.utf8.<ext>` only for an explicit conversion deliverable and `intermediate/plain_text.md` only for an explicit extraction deliverable. 明確轉檔／擷取任務不額外產生製書來源副本；清理及後續製書階段將來源保存於 `source/`，不另寫分散的 conversion/extraction/cleaning 報告檔。

## Encoding Conversion

```text
function convert_encoding(file, inspection, workspace, config) {
    raw = call read_bytes(file)

    if config.encoding.override exists {
        encoding = config.encoding.override
    } else {
        encoding = call detect_encoding(raw)
    }

    text = call decode_to_utf8(raw, encoding)
    text = call replace_invalid_unicode(text)
    text = call normalize_unicode(text, form = "NFKC")
    text = call normalize_line_endings(text)

    persist UTF-8 only when conversion itself is requested
    store conversion facts in state.json

    return canonical_utf8_text
}
```

Encoding detection should try:

```text
UTF-8
BIG5
SJIS
GB2312
fallback BIG5
```

Use `charset-normalizer` as supporting evidence, not as the only authority. Record the detected encoding, confidence if available, and fallback path in `state.json.source`.

### BIG5 Safe Decode

For BIG5, prefer BIG5-HKSCS, then BIG5. Handle bytes safely:

- Preserve ASCII bytes.
- Preserve newline.
- Convert valid BIG5 pairs.
- Convert full-width space byte pair `A1 40` to ideographic space or remove it according to the selected cleanup profile.
- Replace invalid bytes with `■`.
- If a converted code point falls in the Unicode Private Use Area, record it as a visible marker such as `[U+E000]` or `[A140]`, instead of silently dropping it.

### Invalid Characters

Replace these with `■` or visible code markers:

- Unicode replacement character `�`.
- Invalid byte sequences.
- Unsupported control bytes.
- Repeated garble markers such as excessive `??`.

## Extraction to Markdown

Textoria extracts supported source formats into an in-memory Markdown stream. Save `intermediate/plain_text.md` only when extraction itself is requested.

```text
function extract_plain_text(prepared_file, format, workspace, config) {
    if format == "txt" {
        preserve text content and paragraph boundaries
        output Markdown-compatible plain text
    }

    if format == "md" {
        preserve Markdown headings, tables, lists, footnotes, and image links where possible
    }

    if format == "html" {
        remove unsafe markup
        convert h1-h6 to Markdown headings
        convert p to paragraphs
        convert table to Markdown table
        convert img src/alt to Markdown image links
        preserve useful links when possible
    }

    if format == "csv" {
        require config.input.text_column
        optionally read config.input.title_column and metadata columns
        emit Markdown text in source row order
    }

    persist intermediate/plain_text.md only for an explicit extraction deliverable
    store the extraction summary in state.json
    return plain_text_md
}
```

## Cleanup Profiles

Textoria has two named profiles.

### `conservative`

Use when the user wants minimal editorial intervention:

- Remove UTF-8 BOM.
- Normalize line endings to `\n`.
- Remove control characters except tab and newline.
- Trim trailing whitespace.
- Collapse three or more blank lines to two blank lines.
- Preserve punctuation.
- Preserve paragraph boundaries.
- Use Unicode normalization only if enabled.

### `cc_text_cleaner`

Default profile for Chinese historical text preparation:

- Normalize Unicode with `NFKC`.
- Normalize line endings to `\n`.
- Remove control characters except line breaks.
- Remove half-width spaces and tabs except spaces between ASCII letters or digits.
- Replace invalid or unsupported characters with `■`.
- Replace Unicode replacement character `�` with `■`.
- Convert selected vertical punctuation to horizontal punctuation:
  - `﹃` -> `『`
  - `﹄` -> `』`
  - `﹁` -> `「`
  - `﹂` -> `」`
  - `︿` -> `〈`
  - `﹀` -> `〉`
  - `︽` -> `《`
  - `︾` -> `》`
- Convert half-width punctuation to full-width punctuation in prose lines.
- Convert half-width double quotes and curly double quotes (`“”`) to `「` and `」`.
- Preserve Markdown syntax on heading lines, table rows, footnote definitions, and image links.
- Remove unsafe or unwanted markup: `script`, `style`, `head`, `svg`, comments, XML declarations, and doctype declarations.
- Collapse excessive blank lines.

## Half-Width Punctuation Map

Use this map for prose lines in the `cc_text_cleaner` profile:

```text
! -> ！
# -> ＃
$ -> ＄
% -> ％
& -> ＆
' -> ’
( -> （
) -> ）
* -> ＊
+ -> ＋
, -> ，
- -> －
. -> 。
/ -> ／
: -> ：
; -> ；
< -> ＜
= -> ＝
> -> ＞
? -> ？
@ -> ＠
[ -> ［
\ -> ＼
] -> ］
^ -> ＾
_ -> ＿
` -> ｀
{ -> ｛
| -> ｜
} -> ｝
~ -> ～
```

Do not apply this map to Markdown heading markers, Markdown table delimiters, footnote definitions, or image links.

## HTML Cleanup

For HTML input, use `beautifulsoup4` when available.

Remove:

- `script`
- `style`
- `head`
- `svg`
- comments
- layout containers when they add no textual meaning
- unsafe attributes such as inline `style`, event handlers, layout-only classes

Preserve or convert:

- `h1`-`h6` -> Markdown headings.
- `p` -> paragraphs.
- `br` -> line breaks.
- `table`, `tr`, `th`, `td` -> Markdown tables.
- `img src` and `alt` -> Markdown image links.
- `a href` -> links when text and target are meaningful.
- `blockquote`, `ol`, `ul`, `li`, `sup`, `sub` when safely convertible.

## Cleaning Function

```text
function clean_text(plain_text_md, workspace, config) {
    profile = config.cleaning.profile or "cc_text_cleaner"

    if profile == "conservative" {
        cleaned = call clean_conservative(plain_text_md)
    }

    if profile == "cc_text_cleaner" {
        cleaned = call clean_cc_text_cleaner(plain_text_md)
    }

    write cleaned to clean/cleaned_text.md
    store cleaning report in state.json.stages.clean_text

    if config.cleaning.export_txt == true {
        write plain-text export to clean/cleaned_text.txt
    }

    return "clean/cleaned_text.md"
}
```

## Cleaning Report

`state.json.stages.clean_text` records:

- input file
- output file
- profile
- detected encoding
- normalization form
- rules applied
- rules skipped
- invalid character count
- replacement marker count
- char count before and after
- line count before and after
- warnings
