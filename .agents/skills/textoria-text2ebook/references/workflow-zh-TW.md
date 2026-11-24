# 處理流程

## 協調製書

```text
先依 intent-policy-zh-TW.md 判定輸出。
檢查並保存來源 → 準備工作全文與目錄
→ 確認章節 → 確認基本書目 → 選擇素材
→ 建置要求的輸出 → 驗證並交付
→ 已完成網站才詢問選用 Sites 發布。
章節、書目、素材分別決定；內容未變時才能沿用對應的明確確認。
依 SKILL-zh-TW.md 互動規則提問。
```

命令符號定義：`PYTHON` 為已驗證直譯器，`SOURCE` 為實際來源，`PROJECT` 為專案根目錄，`COLLECTION_ROOT` 為實際書籍集合目錄，`NAME` 為集合名稱。執行前替換符號；技術 token 來自命令結果，不要求使用者填寫。

## 準備章節審閱

先讀 [執行環境](runtime-zh-TW.md) 與 [文本清理](text-cleaning-zh-TW.md)，再執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --task inspect_input
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --collection-name NAME --task review_chapters
```

```text
review_chapters 保存來源、可編輯全文與獨立目錄。
回傳 needs_chapter_confirmation，結束碼 2 = 等待確認，不是建置失敗。
將 links 中兩份路徑轉成對話中的實際可點連結。
顯示偵測目錄及主指引要求的標題範例；任何信心值都等待層級／順序確認。
未確認 → 阻擋 canonical archive 正式寫入與下游輸出，保留既有成果。
高信心或 --confirm-inferred-structure 不能取代同意。
```

## 確認與更新章節

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_chapters --review-token REVIEW_TOKEN
```

```text
前提 = 目前版本已獲明確確認；REVIEW_TOKEN 使用本次審閱 token。
結果 = 保存核准結構，回傳 chapters_confirmed，下一步為書目。
不生成網站、SQLite 或 EPUB。
工作文本改變 → 再執行 review_chapters。
標題／層級／順序／段落數／段落歸屬改變 → 新審閱；舊 token 不確認新版本。
只改正文措辭且結構、段落歸屬不變 → 可保留章節確認。
低信心且缺乏可用標題 → 先修正再確認。
目錄由全文衍生；先改全文標題，不維護互相矛盾的結構。
忽略圍欄程式碼中的標題範例。
```

## 保護人工修改

```text
不自動重新清理人工改過的全文。
來源位元組／擷取選項改變且將覆寫工作 → 明確決定後才執行 reclean_text。
原始檔缺少 → 可驗證並沿用保存副本；副本被改動 → 阻擋處理。
新書用 content/全文.md；舊集合若用 clean/cleaned_text.md 就維持唯一來源。
兩者並存 → 停止並釐清權威來源，不按時間戳挑選。
```

## 接續書目與素材

```text
依 metadata-zh-TW.md：
  review_metadata／edit_metadata 只準備待確認值。
  confirm_metadata --metadata-token 才記錄明確同意並投影至 archive。
  重建保留人工值與刪除；書目問題不混入素材。
依 materials-zh-TW.md：
  review_materials 列出保存素材。
  receive_materials --material 保存實際提供檔案。
  明確完成 → 用目前 confirm_materials --materials-token。
  明確略過 → skip_materials；不刪既有素材。
  確認前解決身分衝突。
下游建置也強制確認點，不是繞過檢查的捷徑。
```

## 建置與驗證

| 要求 | 任務 |
|---|---|
| 本機 HTTP／直接開檔網站 | `rebuild_site` |
| 僅 EPUB | `build_epub` |
| 網站及 EPUB | `build_fulltext_archive` |
| 驗證既有網站 | `validate_output` 或獨立驗證器 |

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task rebuild_site
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate.py COLLECTION_ROOT
```

```text
網站、瀏覽器搜尋與預設驗證讀 archive.json，不讀 SQLite。
驗證 = archive 結構、預期章節頁、相對資源、搜尋段落 ID／文字、腳本順序、結果錨點。
搜尋採傳統腳本，支援 HTTP 與直接開檔；依 theme-system-zh-TW.md。
僅另行授權 build_sqlite／rebuild_database 才建立／更新資料庫。
網站工作不改既有資料庫。
textoria_validate.py COLLECTION_ROOT --check-sqlite 可加選用資料庫檢查。
EPUB 依 epub-zh-TW.md；只報告實際完成檢查，不推定符合性。
```

## 交付並處理選用發布

```text
依主指引交付格式列明實際功能、URL 與服務狀態、已生成 HTML／EPUB 絕對路徑及用法。
附全文、目錄、書目連結；不宣稱缺少成果、不留下未替換變數。
網站本機交付後 → 一律提出最終 Sites 選擇。
明確同意 → 依獨立發布流程；終端成功後才報告實際閱讀 URL。
EPUB-only → 不為提供託管而建立網站。
```

## 接續舊命名空間

```text
讀取目前與 textoria-digital-library 登錄檔。
以實際 --output 接續，不默默改 slug、移動、重新清理或重裝環境。
textoria_migrate_paths.py 只處理經驗證且有保護措施的舊 textoria/ 命名空間，
不是通用集合改名工具。
```

相關文件：[範圍](intent-policy-zh-TW.md)、[主指引](../SKILL-zh-TW.md)、[書目](metadata-zh-TW.md)、[素材](materials-zh-TW.md)、[資料結構](schema-zh-TW.md)、[EPUB](epub-zh-TW.md)、[閱讀主題](theme-system-zh-TW.md)。
