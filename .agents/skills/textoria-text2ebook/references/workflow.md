# Textoria Text2Ebook 操作流程

## 先後順序與停點

開始前先依 [intent-policy.md](intent-policy.md) 檢查需求範圍。本 skill 僅生成本機 HTTP 網站、可用 `file://` 開啟的靜態網站及 EPUB；若將「線上」等措辭理解為 Sites 或其他範圍外動作，先具體追問並等待確認。章節、metadata、素材確認不構成外部發布授權。

```text
辨識正文與來源保存 → 整理全文、章節目錄
→ 提供目錄與全文連結，等待章節確認
→ 辨識基本 metadata，等待確認並保存
→ 詢問選用素材，等待提供／沿用／略過
→ 生成要求的網站／EPUB → 驗證與交付
```

任何章節信心等級都必須經過目錄審查；metadata 不與素材提示合併。使用者修正後更新相應檔案與確認狀態，不把延遲、預選值或自動推定當作確認。

各停點依 [SKILL.md 的確認與選項介面](../SKILL.md#確認與選項介面) 顯示可點選選項。檔案連結、審查內容及必要說明仍須先在對話中呈現；互動提問不取代這些資訊，也不將多個階段合併詢問。

## 正文與章節審查指令

處理環境先依 [runtime.md](runtime.md) 檢查。新環境為 `.textoria-text2ebook/venv/bin/python`；已存在且檢查通過的 `.textoria-digital-library/venv/bin/python` 可直接沿用。下例中的 `PYTHON` 表示實際選定的環境執行檔。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --collection-name NAME --task review_chapters
```

首次審查會保存來源副本、`content/全文.md`、`content/章節目錄.md` 與設定／狀態。回傳 `needs_chapter_confirmation`，退出碼為 2，表示等待使用者審查，不是建置失敗。`links` 提供兩個檔案的絕對路徑，`heading_example` 提供章節標記範例，`review_token` 識別目前可確認的版本。Agent 必須把檔案路徑轉為可點選的對話連結並顯示說明，不能只把 JSON 丟給使用者。

即使直接執行完整建置、結構化或資料庫建置，也會在章節尚未確認時回傳同一審查狀態；未確認不產生或取代 canonical archive、SQLite、網站。既有成果保留，狀態中標示待審查。

收到使用者對目前版本的明確確認後，再執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_chapters --review-token REVIEW_TOKEN
```

`COLLECTION_ROOT` 為回傳的 output，`REVIEW_TOKEN` 為已向使用者提供連結並確認過的那一版本 token。此命令不自行詢問或代表使用者同意，Agent 只能在收到確認後執行。成功回傳 `chapters_confirmed`、`next_step: metadata`，保存 canonical archive，但不生成 SQLite、網站或 EPUB。接著依序進入 metadata，不在確認章節的同一則訊息詢問素材。

工作全文或章節目錄已變動時，舊 token 不可用；程式更新目錄並回傳新版本，重新提供連結並等待確認。低信心且無可用標題的版本不能直接確認，需先標記全文或依已確認規則重新結構化。`--confirm-inferred-structure` 只控制標題辨識規則，不能取代章節審查。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_chapters
```

純正文措辭修正且不改變章節結構／段落歸屬時沿用確認；章節改名、層級、順序、段落數或已辨識段落跨章節移動會重新開啟審查。確認版本、雜湊與段落歸屬記錄保存在 `state.json.reviews.chapters`。

`clean_text`／`reclean_text` 是明確只清理正文的技術任務，不自動建立章節目錄；需要章節審查時執行 `review_chapters`。已存在的人工全文不因腳本更新而重新清理；原始來源或擷取選項變更而會覆蓋人工修訂時，停止並要求明確的 `reclean_text` 決定。來源檔消失時可使用已校驗的保存副本；來源副本異動則停止。

## 章節目錄檔

`章節目錄.md` 直接以書籍名稱與層級清單開始，保留順序與原標題，不含助理進度報告。生成目錄時辨識 Markdown 的真正標題，略過程式碼區塊中的 `#` 示例；不要把正文引用或數字清單當章節。

對話中一定同時提供目錄、全文的絕對路徑連結與修訂教學。只有檔案真正存在時才顯示連結。提醒使用者先檢查，明確等待答覆，不在同一則訊息加入 metadata 或素材問題。

## Metadata 與素材

依 [metadata.md](metadata.md) 執行 `review_metadata`，從文本列出建議值；以 `edit_metadata` 接受對話修正或結構資料檔，待使用者確認後執行 `confirm_metadata --metadata-token`。保存 `metadata.json`、原匯入檔與確認依據。既有書籍若已有作者／標題設定，先呈現現有資料，不覆寫。

Metadata 確認後依 [materials.md](materials.md) 執行 `review_materials` 顯示素材提示。`receive_materials --material` 保存已提供的副本；使用者完成提供後才以目前 token 執行 `confirm_materials`，明確略過則使用 `skip_materials`。更換內容須有明確指示與 replace 參數；身份衝突先處理，不修改原文或 metadata。略過只代表本次不新增，不刪除既有素材。首次缺少選用素材亦可製書，但必須等使用者明確完成此步。

網站及 EPUB 共用經確認的基本資料；書名頁、版權頁內容只取自已提供檔案。書名／作者與已提供頁面有矛盾時先指出差異，不擅改文字。

## 下游網站與驗證

對已符合低階 checkpoint 的既有書籍，可在確認完成後執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task rebuild_site
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT
```

新書與既有書籍現在均可用同一 CLI 從已確認的 canonical archive 接續；確認章節命令本身只回傳 metadata 下一步；下游建庫／網站入口也會在 metadata 尚未確認時回傳 metadata 審查，素材尚未選定／略過時回傳素材提示，保存檔異動時重新停止。Agent 不應跳過 metadata 與素材對話步驟。修改 metadata 後同步更新 canonical archive 的 collection／document／metadata 欄位，不在固定 schema 私自增加欄位；參見 [schema.md](schema.md)。

網站與搜尋索引直接從 `archive.json` 生成；標準建置、網站重建、搜尋重建及預設驗證不建立或更新 SQLite，也不要求既有資料庫。驗證以 archive 比對段落數、搜尋正文、章節頁及結果錨點。既有資料庫不自動刪除；只有另行明確要求的 `build_sqlite`／`rebuild_database` 技術任務才建庫，`textoria_validate.py --check-sqlite` 才額外檢查資料庫。

網站檢查閱讀頁、相對資源、搜尋索引與結果錨點。閱讀頁使用原有白色主題並整合搜尋列、結果與命中標示，保留搜尋相容路由。EPUB 執行方式與驗證依 [epub.md](epub.md)。

交付時依 [SKILL.md 的完成交付格式](../SKILL.md#完成交付格式) 列出實際完成的功能、本機網址、閱讀 HTML 完整路徑及 EPUB 完整路徑，並說明各自使用方式；只保留本次已生成的項目。本機服務狀態須在交付時核實，範本變數須替換為真實值。

本次網站完成並交付後，依 [完成後詢問 Sites 發布](../SKILL.md#完成後詢問-sites-發布) 詢問「你要把完成的網站發佈到 Sites 嗎？」，不論最初是否指定 Sites 都須提供最終選擇。明確回答是才接續 Sites 發布，成功後提供真實閱讀網址與存取方式；回答否或尚未答覆時不執行發布。只有 EPUB 成果時不額外建站。

## 接續、改名與相容

新書 namespace 是 `textoria-text2ebook`。讀取新舊 registry；既有 digital-library 書籍以原 `--output` 接續，不自動改 slug、重新清理、搬移書籍或重裝環境。舊 `clean/cleaned_text.md` 已有人工修改時仍是唯一工作檔。

保存 `state.json.reviews`，在章節／metadata／素材變更後只重啟受影響的核對步驟。原始資料缺失時，已有確認工作檔仍可支援下游；不能宣稱可重新執行必須讀原稿的階段。

`textoria_migrate_paths.py` 是經驗證的 legacy `textoria/` 遷移工具，不適用直接將任意 digital-library 根目錄改名。不要因 skill 更名而自動執行。
