# 標準封存資料與選用資料庫結構

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 主要資料模型

```text
const 主要資料模型 = {
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
};
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
const 資料驗證規格 = {
  前六個標準陣列必備，即使其中選用集合層級清單為空。
  每個陣列內 ID 唯一；集合／文件連結可解析。
  分區父層存在且無循環；段落屬於同文件中的分區。
  下游可能另做檢查，一般 archive 驗證不保證所有語意規則。
  使用既有 metadata_json 字串與 metadata 陣列作規定投影。
  可編輯基本書目存 metadata.json，不另建頂層作者表。
};
function 驗證資料契約(archive) {
  依 scripts/textoria_common.py 的 CSV_FIELDS 與既有驗證實作核對欄位。
  使用 textoria_export.validate_archive 檢查實作所涵蓋的關係。
  if (檢查失敗) { return 實際問題，不交給下游當作有效資料; }
  return 通過已執行範圍的 archive 與檢查紀錄;
}
```

## 建立瀏覽器索引

```text
const 搜尋索引規格 = {
  輸出：單一傳統腳本 site/data/search_index.js，設定 window.TEXTORIA_SEARCH_INDEX。
  HTTP 與 file:// 搜尋均不使用資料庫。
};
function 建立瀏覽器索引(已驗證 archive) {
  將每個分區分配至其頂層閱讀頁。
  for (閱讀段落 in archive 的段落) {
    加入分區標題／路徑與相對段落 href。
  }
  依搜尋索引規格寫檔。
  比對段落 ID、數量、文字與結果錨點。
  if (不一致) { return 索引驗證問題; }
  return 可用的靜態搜尋索引與檢查結果;
}
```

## 選用 SQLite

```text
const 選用資料庫規格 = {
  入口：build_sqlite／rebuild_database；輸出 sqlite/library.sqlite。
  權威實作：scripts/textoria_build_sqlite.py 的 SQL、索引與 FTS 宣告。
  八個標準表加 paragraphs_fts；目前不建句子 FTS 表。
  段落 FTS 用 unicode61，含文件／分區上下文；不改網站靜態搜尋。
  一般網站／EPUB 不需也不更新既有資料庫。
};
function 選用_SQLite(具體技術要求, 明確範圍確認, 已驗證 archive) {
  if (尚未另行確認資料庫任務) { return 不建立或更新資料庫; }
  以本節 --check-sqlite 環境命令檢查 FTS5。
  if (環境未就緒) { return 實際缺少需求，不擅自安裝; }
  以已驗證資料執行已授權入口。
  執行本節資料庫驗證；該命令同時驗證網站。
  檢查完整性、資料表／FTS 數量、段落連結、archive 數量一致與 FTS 範例查詢。
  return 實際資料庫輸出與檢查結果;
}
```

命令中的 `PYTHON` 與 `COLLECTION_ROOT` 以實際值替換：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py --check-sqlite
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT --check-sqlite
```

相關文件：[書目](metadata-zh-TW-function.md)、[檔案契約](file-contracts-zh-TW-function.md)。
