# 處理流程

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 協調製書

```text
const 流程規則 = {
  章節、書目、素材各自確認；僅沿用仍符合目前內容的明確決定。
  互動依 SKILL-zh-TW-function.md；不把下游命令當作繞過確認的捷徑。
};
function 協調製書(使用者要求, 來源, 已保存狀態) {
  先依 intent-policy-zh-TW-function.md 判定輸出。
  檢查並保存來源，準備工作全文與目錄。
  for (階段 in [章節確認, 基本書目確認, 選用素材決定]) {
    依對應指引接續該階段。
    if (取消或暫停) { return 已取消或已暫停，保留目前工作; }
    if (尚無有效決定) { return 保存目前階段並等待，不進入下一階段; }
  }
  建置要求輸出，驗證並交付。
  if (已完成且交付網站) { 依主指引處理最終 Sites 選擇。 }
  return 實際完成結果與尚待處理事項;
}
```

命令符號定義：`PYTHON` 為已驗證直譯器，`SOURCE` 為實際來源，`PROJECT` 為專案根目錄，`COLLECTION_ROOT` 為實際書籍集合目錄，`NAME` 為集合名稱。執行前替換符號；技術 token 來自命令結果，不要求使用者填寫。

## 準備章節審閱

先讀 [執行環境](runtime-zh-TW-function.md) 與 [文本清理](text-cleaning-zh-TW-function.md)，再執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --task inspect_input
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py SOURCE --project-root PROJECT --collection-name NAME --task review_chapters
```

```text
const 章節檢查規則 = {
  review_chapters 保存來源、可編輯全文與獨立目錄。
  needs_chapter_confirmation 與結束碼 2 表示確認點，不是建置失敗。
  高信心及 --confirm-inferred-structure 不代表同意。
  未確認時阻擋 canonical archive 正式寫入與下游輸出，保留既有成果。
};
function 準備章節審閱(來源, 集合, 可用環境) {
  先依執行環境與清理文件完成必要檢查。
  依本節命令執行 inspect_input 與 review_chapters。
  if (實際錯誤不是待確認點) { return 實際錯誤，不往下建置; }
  將回傳 links 的兩份路徑轉成實際可點連結。
  顯示偵測目錄、主指引標題範例及層級／順序檢查要求。
  return 目前全文、目錄、審閱 token 與等待章節確認狀態;
}
```

## 確認與更新章節

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_chapters --review-token REVIEW_TOKEN
```

```text
const 章節版本規則 = {
  標題、層級、順序、段落數或段落歸屬改變會重開審閱。
  只改措辭且結構、段落歸屬不變時，可保留確認。
  目錄由全文衍生；先改全文標題，不維護矛盾目錄。
  忽略圍欄程式碼中的標題範例。
  confirm_chapters 不生成網站、SQLite 或 EPUB。
};
function 確認與更新章節(工作文本, 目前版本, 保存審閱狀態, 明確確認) {
  if (工作文本有變更) {
    再執行 review_chapters，重新核對確認是否仍有效。
  }
  if (低信心且沒有可用標題) { return 先修正標題，再進行確認; }
  if (目前版本已有有效確認) { return chapters_confirmed，下一步為書目; }
  if (缺少目前版本的明確確認或 token 不符) {
    return 等待目前版本的確認，不使用舊 token;
  }
  使用本次 REVIEW_TOKEN 執行本節 confirm_chapters --review-token 命令。
  if (命令未成功) { return 實際問題，不宣稱確認完成; }
  return 保存核准結構的 chapters_confirmed 結果，下一步為書目;
}
```

## 保護人工修改

```text
const 工作文本規則 = {
  新書使用 content/全文.md；既有舊集合沿用 clean/cleaned_text.md 作為唯一正文。
  不自動重新清理人工改過的全文；不按時間戳選權威來源。
};
function 保護人工修改(工作文本, 來源變更, 保存副本, 重新清理決定) {
  if (新舊工作檔並存) { return 等待權威來源選擇，不覆寫; }
  if (原始檔缺少) {
    驗證保存副本。
    if (副本被修改或驗證失敗) { return 阻擋處理; }
    沿用已驗證副本。
  }
  if (來源位元組或擷取選項改變 && 將覆寫人工工作) {
    if (尚未明確決定重新清理) { return 等待重新清理決定; }
    執行 reclean_text。
  }
  return 已核對且受到保護的唯一工作來源;
}
```

## 接續書目與素材

```text
const 後續確認規則 = {
  review_metadata／edit_metadata 只產生待確認值。
  confirm_metadata --metadata-token 才記錄同意並投影 archive。
  重建保留人工值與刪除；書目提問不混入素材。
  下游建置也檢查確認點，不能用建置命令代替確認。
};
function 接續書目與素材(章節狀態, 保存狀態) {
  if (章節未確認或已失效) { return 等待章節確認; }
  依 metadata-zh-TW-function.md 審閱並確認書目。
  if (書目尚未確認) { return 等待目前書目確認; }
  依 materials-zh-TW-function.md 執行 review_materials。
  if (有實際提供檔案) { 用 receive_materials --material 保存。 }
  if (存在未解身分衝突) { return 等待衝突處理; }
  if (已明確完成) {
    執行 confirm_materials --materials-token，使用目前 token。
  } else if (已明確略過) {
    執行 skip_materials，不刪既有素材。
  } else {
    return 等待素材完成或略過決定;
  }
  return 命令實際記錄的書目與素材狀態;
}
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
const 網站驗證範圍 = {
  archive 結構、預期章節頁、相對資源、搜尋段落 ID 與文字、腳本順序、結果錨點。
};
const 建置資料規則 = {
  網站、瀏覽器搜尋、預設驗證讀 archive.json，不讀 SQLite。
  傳統腳本搜尋同時支援 HTTP 與直接開檔，依 theme-system-zh-TW-function.md。
  只有另行授權的 build_sqlite／rebuild_database 才建立或更新資料庫。
  一般網站工作不改既有資料庫。
};
function 建置與驗證(要求輸出, 集合, 目前確認狀態, 資料庫授權) {
  if (必要確認尚未完成或已失效) { return 等待對應確認點; }
  依本節任務表選擇且只建置要求的輸出。
  if (包含網站) {
    執行本節網站驗證命令。
    if (另有資料庫檢查授權) {
      使用 textoria_validate.py COLLECTION_ROOT --check-sqlite 加選用檢查。
    }
  }
  if (包含 EPUB) { 依 epub-zh-TW-function.md 生成並驗證。 }
  if (建置或驗證失敗) { return 實際問題，保留既有輸出; }
  只陳述實際完成檢查，不推定符合性。
  return 實際輸出路徑與驗證結果;
}
```

## 交付並處理選用發布

```text
function 交付並處理選用發布(驗證結果, 實際輸出, 最終選擇紀錄) {
  依主指引格式交付實際功能、URL、服務狀態、HTML／EPUB 絕對路徑與用法。
  附全文、目錄與書目連結；省略缺少成果，替換全部範本變數。
  if (只有 EPUB) { return 已交付 EPUB，不為託管另建網站; }
  if (網站已完成本機交付) {
    依主指引取得最終 Sites 選擇。
    if (尚未明確同意) { return 保留本機成果，不發布; }
    依獨立發布流程執行。
    if (無終端成功證據) { return 實際部署狀態，不報告成功網址; }
    報告實際閱讀 URL。
  }
  return 實際交付與選用發布結果;
}
```

## 接續舊命名空間

```text
const 舊集合保護規則 = {
  不默默改 slug、移動、重新清理或重裝環境。
  textoria_migrate_paths.py 只處理經驗證且有保護措施的舊 textoria/ 命名空間，
  不是通用集合改名工具。
};
function 接續舊命名空間(登錄資料, 既有集合, 明確要求) {
  讀取目前與 textoria-digital-library 登錄檔。
  if (目標集合不明) { return 等待目標釐清; }
  if (明確要求遷移) {
    依適用的明確遷移流程處理，不擴張腳本用途。
    return 實際遷移或待決狀態;
  }
  以既有集合的實際 --output 接續。
  return 原位接續狀態;
}
```

相關文件：[範圍](intent-policy-zh-TW-function.md)、[主指引](../SKILL-zh-TW-function.md)、[書目](metadata-zh-TW-function.md)、[素材](materials-zh-TW-function.md)、[資料結構](schema-zh-TW-function.md)、[EPUB](epub-zh-TW-function.md)、[閱讀主題](theme-system-zh-TW-function.md)。
