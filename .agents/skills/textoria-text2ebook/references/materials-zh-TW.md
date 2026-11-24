# EPUB 選用素材

## 詢問素材

```text
前提 = 章節與書目皆已確認。
列出選用素材，提供「提供／略過」；已有素材則顯示沿用／替換選擇。
接受附件或本機路徑；不以僅支援文字的提問工具要求上傳。
素材只影響目前 EPUB，不出現在靜態閱讀頁。
缺項 → 省略；不生成封面、空白頁或出版文字。
既有素材未再次附上仍保留。
選擇「提供」不代表接收完成；等待明確完成通知。
```

| 素材 | 固定接受檔名 | 要求 |
|---|---|---|
| 封面 | `封面.jpg`、`封面.jpeg`、`封面.png` | RGB 相容 JPEG／PNG；建議 1600 × 2400 像素。 |
| 書名頁 | `書名頁.txt`、`書名頁.md` | 可讀且非空文字。 |
| 版權頁 | `版權頁.txt`、`版權頁.md` | 可讀且非空文字。 |

```text
副檔名不區分大小寫；固定檔名不改寫。
名稱相近或多個候選 → 釐清，不猜測。
拒絕空檔或超過程式 32 MiB 上限的檔案。
```

## 接收並保存

以實際直譯器、集合與素材路徑替換下列符號；僅傳入已提供素材，省略未使用參數。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_materials
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --material TITLEPAGE_PATH --material COPYRIGHT_PATH
```

```text
先驗證整批，再保存至 materials/。
保留 = 原始位元組、格式、名稱、來源／保存路徑、SHA-256、檢查結果。
同名但內容改變 → 版本化另存，不覆寫。
回傳 = 檔案、缺項、檢查、連結、materials_token。
結束碼 2 通常表示等待完成決定。
只報告實際檢查；附件暫存路徑不是永久保存。
```

## 確認或略過

```text
明確完成且檢查成功 → 使用目前綁定檔案與書目的 token 執行 confirm_materials。
已明示以這批完成 → 不再等同追問。
完成與否不明 → 保持待確認。
沒有檔案但說完成 → 不推定為略過。
明確略過 → 執行 skip_materials。
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_materials --materials-token MATERIALS_TOKEN
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task skip_materials
```

```text
上述兩命令為不同分支，不連續執行。
首次略過 → 不建空資料夾。
既有集合略過 → 不新增，保留既有選擇，不刪頁面或素材。
部分接收且明確完成 → 省略其他缺項。
確認只保存選擇，不自行產生 EPUB。
```

## 處理替換與衝突

```text
替換需要明確指示；保留舊副本與選擇歷史。
替換鍵 = cover、titlepage、copyright。
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --replace-material cover
```

```text
比較書名頁 H1、明確標示的書目行與已確認書目；忽略圍欄範例。
目前逐行比對使用程式的中文欄位標籤。
發現差異 → 顯示，不改寫來源或書目。
解決差異，或取得保留差異的明確指示後，
  才於本次確認使用 --accept-material-conflicts。
略過不能繞過未解衝突。
保存檔案遺失／變更或書目變更 → 原選擇失效，阻擋下游替換直到解決。
```

## 檢查素材

```text
PNG = 簽章、chunk CRC、尺寸、RGB／RGBA 色彩型別、解壓列、濾波器。
JPEG = 容器與 frame 尺寸／通道；此檢查本身不完整解碼所有像素。
macOS sips 可用時 → 額外檢查格式、尺寸與色彩空間。
只陳述實際範圍；未做相應檢查，不宣稱完整影像解碼或商店送審符合性。
保留圖片比例；不自動裁切、放大、轉換或替換封面。
建議尺寸不是唯一有效 EPUB 尺寸，也不是目前各商店規格的依據。
文字接受 UTF-8、有 BOM 的 UTF-16 及其他可靠解碼的編碼。
保留原始位元組與副檔名；EPUB 生成時才轉 UTF-8 排版。
拒絕不可讀、空白或控制字元損壞的文字。
```
