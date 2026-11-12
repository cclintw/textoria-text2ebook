# 基本書籍 Metadata

## 欄位與依據

基本書籍資料僅包含書名、作者／編者、有明確資料的校註者／校訂者。書名為必要值，其餘允許省略或未詳；沒有署名不能自行判定為佚名。角色以原文為準，支持多位人物，不將前言撰寫者直接指定為全書作者。

先從正文的卷首、標題、序跋及署名整理建議值，檔名只作參考。為每個推定值保存來源段落或檔案與簡短依據。未由使用者確認的外部記憶不能覆蓋文本證據；有衝突時在對話中指出並詢問。

使用者可在對話中新增、刪除、修改欄位，也可提供 CSV、Excel（`.xlsx`）、JSON、TXT 或 Markdown。CSV／Excel 接受「欄位、內容」兩欄或具名欄位的單筆書目資料；多筆或多工作表有歧義時先確認。JSON 接受具名物件；文字接受「書名：……」「作者：……」等可辨識格式。Excel 僅用於 metadata，不屬於正文輸入。內附程式以標準函式庫讀取 `.xlsx` 的 literal values，不執行公式；多個有內容的工作表使用 `--metadata-sheet` 選定。舊 `.xls` 需先另存為 `.xlsx` 或 CSV，不宣稱已支援讀取。重複 JSON 欄位、重複表格欄位、多筆書目或不可解析的內容均明確停止，不自行選第一筆。

## 保存格式

`metadata.json` 保存一份基本資料，例如以下明確標示的虛構示例：

```json
{
  "title": "示例文獻",
  "creators": [{"name": "示例作者", "role": "作者"}],
  "contributors": [{"name": "示例校訂者", "role": "校訂者"}],
  "extra": {}
}
```

`extra` 只存使用者主動提供的其他資料，不預先建立 ISBN、出版者、出版日期等空欄位。原 metadata 附件保存在 `source/metadata/`，書籍所用的標準化值以 `metadata.json` 為準。辨識依據、人工刪除欄位及此檔案的確認雜湊存於 `state.json.reviews.metadata`，不混入可見書名。

人工值優先；同一書籍重建不重新推定並覆寫。若使用者刪除角色或值，保存刪除狀態，禁止後續補預設值時恢復。修改 metadata 後重新確認；只修改排版不需重問。

## 對話提示範例

以下是示例對話，正式執行時以實際辨識資料替換，不將示例人物當作真實結果：

> 從文本的卷首與署名辨識到以下基本書籍資料：
>
> 書名：示例文獻  
> 作者：示例作者  
> 校訂者：示例校訂者
>
> 請確認資料是否正確。可回覆「確認」，或直接說明要新增、刪除、修改的內容，例如「書名改為……」「新增編者……」「刪除校訂者」。也可上傳 CSV、Excel、JSON 或 TXT／MD 檔案提供資料；讀取後會再次列出供核對。

此訊息不詢問素材。基本 metadata 不自動生成封面、書名頁或版權頁，也不自動判定古籍的現代校註內容屬公領域。

## 程式與對話分工

`textoria_metadata.py` 自動讀取文件標題及卷首明確的「書名：」「作者：」「編者：」「校註者：」「校訂者：」標記，不從正文敘事或前言署名猜全書作者。古籍中沒有這些標記的署名由 Agent 閱讀原文後提出有依據的建議，再透過 patch 寫入待確認資料；不得把程式沒有辨識到姓名解釋為作者必然未詳。

首次整理將建議值保存為 `metadata.json`，狀態為 pending，列出值及依據供確認；不是保存即代表通過。既有檔案不重做推定，不填回刪除的人物；檔案遺失或 JSON 損壞時停止，不以新推定值覆蓋。人工刪除狀態、證據、匯入來源與最近一次比較值存於 state，不另造第二份人工作業檔。

## 操作指令

以下的 `PYTHON` 是已通過 runtime check 的實際環境執行檔，`COLLECTION_ROOT` 是書籍根目錄。章節未確認時，所有 metadata 指令先回傳章節審查，不接收或處理素材。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_metadata
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-patch '{"書名":"示例文獻","作者":"示例作者"}' --metadata-delete 校訂者
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task edit_metadata --metadata-file METADATA_FILE
```

指令中的書目值為虛構示例，實際以文本依據與使用者修正替換。Patch 可以替換某角色的完整名單，`creators`／`contributors` 接受含 name／role 的陣列。未知的主動新增欄位存入 `extra`；不自動新增出版資料。

指令回傳 `needs_metadata_confirmation`、`metadata_file`、整理值、依據與 `metadata_token`，退出碼為 2，表示等待確認。Agent 在對話中列出結果並提供檔案連結，提醒可新增／刪除／修改，不能直接將技術 token 當作使用者應填的欄位。

收到使用者對這個版本的明確確認後，執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_metadata --metadata-token METADATA_TOKEN
```

`METADATA_TOKEN` 取自已呈現並確認的那次結果。變更與確認必須分開；不可同時匯入檔案、patch 與確認。使用者直接修改 JSON 後也須重新列出確認，舊 token 不能套用。成功回傳 `metadata_confirmed`、`next_step: materials`，此指令不接收素材、不生成 EPUB 或網站。Agent 接著才依素材規範詢問，不將素材問題混入 metadata 審查提示。

確認結果同步至 canonical archive 的 collection／document 與其 metadata_json，後續 SQLite、網站從該資料生成。書名改動不自動改資料夾／slug，也不使正文章節標題的既有確認失效；原始結構標題保留於內部資料。多文件書籍不將同一位作者強行指定給每個文件。

`source/metadata/` 保留匯入原件與 SHA-256；同名不同內容另存帶雜湊後綴的版本，不覆寫舊原件。解析及欄位驗證失敗時不更新 metadata 或保存失敗的匯入。只改 metadata 時不覆寫工作全文或重清理原稿。
