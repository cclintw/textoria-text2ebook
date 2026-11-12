# EPUB 製作與驗證

## 執行入口

使用已確認的正文、章節、metadata 與素材。各確認停點不能由生成指令略過。`PYTHON` 為已就緒的專案虛擬環境 Python，`COLLECTION_ROOT` 為書籍工作目錄。

```sh
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub --require-epubcheck
```

`build_epub` 只產生 EPUB；`build_fulltext_archive` 產生網站並在網站檢查成功後產生 EPUB。`rebuild_site` 仍只重建網站。成功結果包含實際 EPUB 路徑與驗證資訊，驗證失敗不取代既有電子書。

## 內容與封裝

- 依序排列封面、書名頁、版權頁、可見目錄、正文。選用頁面僅取自已確認素材；未提供時省略，不生成空頁或補寫出版資料。
- 封面保留原始 PNG／JPEG 位元組，manifest 使用相應 MIME，另建立可見封面頁並保留比例。
- 使用階層章節目錄、有效 XHTML 與段落錨點。文字頁支援 TXT／Markdown；內嵌圖片目前不支援，遇到圖片標記應先處理，不能默默遺失圖片或下載外部資源。
- EPUB 使用 ZIP 容器，首項為未壓縮的 `mimetype`，包含 container、package、manifest、spine、導覽與樣式。副檔名為 `.epub`。
- 識別碼保存於 `state.json`，改書名或重建仍沿用；語言與修改時間由程式管理。外部下載檔名可使用中文書名，內部資源採安全路徑。
- 電子書先寫入候選檔，驗證成功且輸入未異動才發布。未追蹤或經外部修改的同名檔保留，另用雜湊後綴命名；不能安全命名時停止。

## 驗證器設定

依序使用明確參數 `--epubcheck-jar`／`--java`、環境變數 `TEXTORIA_EPUBCHECK_JAR`／`TEXTORIA_JAVA`、專案 `.textoria-text2ebook/tools/epub-tools.json`，以及可用的 PATH 驗證器。設定檔中的 `java`、`epubcheck_jar` 為實際可用的檔案路徑。

工具已可用時直接使用；新增 Java／驗證器須遵守環境安裝授權。採專案工具目錄保存完整官方 EPUBCheck 發行包與相依函式庫，不更改系統 Java 設定。

獨立檢查既有 EPUB：

```sh
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_validate_epub.py BOOK.epub --project-root PROJECT --require-epubcheck
```

內部檢查涵蓋封裝、XML、資源宣告、閱讀順序、目錄參照、圖片格式與段落完整性。EPUBCheck 的實際狀態、訊息與版本另行記錄；只有實際執行成功時 `compliance_verified` 才為真。未設定驗證器且未指定 `--require-epubcheck` 時，可生成經內部檢查的成果，但必須說明未通過官方驗證。正式宣稱 EPUBCheck 通過前，使用 `--require-epubcheck`。

原始外掛快照保存在 `epub-reference/textoria-plugin/`，僅供來源比較，不能整套覆寫現行共用程式。
