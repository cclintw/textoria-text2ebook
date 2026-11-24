# EPUB 生成與驗證

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 選擇建置入口

```text
const EPUB入口規則 = {
  build_epub 僅產生 EPUB；rebuild_site 僅產生網站。
  build_fulltext_archive 先建網站，網站檢查成功後才產生 EPUB。
  各入口使用 canonical archive，不建立 SQLite，也不繞過審閱確認。
};
function 選擇建置入口(要求輸出, 文本與章節狀態, 書目狀態, 素材決定) {
  if (任一必要確認缺少或已失效) { return 等待對應確認; }
  if (只要求 EPUB) {
    依本節命令執行 build_epub。
  } else if (要求網站及 EPUB) {
    執行 build_fulltext_archive。
  } else if (只要求網站) {
    執行 rebuild_site。
  } else { return 等待輸出需求釐清; }
  if (建置失敗) { return 實際失敗結果，失敗候選不替換既有電子書; }
  return 實際生成路徑與驗證結果;
}
```

以實際直譯器與集合路徑替換 `PYTHON`、`COLLECTION_ROOT`：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub
```

## 組裝 EPUB

```text
const EPUB封裝規格 = {
  閱讀順序：封面、書名頁、版權頁、可見目錄、正文。
  選用頁面僅取自已提供且確認素材，不虛構頁面或出版事實。
  封面保留 JPEG／PNG 原始位元組、正確 MIME、比例及可見封面頁。
  使用階層導覽、有效 XHTML、段落錨點；前置頁接受 TXT／Markdown。
  ZIP 首項為未壓縮 mimetype；含 container/package 文件、manifest、spine、navigation、資源、樣式。
  輸出副檔名為 .epub；state.json 持久識別碼跨重建與改書名保留。
  語言與修改時間由程式管理，不要求使用者填技術欄位。
};
function 組裝_EPUB(已確認內容, 已確認素材, 持久識別碼, 既有輸出紀錄) {
  if (正文或前置頁含 Markdown 行內圖片) {
    return 需要明確處理，不遺失圖片或默默下載;
  }
  依 EPUB 封裝規格寫入候選檔，省略不存在的選用項目。
  執行驗證，並再次確認輸入未變。
  if (驗證失敗或輸入改變) { return 保留既有電子書，不以候選替換; }
  if (既有 EPUB 未追蹤或被外部修改) {
    選擇安全雜湊後綴輸出名稱，不默默覆寫。
  }
  正式寫入已驗證候選。
  return 實際 EPUB 路徑與驗證證據;
}
```

## 解析 EPUBCheck

```text
const EPUBCheck解析來源 = {
  依實作順序：--epubcheck-jar／--java、TEXTORIA_EPUBCHECK_JAR／TEXTORIA_JAVA、
  .textoria-text2ebook/tools/epub-tools.json、可用 PATH 工具。
  設定 java、epubcheck_jar 必須為實際可用路徑。
};
function 解析_EPUBCheck(命令參數, 環境變數, 專案設定, PATH) {
  依上述來源與實作順序解析工具。
  if (工具可用) { return 實際 Java 與 EPUBCheck 路徑; }
  依 runtime-zh-TW-function.md 處理安裝批准與完整官方發行包、相依項目保存。
  不改系統 Java。
  if (安裝尚未批准或工具仍不可用) { return 工具未就緒，不宣稱已執行官方驗證; }
  return 經檢查可用的工具路徑;
}
```

生成時要求官方驗證：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub --require-epubcheck
```

獨立驗證現有電子書；`BOOK.epub`、`PROJECT` 必須換成實際路徑：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate_epub.py BOOK.epub --project-root PROJECT --require-epubcheck
```

## 陳述驗證結果

```text
const 內部驗證範圍 = {
  封裝、XML、資源宣告／參照、閱讀順序、導覽、支援影像格式與段落完整性。
};
function 陳述驗證結果(內部檢查, 官方檢查結果, 是否要求 EPUBCheck) {
  分別報告內部驗證與官方檢查。
  if (EPUBCheck 成功執行並通過) {
    compliance_verified = true。
  } else {
    compliance_verified = false。
    說明官方符合性未驗證，不以內部檢查宣稱完整 EPUB 3 符合性。
  }
  if (要求官方驗證 && 未成功通過) { return 未滿足必要驗證，不正式交付候選為成功成果; }
  if (未要求官方驗證 && 內部檢查通過 && 未設定 EPUBCheck) {
    return 可產生內部驗證 EPUB，明列官方符合性未驗證;
  }
  return 實際檢查範圍與結果;
}
```

相關文件：[執行環境](runtime-zh-TW-function.md)。
