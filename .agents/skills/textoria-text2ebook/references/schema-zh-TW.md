# 標準封存資料與選用資料庫結構

## 主要資料模型

```text
共用來源 = intermediate/archive.json。
使用者 = 網站、瀏覽器搜尋、EPUB。
標準建置不建立 SQLite。
階層 = collection → document → division → paragraph → sentence → token。
divisions 遞迴表示卷、章、期、日期、案例、標題等可變層級。
不另加固定 book/chapter/section 表或標準陣列不認識的欄位。
可執行欄位契約 = scripts/textoria_common.py 的 CSV_FIELDS。
使用前驗證 = textoria_export.validate_archive。
load_archive 為選用 sentences／tokens 補空陣列。
改模型時查上述實作，不在文件另維護第二份 SQL 結構。
```

| 陣列 | 責任與關係 |
|---|---|
| `collections` | 恰一集合，含身分、書名、slug、語言、時間及序列化書目。 |
| `documents` | 屬於集合的書目單位。 |
| `divisions` | 屬於文件的有序遞迴分區；`parent_division_id` 指向存在的父層。 |
| `paragraphs` | 同文件既有分區下的文本單位，含順序及來源偏移。 |
| `source_files` | 原始／準備／擷取來源的格式、編碼、大小、雜湊、順序與溯源。 |
| `metadata` | 主體資料表／主體 ID 的鍵值紀錄。 |
| `sentences` | 段落下的選用有序切分，預設不切句。 |
| `tokens` | 選用詞元，通常製書不增加此層。 |

## 驗證資料契約

```text
前六個陣列必備，即使其中選用集合層級清單為空。
每個陣列內 ID 唯一。
集合／文件連結必須可解析。
分區父層存在且無循環。
段落所屬分區必須位於同一文件。
下游可能另做檢查；不宣稱一般 archive 驗證涵蓋所有語意規則。
使用既有 metadata_json 字串與 metadata 陣列進行規定投影。
可編輯基本書目存 metadata.json，不另建頂層作者表。
```

## 建立瀏覽器索引

```text
網站建置器將分區分配到其頂層閱讀頁。
索引在閱讀段落加入分區標題／路徑與相對段落 href。
寫單一傳統腳本 site/data/search_index.js，設定 window.TEXTORIA_SEARCH_INDEX。
預設驗證比對段落 ID、數量、文字與結果錨點。
HTTP 與 file:// 搜尋均不使用資料庫。
```

## 選用 SQLite

```text
僅明確授權後使用 build_sqlite／rebuild_database。
輸出 = sqlite/library.sqlite。
權威實作 = scripts/textoria_build_sqlite.py 的 SQL、索引與 FTS 宣告。
資料表 = 八個標準表 + paragraphs_fts；目前不建句子 FTS 表。
段落 FTS 使用 unicode61，含文件／分區上下文。
存在資料庫不改變網站靜態搜尋。
只有下列明確檢查需要 SQLite FTS5。
```

命令中的 `PYTHON` 與 `COLLECTION_ROOT` 以實際值替換：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py --check-sqlite
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT --check-sqlite
```

```text
第二個命令也驗證網站。
資料庫檢查 = 完整性、資料表／FTS 數量、段落連結、archive 數量一致、FTS 範例查詢。
一般網站／EPUB 不需要也不更新既有資料庫。
```

相關文件：[書目](metadata-zh-TW.md)、[檔案契約](file-contracts-zh-TW.md)。
