# 電子書選用素材

## 詢問時機與提示

Metadata 已確認後，才詢問素材。保留已存在的素材，未重新上傳不代表刪除；首次製書必須等待使用者提供素材或明確略過。

使用以下提示：

> 請上傳以下素材，以便生成 EPUB 電子書使用；也可以提供本機檔案路徑。
>
> - 封面：`封面.jpg`、`封面.jpeg` 或 `封面.png`，RGB，建議 1600 × 2400 px。
> - 書名頁：`書名頁.txt` 或 `書名頁.md`。
> - 版權頁：`版權頁.txt` 或 `版權頁.md`。
>
> 以上皆為選用，未提供的項目就不加入。書名頁與版權頁依檔案內容排版，不另行補寫。上傳完成後請回覆「素材已提供」；若不加入任何素材，請回覆「略過素材」。

## 保存與檢查

- 封面按檔案實際類型檢查 JPG／PNG、像素尺寸與色彩模式，不能只信副檔名。圖片檢查能力不足時報告未驗證，不宣稱通過。
- 建議尺寸是本工具的輸入建議，不是 EPUB 的唯一尺寸。維持原圖比例，不擅自裁切、放大、生成或替換圖片。
- Apple Books 區分商店封面與內嵌封面。參考規範為 RGB、商店圖短邊至少 1400 px，內嵌圖不超過 560 萬像素；1600 × 2400 px 同時位於這些範圍。若要聲稱符合當時 Apple 發布要求，重新核對官方文件，不以建議尺寸取代完整驗證。
- 書名頁與版權頁只接受指定檔名的 TXT／MD；近似或多個候選檔名先列出請確認，不自行混入正文。另存時保留原格式與文字。
- 使用者提供附件後，複製到書籍的 `materials/`，記錄原名、來源、相對路徑及 SHA-256。只使用已保存副本生成成果，不依賴暫存附件路徑。若已有同名不同內容的素材，保留原檔，明確處理更換，不能靜默覆寫。
- 書名頁、版權頁的內容不自動回填或覆蓋已確認 metadata；有影響書名或作者的衝突時顯示差異供確認。
- 收到檔案後只報告實際完成的檢查結果；未提供項目省略，不建立空白頁或虛構版權內容。

封面參考：[Apple Books Book Cover Art](https://help.apple.com/itc/booksassetguide/en.lproj/itc1bda991ba.html)。

## 接收、完成與略過指令

章節及 metadata 尚未確認時，素材指令先回傳對應上游審查，不會越過流程接收素材。以下的 `PYTHON` 是已檢查的環境執行檔，`COLLECTION_ROOT` 是書籍根目錄。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_materials
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --material TITLEPAGE_PATH --material COPYRIGHT_PATH
```

每個 `--material` 只對應一個實際已提供的檔案；省略未提供項目，不填假路徑。程式依指定檔名分類，`.txt`／`.md`、`.jpg`／`.jpeg`／`.png` 的副檔名不分大小寫；同一項出現多個候選檔案時停止，請先選定。保存後的版本檔名可帶校驗碼後綴，初次接收名稱仍須符合規則。

`receive_materials` 先完成整批新檔的格式／內容檢查，再保存副本。回傳實際 `files`、`missing`、檔案連結、檢查結果及 `materials_token`；狀態通常為 `needs_materials`，退出碼 2 表示等待素材提供完成。Agent 在對話中列出實際接收項目與檢查結果，不宣稱未執行的完整影像解碼或 EPUB 相容驗證。

使用者明確回覆「素材已提供」、或已明確指示以這批素材完成時，Agent 可使用檢查後的目前版本確認，不必另加一次相同問題；若只有部分上傳而完成意圖不明，保留 pending，等待完成或略過。技術 token 不作為使用者要填的欄位。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_materials --materials-token MATERIALS_TOKEN
```

成功回傳 `materials_confirmed`、`next_step: generate`，保存目前選擇及未提供項目的略過狀態。此命令不生成 EPUB，也不建立空白書名頁、版權頁。尚未接收任何素材不能用完成確認默認為略過，必須是使用者明確選擇略過。

若使用者回覆「略過素材」，執行：

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task skip_materials
```

首次無素材時記錄 skipped，不建立 `materials/`。既有書籍中略過代表不新增，沿用已保存的選擇；不刪除素材、不自動移除某頁。部分提供且已完成時，缺少的其他項目會標示 skipped。

## 更換、衝突與失效

同一項素材內容不同時，接收預設停止，不能靜默換檔。使用者明確要求更換後，才使用 `--replace-material cover`、`titlepage` 或 `copyright`，舊副本與選擇歷史保留，新版本重新核對。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --replace-material cover
```

書名頁的第一層書名標題、以及兩種文字頁中明確標示的書名／作者／編者／校註者／校訂者，會與 metadata 比較。程式碼示例中的標題與欄位不參與比較。差異回傳 `needs_material_conflict_confirmation`，保存原文但不自動更正，Agent 列出兩邊內容請使用者決定。修正 metadata 或素材後重新核對；只有使用者明確要求保留差異，才在確認目前素材版本時使用 `--accept-material-conflicts`。略過不能繞過未解決的差異。

素材確認綁定目前 metadata 版本、選用檔案路徑與 SHA-256；舊 token 不能確認新版本。每次下游建置重查保存檔，遺失或內容改動時回傳待處理，保留既有生成成果，不默認把缺檔視為使用者不要。修復原件或明確更換後才繼續。不存在的檔案不提供假連結。

## 圖片與文字驗證範圍

PNG 檢查 magic、chunk CRC、尺寸、RGB／RGBA 色彩類型、壓縮資料與列長／過濾器；JPEG 檢查容器及 frame 尺寸／通道資訊。macOS 可用 `sips` 時另外比對實際格式、尺寸與色彩資訊；其他環境如無額外解碼器，JPEG 必須明確記錄尚未完整解碼像素，不宣稱已通過完整影像或 Apple 上架驗證。此階段沒有新增 Pillow 依賴。

實際副檔名與格式不符、非 RGB 圖片、空白或不可辨識的文字會停止。小於建議尺寸或超過 Apple 參考像素上限時記錄實際提示，不擅自轉檔或修改原圖，也不把建議尺寸當唯一格式。文字支持 UTF-8、帶 BOM 的 UTF-16 及可辨識的其他編碼，保存原始位元組與原副檔名；生成時的 UTF-8 排版轉換屬後續匯出階段。
