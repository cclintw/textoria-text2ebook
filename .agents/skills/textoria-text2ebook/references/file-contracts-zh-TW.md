# 保存檔案與資料權責

## 集合配置

新集合根目錄：`textoria-text2ebook/collections/<slug>/`。登錄檔：`textoria-text2ebook/registry.json`。

```text
source/                    保存原始正文
source/metadata/           實際提供的書目原始附件
content/全文.md            新集合唯一可編輯全文
content/章節目錄.md        由全文標題衍生的目錄
metadata.json              可編輯基本書目
materials/                 提供的封面與前置頁
intermediate/archive.json  共用結構化確認資料
config/textoria.json       技術設定與集合身分
state.json                 階段結果、雜湊與審閱決定
site/                      生成的靜態閱讀網站
export/<title>.epub        成功生成並驗證的 EPUB
```

```text
中文工作檔名為固定程式契約，不改拼法。
僅在實際提供檔案時建立素材／附件資料夾。
來源、可編輯工作與生成輸出分離保存。
```

## 維護權威來源

```text
source/：
  保存不可變來源副本；來源改變時以雜湊後綴另存，不覆寫舊副本。
  在 state.json.source 記錄原始／保存路徑及 SHA-256。
  從保存副本接續前先驗證。
content/全文.md：
  唯一可編輯正文與章節來源；目錄由此衍生。
  標題修改必須反映於全文，不能只改目錄。
metadata.json：
  人工書目值的來源；不以檔名覆寫，不恢復刻意移除的欄位。
materials/：
  保存原始位元組、格式、替換歷史與雜湊；建置時不覆寫封面。
archive.json：
  由確認後文本與書目衍生；依 schema-zh-TW.md。
  預設不生成句子／詞元陣列內容。
sqlite/：
  標準網站、搜尋、EPUB 不建立或更新；既有資料庫保持原狀。
  獨立 CSV、SQLite、TEI 操作另需範圍確認。
明確轉碼／擷取任務可寫 prepared/<stem>.utf8.<ext>／intermediate/plain_text.md。
一般製書將相應緩衝保留在記憶體；摘要寫入 state.json，不另建報告目錄。
```

## 確認狀態

| 獨立紀錄 | 綁定資料 |
|---|---|
| `chapters` | 全文／目錄路徑、輸入／目錄／標題雜湊、token、段落歸屬、狀態、確認時間。 |
| `metadata` | 值雜湊與 token、證據、刪除欄位、匯入輸入、上次值、狀態、確認時間。 |
| `materials` | 選用檔案與檢查、原始／保存路徑與雜湊、替換歷史、書目雜湊、token、衝突、無效項目、略過／狀態決定、確認時間。 |

```text
狀態 = pending、confirmed；僅素材另有 skipped。
記錄實際決定，不推定同意。
結構或段落歸屬改變 → 重開章節審閱。
書目改變 → 重開書目審閱，並可能影響素材身分檢查。
下游生成前 → 重查保存素材雜湊。
只重開受到影響的確認點。
```

## 網站與 EPUB

```text
網站 = HTML、CSS／JavaScript、單一 site/data/search_index.js。
索引以傳統腳本設定 window.TEXTORIA_SEARCH_INDEX，先於閱讀搜尋介面載入。
不改為依賴 fetch 的 JSON；瀏覽器不讀 SQLite。
保留 theme-system-zh-TW.md 中的路由與行為。
EPUB 識別碼 = state.json.epub_identity.identifier。
epub_outputs = 已正式寫入輸出的檔案雜湊紀錄。
未追蹤或外部修改的 EPUB → 不默默覆寫。
驗證失敗 → 保留既有輸出；詳見 epub-zh-TW.md。
```

## 維持相容或搬移集合

```text
舊集合已使用 clean/cleaned_text.md → 仍以它作為唯一可編輯正文。
舊、新工作檔並存 → 停止並明確選定，不按時間戳判斷。
未要求 → 不移動 textoria-digital-library/ 集合。
已授權搬移 → 備份、拒絕已占用目的地、保留來源與人工修改、
              更新登錄／設定／狀態路徑、驗證搬移結果，不重新處理正文。
搬移集合不授權搬移虛擬環境。
```

相關文件：[資料結構](schema-zh-TW.md)、[閱讀主題](theme-system-zh-TW.md)、[EPUB](epub-zh-TW.md)。
