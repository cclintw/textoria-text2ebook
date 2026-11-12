# Textoria Compact Checkpoint Fork

This project-local fork uses one canonical structured checkpoint and compact stage state. Archive output contracts differ from the upstream multi-format layout.

## 發布檔案範圍

Skill 的 `scripts/` 保留製書、環境檢查與成果驗證程式。開發回歸測試腳本已移除，本機不另存 `tests/`；流程文件不再提供已移除的測試指令。`textoria_validate.py` 與 `textoria_validate_epub.py` 繼續用於實際成果檢查。

## 不依賴 SQLite 的製書流程

網站、搜尋索引與 EPUB 直接使用 `intermediate/archive.json`。標準建置、網站重建、搜尋重建與預設驗證不建立或更新 SQLite；只有明確的 `build_sqlite`／`rebuild_database` 技術任務保留建庫能力。驗證器從 archive 取得章節與段落，檢查搜尋正文及連結；`--check-sqlite` 可額外核對資料庫。Runtime 就緒判斷不再要求 FTS5。既有資料庫保留，不隨重建刪除。

## 選用 Sites 發布

完成並交付本次網站後，固定詢問是否發布到 Sites，即使最初已提及發布也須取得對完成網站的最終選擇。肯定答覆後依 Sites 流程發布，驗證成功後提供實際閱讀網址與存取方式；否定或未答覆不執行。發布屬製書後的選用工作，網站以外的內部檔案不隨附上傳。只有 EPUB 時不額外生成網站。

## 完成交付格式

`SKILL.md` 定義以變數表示書名、完成功能、本機閱讀網址、服務狀態、閱讀 HTML 絕對路徑與 EPUB 絕對路徑的交付範本。實際回覆替換為已驗證的成果值，逐項提供連結與使用方式；未生成的成果不列為完成，停止的服務不列為可即時使用。`references/workflow.md` 連回同一份交付規範。

## 功能範圍與意圖確認

對外功能限定為本機 HTTP 閱讀網站、可用 `file://` 開啟的靜態網站與 EPUB。凡意圖判斷涉及三者之外的動作，須先具體追問確認；「線上」不得直接解讀為 Sites 發布授權。確認前不建立遠端專案、上傳或部署，也不以其他技能的自動路由或製書各階段確認代替範圍確認。`SKILL.md`、`references/intent-policy.md` 與 `references/workflow.md` 同步採用此邊界；既有技術腳本保留。

## 互動確認介面

環境安裝與製書各確認停點使用可用且允許該用途的互動提問工具提供選項，並保留文字回覆；無適用工具時以文字列出選項。章節與書目審查仍先呈現實際內容及檔案連結。素材選項區分略過、提供、沿用與調整；選擇進入修訂或提供流程不等於完成確認。預選與未回覆不構成授權或確認。規範集中於 `SKILL.md`，環境及流程參考文件連回共同規則。

## Default retention

The processing pipeline retains `clean/cleaned_text.md`, `intermediate/archive.json`, `config/textoria.json`, `state.json` and the website. Originals remain at their source paths. UTF-8 conversion and extraction buffers remain in memory during broader tasks.

Automatic source copies, duplicate per-table JSON, CSV exports, separate review/manifest/log files, Markdown reading exports and unused frontend data copies are no longer default outputs. Sentence segmentation is opt-in. Explicit conversion, extraction, CSV and Markdown requests still produce their requested deliverables.

## Implementation

The orchestrator supports individual stages and resuming saved collection settings. Export, database and site builders use the canonical checkpoint; validation checks the archive and reading/search links. SQLite integrity and FTS checks run only when explicitly requested. State summaries replace per-stage logs. The optional SQLite table model remains unchanged.

Changed modules: `textoria_build`, `textoria_common`, `textoria_utf8_converter`, `textoria_extract_text`, `textoria_clean_text`, `textoria_structure`, `textoria_export`, `textoria_build_sqlite`, `textoria_build_search`, `textoria_build_site`, and `textoria_validate`. The skill entrypoint and relevant workflow, input-resolution, cleaning, schema, theme, intent and file-contract references describe the compact layout.

## Compatibility

Compact config/state use schema version 2. Existing sites and SQLite databases remain usable. Existing collection outputs are not automatically deleted or migrated. Preserve manual edits before rebuilding legacy archives from their original source; a skill update does not authorize collection cleanup.

## Skill namespace

Project outputs use `textoria-text2ebook/`; runtime and backups use `.textoria-text2ebook/`. The namespace is centralized in `textoria_common.SKILL_NAMESPACE`. The collection registry, default output resolver, references and continuation tests use that name. `textoria_migrate_paths.py` migrates verified legacy roots with backup and rollback protection, repairs generated path references and venv launchers, and refuses to merge occupied destinations. Migration preserves existing archive files rather than applying compact-output cleanup.

## Direct file search

The browser index is `site/data/search_index.js`, loaded synchronously as a classic script before the search UI. The same website supports HTTP and `file://` without fetching JSON. The builder emits one safely serialized index; validation parses the JSON payload without execution and checks script order and reading anchors. Existing website outputs need rebuilding to adopt this behavior.

## Textoria Text2Ebook 流程版本

Skill 識別名稱、目錄與新書預設 namespace 改為 `textoria-text2ebook`，顯示名稱為 Textoria Text2Ebook，中文名稱為 Textoria 電子書製作工具。既有 `textoria-digital-library/` 館藏及執行環境保留原位，不因改名自動遷移或重建。

流程改為正文／章節審查、基本 metadata 確認、選用素材、生成與驗證，三個使用者停點分開執行。章節目錄另存並與全文連結同時顯示；所有信心等級均需確認。新增來源與素材保存、metadata 人工修訂及刪除保留、章節修改教學與獨立參考文件。

現有低階 checkpoint 腳本仍保留，沒有新增可繞過確認的製書捷徑。EPUB 外掛快照仍為參考來源；新版檔案路徑、素材轉接、EPUB 生成與閱讀器搜尋整合尚未成為既有 CLI 的完整功能。這次修改不宣稱完成上述程式功能，也未重建既有網站。

## 正文保存與章節審查實作

新增 `textoria_chapter_review.py` 與 `review_chapters`／`confirm_chapters` 指令。新書使用 `content/全文.md`，既有書保留 `clean/cleaned_text.md`；CLI 查詢新舊 registry，不自動搬移。來源副本採不可覆寫版本保存，附件消失後可從校驗過的副本接續。

建置入口在所有信心等級均先生成獨立目錄並停在章節確認，確認綁定目前全文及目錄 token；章節異動會失效，未確認不取代 canonical archive 或下游成果。程式碼區塊中的 Markdown 標題不作章節，修正多文件無標題段落的歸屬。確認命令僅保存結構並回傳 metadata 下一步。

Metadata／素材／EPUB 程式與 UI 合併仍為不同實作階段。

## 基本 Metadata 保存與確認實作

新增 `textoria_metadata.py` 及 `review_metadata`、`edit_metadata`、`confirm_metadata` 任務。章節確認後才處理 metadata；下游建庫／網站任務在 metadata 待審時停止。僅書名必要，保留作者／編者與校註／校訂角色，不自動增加出版欄位。

支援對話 patch、刪除、CSV、JSON、標記文字與 XLSX literal values 匯入；歧義資料、公式及舊 XLS 明確停止。使用標準函式庫讀取 XLSX，沒有新增依賴。保存上傳原件版本與校驗碼，保留人工修訂／刪除及確認狀態，不因重建重新推定。

Metadata 確認與資料修改分開，直接修改 JSON 亦使舊確認失效。確認後同步 canonical archive，書名修正不改變既有正文目錄的確認，資料夾與 slug 不更名。確認命令只回傳素材下一步，未實作素材或 EPUB 整合。

## 選用素材接收與保存實作

新增 `textoria_materials.py` 及 `review_materials`、`receive_materials`、`confirm_materials`、`skip_materials` 任務。在章節與 metadata 確認後才接收素材；下游建庫與網站入口檢查素材決定及保存檔完整性。首次無素材須明確略過，不建立空素材目錄；後續略過保留既有選擇。

封面檢查實際 PNG／JPEG 格式、尺寸與 RGB 資訊；文字頁保留原副檔名、編碼與內容。不同內容更換須明確指定，原件版本與選擇歷史保留。明確的書名／署名差異等待決定，不自動修改文字或 metadata。Token 綁定素材與 metadata 版本；保存檔遺失或變更會阻止下游更新。

未新增依賴，PNG 以標準函式庫檢查容器、壓縮資料與列資訊，JPEG 記錄 frame 檢查範圍，macOS 可另外使用系統 sips 查驗圖片資訊。此階段不生成 EPUB，也不修改讀取器 UI。

## EPUB 生成與驗證

`textoria_build_epub.py` 將已確認正文、metadata 與素材封裝為 EPUB，保留階層目錄與段落錨點，依實際圖片格式註冊封面，省略未提供的前置頁。`build_epub` 只建電子書；`build_fulltext_archive` 在網站檢查成功後同時建電子書。其他網站重建入口保留原有範圍。

`textoria_validate_epub.py` 檢查 ZIP、XML、manifest、spine、參照與段落完整性，並依專案設定執行 EPUBCheck。識別碼持久保存；驗證失敗及輸入途中異動均不發布候選檔。網站閱讀器 UI 尚未調整。

## 閱讀頁整合搜尋

預設主題移除頂部主選單，書名指向閱讀入口，右側改為尋找圖示並開啟左側搜尋列。查詢使用 classic-script 全書索引，結果按書籍根目錄解析路徑，支援跨章錨點、原文標示及分批載入；清空搜尋恢復原目錄，保留目錄展開狀態。`search.html` 渲染相同閱讀器供舊連結使用。正文、章節結構及 EPUB 封裝不因主題變動而重新處理。

## 搜尋彈出框與目錄獨立

尋找改為右上方彈出框，恢復前次查詢與結果；結果跳轉關閉搜尋框而保留查詢。左側欄只顯示章節目錄，與各層分支均預設收合，瀏覽時選取目前章節或其最近可見上層，不自動展開。搜尋、章節選取及側欄開關各自維持獨立操作。

## 桌面側欄狀態

桌面版依書籍於同一瀏覽分頁保存側欄開關狀態，章節切換保持使用者選擇。Mobile 初始收合，點擊章節連結後收合，包括同頁章節錨點；切換視窗寬度不覆寫桌面側欄偏好。

章節分支狀態依書籍保存，不隨側欄收合而重設。切換目前章節及重新展開側欄時，展開其上層路徑並保持目前章節可見；其他分支不自動收合。同一章節內持續捲動不覆寫手動收合。
