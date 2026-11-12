# Textoria Text2Ebook 檔案契約

## 新書保存結構

新書保存在 `textoria-text2ebook/collections/<slug>/`，registry 位於 `textoria-text2ebook/registry.json`。每本書包含：

```text
source/                    原始正文副本；不修改
source/metadata/           有上傳時保存原始 metadata 附件
content/全文.md            唯一可編輯的完整正文，含 Markdown 章節標題
content/章節目錄.md        從全文標題生成，供核對與連結
metadata.json              已確認的基本書籍資料
materials/                 僅保存使用者提供的封面、書名頁、版權頁
intermediate/archive.json  正文、結構及 metadata 的共用資料
config/textoria.json       技術設定與身分資料
state.json                 來源校驗、階段狀態與三階段確認紀錄
site/                      生成的閱讀網站
export/<書名>.epub         實際生成的電子書
```

正文階段已實作 `source/`、`content/全文.md`、`content/章節目錄.md`、設定、確認狀態及確認後的 canonical archive。`metadata.json`、`source/metadata/` 與 metadata 確認紀錄亦已接入；素材接收、檢查、保存與選擇亦已接入；EPUB 匯出已接入，只有驗證成功才發布至 `export/`。不要為未提供的素材建立檔案或空目錄。原始資料、工作內容與生成成果不得混為一份。上傳附件必須保存副本；本機原稿保持原位不改動，同時保存來源副本供重建。

## 單一修訂依據

- 原稿副本放在 `source/`，來源內容變更時另存帶雜湊後綴的版本，不覆寫舊副本。`state.json.source` 保存原始路徑、保存路徑與校驗碼；暫存附件消失後可從保存副本接續。
- 正文與章節的唯一人工修訂依據是 `content/全文.md`；目錄由其標題生成。修改目錄的要求要回寫全文標題，再更新目錄，不能只改目錄而保留不同結構。
- `metadata.json` 是基本書目的人工作業依據；不要再從檔名覆寫。
- `materials/` 保存實際使用的原始素材，保留名稱與格式。圖片不因生成而覆寫。
- `archive.json` 是下游共用的結構化資料，由確認過的內容更新。資料模型保持 `collections -> documents -> divisions -> paragraphs -> sentences -> tokens`。不自動增加句子／詞層或固定 book/chapter 表。
- 網站、搜尋索引與 EPUB 直接從 `archive.json` 生成；標準流程不產生 `sqlite/` 或資料庫檔案。既有資料庫保留且不因網站重建而更新。CSV、SQLite、TEI 僅保留額外技術能力，不自行啟用。

## 確認狀態

在 `state.json.reviews` 分別保存：

- `chapters`：`status`、`input_hash`、`outline_hash`、`heading_hash`、`review_token`、`assignments`、工作檔路徑及確認時間。`heading_hash` 同時涵蓋文件／章節拓樸與段落數／歸屬，`assignments` 保存段落雜湊及其文件／章節。正文變更後重新比對標題與章節歸屬；章節、順序或段落歸屬有變更須重新確認，不能因舊狀態存在而跳過。
- `metadata`：`status`、`input_hash`、`review_token`、`evidence`、`removed_fields`、`inputs`、`last_values` 與確認時間。`last_values` 僅供比較直接編輯與刪除，不是另一份可編輯 metadata。
- `materials`：`status`、`files`、`history`、`review_token`、`metadata_hash`、`conflicts`、`invalid`、`skipped` 與確認時間。`files` 以 cover／titlepage／copyright 為鍵，保存 name、original_path、relative_path、sha256、inspection；history 保存被替換的選擇記錄。

`status` 使用 `pending`、`confirmed` 或 `skipped`；`skipped` 僅適用選用素材，不能用於章節確認。記錄的是使用者實際選擇，不能因辨識高信心或等候逾時而設為 confirmed。後續重建先比對相關檔案／結構；改動哪一部分，才重啟該部分的確認。所有新增來源與素材均記錄原路徑、保存路徑、格式及 SHA-256。

## 現有資料的相容性

新書籍根目錄使用 `textoria-text2ebook/collections/`。已存在的 `textoria-digital-library/collections/` 僅在使用者明確要求改名時搬移；搬移前備份，目的地存在時停止，不合併覆寫，並同步 registry 與工作路徑後驗證。其 `clean/cleaned_text.md` 仍為唯一正文工作檔，`intermediate/archive.json`、`config/textoria.json`、`sqlite/library.sqlite` 與既有網站繼續保留。章節目錄可另存在原書的 `content/章節目錄.md`，對話全文連結指向實際工作檔，不製作另一份可能分歧的全文。

CLI 對新書使用 `content/全文.md`，對已存在 `clean/cleaned_text.md` 的書籍沿用舊工作檔，不建立另一份全文。兩份同時存在時停止，要求先確定唯一修訂依據；不根據時間戳自行選擇。改名後 CLI 同時讀取新舊 registry，沿用原 output，避免同一來源形成重複書籍。

## Canonical archive 與網站

`archive.json` 必須包含恰一個 collection，以及 documents、divisions、paragraphs、source_files、metadata 陣列；可選 sentences／tokens 僅在啟用時保留。欄位依 `textoria_common.CSV_FIELDS` 與 [schema.md](schema.md)，驗證唯一 ID、文件連結、章節父子連結、循環與段落歸屬。

目前網站仍由真實 HTML 頁面、CSS／JS、唯一的 `site/data/search_index.js` 組成。此索引以 classic script 設定 `window.TEXTORIA_SEARCH_INDEX`，先於搜尋 UI 載入，不 fetch JSON，保留 HTTP 與直接開檔支援。SQLite 不在瀏覽器中讀取。新的製書 UI 尚未套用，參見 [theme-system.md](theme-system.md)。

## EPUB 建置紀錄

`state.json` 的 `epub_identity.identifier` 保存持久識別碼，`epub_outputs` 保存生成檔案雜湊。階段紀錄保存建置與驗證結果。未追蹤或經外部修改的 EPUB 不覆寫。驗證失敗不取代既有成果。
