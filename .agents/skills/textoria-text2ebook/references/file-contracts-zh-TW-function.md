# 保存檔案與資料權責

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

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
const 集合配置 = {
  中文工作檔名為固定程式契約，不改拼法。
  僅在實際提供檔案時建立素材／附件資料夾。
  來源、可編輯工作與生成輸出分離保存。
};
```

## 維護權威來源

```text
const 檔案權責 = {
  source/：不可變副本；改變來源以雜湊後綴另存。
  state.json.source：原始／保存路徑與 SHA-256。
  content/全文.md：新集合唯一可編輯正文與章節來源；目錄從全文衍生。
  metadata.json：人工書目值，不以檔名覆寫，不恢復刻意刪除欄位。
  materials/：原始位元組、格式、替換歷史與雜湊；建置不覆寫封面。
  archive.json：確認文本與書目衍生，依 schema-zh-TW-function.md；預設不生成句子／詞元內容。
  sqlite/：標準網站、搜尋與 EPUB 不建立或更新；獨立 CSV／SQLite／TEI 另確認範圍。
};
function 維護權威來源(集合, 來源, 目前確認狀態, 明確任務) {
  保存來源；來源變更時新增副本，不覆寫舊版。
  if (需從保存副本接續 && 副本驗證未通過) { return 阻擋接續; }
  if (要求變更章節) { 先修改權威全文，再衍生目錄。 }
  保留人工書目、素材位元組、替換歷史與雜湊。
  if (確認資料有效) { 依標準結構同步 archive.json。 }
  if (明確轉碼任務) {
    寫 prepared/<stem>.utf8.<ext>。
  } else if (明確擷取任務) {
    寫 intermediate/plain_text.md。
  } else {
    轉碼／擷取緩衝保留於記憶體。
  }
  階段摘要寫入 state.json，不另建報告目錄。
  return 依檔案權責保存的實際資料狀態;
}
```

## 確認狀態

| 獨立紀錄 | 綁定資料 |
|---|---|
| `chapters` | 全文／目錄路徑、輸入／目錄／標題雜湊、token、段落歸屬、狀態、確認時間。 |
| `metadata` | 值雜湊與 token、證據、刪除欄位、匯入輸入、上次值、狀態、確認時間。 |
| `materials` | 選用檔案與檢查、原始／保存路徑與雜湊、替換歷史、書目雜湊、token、衝突、無效項目、略過／狀態決定、確認時間。 |

```text
const 審閱狀態規格 = {
  state.json.reviews 的三項獨立紀錄依本節表格保存。
  狀態為 pending、confirmed；僅素材可為 skipped。
  只記錄實際決定，不推定同意；只重開受影響的確認點。
};
function 核對確認狀態(目前內容, 保存審閱紀錄) {
  if (章節結構或段落歸屬改變) { 將章節設為待審閱，不沿用舊 token。 }
  if (書目改變) {
    將書目設為待審閱，並重新核對素材身分與綁定資料。
  }
  下游生成前重查保存素材雜湊。
  if (任一必要確認缺少或失效) { return 對應的待確認狀態，不生成下游結果; }
  return 與目前內容一致的有效審閱狀態;
}
```

## 網站與 EPUB

```text
const 網站與 EPUB = {
  網站 = HTML、CSS／JavaScript、單一 site/data/search_index.js。
  索引以傳統腳本設定 window.TEXTORIA_SEARCH_INDEX，先於閱讀搜尋介面載入。
  不改為依賴 fetch 的 JSON；瀏覽器不讀 SQLite。
  保留 theme-system-zh-TW-function.md 中的路由與行為。
  EPUB 識別碼 = state.json.epub_identity.identifier。
  epub_outputs = 已正式寫入輸出的檔案雜湊紀錄。
  未追蹤或外部修改的 EPUB → 不默默覆寫。
  驗證失敗 → 保留既有輸出；詳見 epub-zh-TW-function.md。
};
```

## 維持相容或搬移集合

```text
const 相容規則 = {
  舊集合已使用 clean/cleaned_text.md 時，不再建第二份可編輯正文。
  搬移集合不授權搬移虛擬環境。
};
function 維持相容或搬移集合(既有集合, 明確搬移要求) {
  if (舊、新工作檔並存) { return 等待權威來源選擇，不按時間戳判斷; }
  if (沒有搬移要求) { return 沿用 textoria-digital-library/ 實際路徑; }
  if (目的地已占用) { return 拒絕搬移至已占用目的地; }
  備份集合，保留來源與人工修改。
  搬移後更新登錄／設定／狀態路徑。
  驗證搬移輸出，不重新處理正文。
  return 實際搬移與驗證結果;
}
```

相關文件：[資料結構](schema-zh-TW-function.md)、[閱讀主題](theme-system-zh-TW-function.md)、[EPUB](epub-zh-TW-function.md)。
