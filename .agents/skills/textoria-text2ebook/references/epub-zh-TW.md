# EPUB 生成與驗證

## 選擇建置入口

```text
前提 = 文本、章節、書目與素材決定已確認。
生成命令不繞過確認點。
build_epub → 僅 EPUB。
build_fulltext_archive → 網站檢查成功後再產生 EPUB。
rebuild_site → 僅網站。
全部讀 canonical archive，不建立 SQLite。
成功 → 回傳實際 EPUB 路徑與驗證結果。
失敗候選 → 不取代既有電子書。
```

以實際直譯器與集合路徑替換 `PYTHON`、`COLLECTION_ROOT`：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task build_epub
```

## 組裝 EPUB

```text
閱讀順序 = 封面 → 書名頁 → 版權頁 → 可見目錄 → 正文。
選用項目僅來自已提供且確認素材；不虛構頁面或出版事實。
封面保留 JPEG／PNG 原位元組、正確 MIME、比例及可見封面頁。
使用階層導覽、有效 XHTML 與段落錨點。
前置頁接受 TXT／Markdown。
正文／前置頁的 Markdown 行內圖片目前會被拒絕：
  明確處理，不遺失圖片或默默下載。
ZIP 首項 = 未壓縮 mimetype。
包含 = container/package 文件、manifest、spine、navigation、資源、樣式。
副檔名 = .epub。
state.json 持久識別碼跨重建／改名保留；語言與修改時間由程式管理。
不要求使用者填技術欄位。
先寫候選檔 → 驗證成功且輸入未變才正式寫入輸出。
未追蹤／外部修改的既有 EPUB → 使用安全雜湊後綴，不默默覆寫。
```

## 解析 EPUBCheck

```text
依實作順序解析：
  --epubcheck-jar／--java。
  TEXTORIA_EPUBCHECK_JAR／TEXTORIA_JAVA。
  .textoria-text2ebook/tools/epub-tools.json。
  可用 PATH 工具。
設定的 java、epubcheck_jar 必須是實際可用路徑。
已有工具 → 使用。
需新安裝 → 依 runtime-zh-TW.md 取得批准，保留完整官方發行包與相依項目。
不改系統 Java。
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
內部檢查 = 封裝、XML、資源宣告／參照、閱讀順序、導覽、支援影像格式、段落完整性。
官方結果與符合性分開報告。
compliance_verified = true，僅限 EPUBCheck 成功執行。
未要求官方檢查且未設定 EPUBCheck → 可產生通過內部驗證的 EPUB，
                                      但須說明未驗證官方符合性。
不以內部檢查宣稱完整 EPUB 3 符合性。
```

相關文件：[執行環境](runtime-zh-TW.md)。
