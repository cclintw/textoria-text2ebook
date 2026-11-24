# 基本書目資料

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 提出書目候選

```text
const 書目判斷依據 = {
  開頭文本、標題、序跋、刊記與署名；每個候選值記錄來源路徑／段落及簡短依據。
  程式可確定辨識標題與明確標示行，但不能解決所有歷史署名。
};
const 候選值規則 = {
  僅蒐集書名、作者／編者及明確有據的校註／校訂者；只有書名必填。
  未知選填貢獻者可省略或在對話說明未詳；未署名不證明匿名。
  序作者不自動等於全書作者，各角色保持區別。
  檔名只作輔助證據；外部記憶不凌駕文本或已確認資訊。
  自動作者欄為空不等於作者未知的證據。
};
function 提出書目候選(來源文本, 已保存書目) {
  依書目判斷依據檢查文本。
  for (候選欄位 in 基本書目欄位) {
    if (已有明確人工決定) { 保留該決定。 }
    else if (找到明確證據) { 記錄候選值與證據。 }
    else if (欄位選填) { 省略，不猜姓名。 }
  }
  if (Agent 找到自動辨識未涵蓋的有據值) { 以待審 patch 提出。 }
  return 附來源依據的待確認書目;
}
```

## 編輯與匯入

```text
const 書目資料規格 = {
  接受對話增刪改、直接編輯、CSV、XLSX、JSON、TXT、Markdown。
  CSV／XLSX：欄位／值配對，或有命名欄位的單筆紀錄。
  JSON：無重複鍵的命名物件。
  metadata.json：title、creators、contributors、extra；人物含 name、role。
  固定角色與便利 patch 鍵依本節表格；角色儲存值不改譯。
  extra 僅保存使用者主動提供值，不預建 ISBN、出版者、出版日或權利欄位。
  patch 替換指定角色的完整名單。
};
function 編輯與匯入(書目輸入, 指定工作表, 既有資料) {
  if (格式是 XLS) { return 先轉 XLSX 或 CSV; }
  if (多筆紀錄或工作表且目標不明) {
    return 等待明確選定，必要時使用 --metadata-sheet;
  }
  if (格式是 XLSX) {
    用標準函式庫讀字面值，不執行公式。
    if (輸入模糊或以公式為基礎) { return 拒絕該輸入並請求明確值; }
  }
  if (JSON 有重複鍵或其他重複／模糊欄位) { return 需要釐清，不擅選第一筆; }
  保存原始附件至 source/metadata/，記錄雜湊與版本化檔名。
  依書目資料規格整理值。
  return 待審閱值與原始輸入溯源，不自動確認;
}
```

| 角色 | 固定儲存值 | patch 便利鍵 |
|---|---|---|
| 作者 | `作者` | `author` |
| 編者 | `編者` | `editor` |
| 校註者 | `校註者` | `annotator` |
| 校訂者 | `校訂者` | `reviser` |

## 審閱與編輯

命令中的 `PYTHON`、`COLLECTION_ROOT`、`METADATA_FILE` 必須替換為實際直譯器、集合及輸入路徑。書名與作者值是虛構示例。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_metadata
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-patch '{"title":"Example Work","author":"Example Author"}'
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-file METADATA_FILE
```

```text
const 書目審閱規則 = {
  needs_metadata_confirmation 與結束碼 2 是審閱確認點。
  直接編輯也須重新顯示值；舊 token 不確認變更後的值。
  匯入／patch 不與確認合併一次呼叫；本階段不詢問素材。
};
function 審閱與編輯(章節狀態, 書目輸入, 修改要求) {
  if (章節未確認或已失效) { return 等待章節確認; }
  if (要求移除欄位) { 使用 --metadata-delete 搭配實際欄位。 }
  依本節命令執行 review_metadata 或 edit_metadata。
  if (發生非待確認錯誤) { return 實際問題; }
  顯示回傳值、證據、metadata_file 實際連結與確認／編輯選項。
  接受自由文字、檔案修改與直接編輯。
  return 目前待確認版本與 metadata_token，不執行確認命令;
}
```

## 確認書目

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_metadata --metadata-token METADATA_TOKEN
```

```text
function 確認書目(目前顯示書目, 保存確認, metadata_token) {
  if (目前值已有有效明確確認且無變更) { return 保存的書目確認; }
  if (尚未明確確認目前值 || token 不對應目前版本) {
    return 等待目前版本確認，不執行本節命令;
  }
  以目前 METADATA_TOKEN 執行 confirm_metadata --metadata-token。
  if (未回傳 metadata_confirmed) { return 實際待決或錯誤結果; }
  核對書目保存與 archive 同步結果。
  return metadata_confirmed，下一步為素材；不接收素材或生成輸出;
}
```

## 保存與投影人工決定

```text
const 書目保存規則 = {
  state.json.reviews.metadata 保存證據、雜湊、匯入輸入與刪除，不是第二份可編輯書目。
  重建保留人工值與刪除；已刪角色不由推論恢復。
  書目不虛構書名頁文字，也不決定現代校註權利。
};
function 保存與投影人工決定(已確認書目, 人工決定, archive) {
  if (保存書目缺少或無效) { return 等待釐清，不猜測重建; }
  保存書目審閱紀錄與人工增刪改。
  將核准值投影至 archive 的集合／文件書目，供網站與 EPUB 使用。
  if (archive 含多文件) { 只向有證據的文件投影該作者，不套用全部。 }
  if (只改書名) { 不改資料夾，不使未變章節失效。 }
  return 保存與投影結果;
}
```
