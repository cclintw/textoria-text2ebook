# 基本書目資料

## 提出書目候選

```text
僅蒐集 = 書名、作者／編者、明確有據的校註者／校訂者。
必填 = 書名；未知的選填貢獻者可省略或在對話說明未詳。
未署名不證明匿名；序作者不自動等於全書作者；各角色保持區別。
檢查 = 開頭文本、標題、序跋、刊記與署名。
為每個候選值記錄來源路徑／段落及簡短依據。
檔名僅為輔助證據，不覆寫確認書名。
外部記憶不凌駕文本或使用者確認。
程式可確定辨識標題與明確標示行，但不解決所有歷史署名。
Agent 可用待審 patch 提出其他有據值。
自動作者欄位為空，不等於作者未知的證據。
```

## 編輯與匯入

```text
接受 = 對話增刪改、直接編輯書目檔、CSV、XLSX、JSON、TXT、Markdown。
CSV／XLSX = 欄位／值配對，或含命名欄位的單筆紀錄。
多筆紀錄／工作表 → 明確釐清；必要時使用 --metadata-sheet。
XLSX 用標準函式庫讀取字面值，不執行公式；拒絕模糊或以公式為基礎的輸入。
XLS → 先轉 XLSX 或 CSV。
JSON = 無重複鍵的命名物件；模糊紀錄／重複欄位不得擅選第一筆。
原始附件保存於 source/metadata/，保留雜湊與版本化檔名。
metadata.json = title、creators、contributors、extra。
人物 = name、role。
```

| 角色 | 固定儲存值 | patch 便利鍵 |
|---|---|---|
| 作者 | `作者` | `author` |
| 編者 | `編者` | `editor` |
| 校註者 | `校註者` | `annotator` |
| 校訂者 | `校訂者` | `reviser` |

```text
固定角色值不得改譯。
extra 僅保存使用者主動提供的額外值；不預建 ISBN、出版者、出版日、權利欄位。
patch 對指定角色採整份名單替換。
```

## 審閱與編輯

命令中的 `PYTHON`、`COLLECTION_ROOT`、`METADATA_FILE` 必須替換為實際直譯器、集合及輸入路徑。書名與作者值是虛構示例。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_metadata
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-patch '{"title":"Example Work","author":"Example Author"}'
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-file METADATA_FILE
```

```text
移除值 → --metadata-delete 搭配實際欄位。
待確認結果 = needs_metadata_confirmation、metadata_file、值、證據、metadata_token。
結束碼 2 = 審閱確認點。
顯示實際值與證據、提供檔案連結及確認／編輯選擇，接受文字或檔案修改。
本階段不詢問素材。
匯入／patch 與確認不可合併一次呼叫。
直接編輯後仍須顯示新值並等待確認；舊 token 不確認新值。
```

## 確認書目

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_metadata --metadata-token METADATA_TOKEN
```

```text
metadata_confirmed → 同步 archive，下一步為素材。
本命令不接收素材，也不生成輸出。
```

## 保存與投影人工決定

```text
state.json.reviews.metadata 保存證據、雜湊、匯入輸入與刪除紀錄；不是第二份可編輯書目。
重建保留人工值與刪除；已刪角色不得由推論恢復。
保存書目缺少或無效 → 釐清，不猜測重建。
將核准值投影至 archive 的集合／文件書目，供網站與 EPUB 使用。
只改書名 → 不改資料夾、不使未變章節失效。
多文件 archive → 不無據將同一作者套到全部文件。
書目不虛構書名頁文字，也不決定現代校註的權利。
```
