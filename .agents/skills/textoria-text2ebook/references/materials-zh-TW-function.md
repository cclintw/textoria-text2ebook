# EPUB 選用素材

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 詢問素材

```text
const 素材詢問規則 = {
  本節表格檔名為固定契約，副檔名不分大小寫。
  素材不得為空或超過 32 MiB；名稱相近或多候選需釐清。
  素材目前只出現在 EPUB，不在靜態閱讀頁。
  缺項省略，不生成封面、空白頁或出版文字。
  既有素材即使未重新附上仍保留；選擇提供不代表接收完成。
};
function 詢問素材(章節狀態, 書目狀態, 已保存素材, 保存決定) {
  if (章節或書目尚未確認) { return 等待前置確認; }
  if (目前選擇已有有效確認或明確略過) { return 保存的有效決定; }
  列出表格中的選用素材與既有檔案，提供沿用／替換／提供／略過選擇。
  說明接受附件或本機路徑，不以純文字提問工具要求上傳。
  使用者回覆 = 等待使用者回覆。
  if (尚未回覆) { return 等待素材選擇; }
  if (取消或暫停) { return 保留素材，停止本次接收; }
  if (選擇提供) { return 開始接收，仍需明確完成通知; }
  return 實際明確選擇，不推定接收完成;
}
```

| 素材 | 固定接受檔名 | 要求 |
|---|---|---|
| 封面 | `封面.jpg`、`封面.jpeg`、`封面.png` | RGB 相容 JPEG／PNG；建議 1600 × 2400 像素。 |
| 書名頁 | `書名頁.txt`、`書名頁.md` | 可讀且非空文字。 |
| 版權頁 | `版權頁.txt`、`版權頁.md` | 可讀且非空文字。 |

## 接收並保存

以實際直譯器、集合與素材路徑替換下列符號；僅傳入已提供素材，省略未使用參數。

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task review_materials
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --material TITLEPAGE_PATH --material COPYRIGHT_PATH
```

```text
const 素材保存規則 = {
  保留原始位元組、格式、名稱、來源／保存路徑、SHA-256 與檢查結果。
  同名內容改變時版本化另存，不覆寫；附件暫存路徑不是永久保存。
  receive_materials 的結束碼 2 通常表示等待完成決定。
};
function 接收並保存(實際提供檔案, 集合) {
  if (沒有實際檔案) { return 等待提供檔案，不虛構路徑; }
  先檢查整批輸入。
  if (任一檔案不合格) { return 實際問題，不保存不合格批次; }
  依本節命令執行 receive_materials，只傳實際提供檔案。
  核對 materials/ 保存副本、檔案、缺項、checks、links 與 materials_token。
  只報告實際完成檢查。
  return 實際保存與檢查結果，等待完成決定;
}
```

## 確認或略過

```text
const 素材決定規則 = {
  已明確以這批完成時，不追加等同問題。
  沒有檔案但說完成不等於略過；未明確完成時維持待確認。
  首次略過不建空資料夾；既有集合略過只是不新增，保留原選擇與素材。
  部分提供且明確完成時省略其他缺項。
  確認只保存選擇，不直接生成 EPUB。
};
function 確認或略過(明確決定, 目前素材 token, 保存檔案與書目, 檢查結果) {
  if (取消或暫停) { return 保留素材，停止本次處理; }
  if (存在未解衝突) { return 等待衝突處理，略過不能繞過衝突; }
  if (明確略過) {
    只執行本節 skip_materials 命令。
    return 命令實際記錄的略過結果;
  } else if (明確完成 && 檢查成功 && token 對應目前檔案與書目) {
    只執行本節 confirm_materials --materials-token 命令。
    return 命令實際記錄的確認結果;
  }
  return 等待目前素材完成決定，不連續執行確認與略過兩命令;
}
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task confirm_materials --materials-token MATERIALS_TOKEN
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task skip_materials
```

## 處理替換與衝突

```text
const 素材比對依據 = {
  書名頁 H1 及明確標示書目行與已確認書目比對；忽略圍欄範例。
  目前行比對使用程式中文欄位標籤。
  替換鍵：cover、titlepage、copyright；保留舊副本與選擇歷史。
};
function 處理替換與衝突(新選擇, 已確認書目, 保存素材, 明確指示) {
  if (保存檔案遺失或變更 || 綁定書目改變) {
    使原選擇失效，阻擋下游輸出替換直到解決。
  }
  if (要替換素材) {
    if (缺少明確替換指示) { return 等待替換決定; }
    使用本節 --replace-material 命令，選擇對應替換鍵。
  }
  依素材比對依據檢查差異。
  if (有差異) {
    顯示差異，不改寫來源或書目。
    if (差異尚未解決且無明確保留差異指示) { return 等待衝突處理; }
    if (已明確同意保留差異) {
      僅在目前確認中使用 --accept-material-conflicts。
    }
  }
  return 目前可審閱素材選擇與歷史，不以略過繞過未解衝突;
}
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_build.py --output COLLECTION_ROOT --task receive_materials --material COVER_PATH --replace-material cover
```

## 檢查素材

```text
const 素材檢查範圍 = {
  PNG：簽章、chunk CRC、尺寸、RGB／RGBA 色彩型別、解壓列與濾波器。
  JPEG：容器、frame 尺寸／通道；本檢查不完整解碼所有像素。
  文字：UTF-8、有 BOM 的 UTF-16 或其他可靠解碼的編碼。
  保留原始位元組與副檔名；EPUB 生成時才轉 UTF-8 排版。
};
const 圖片保護規則 = {
  保留比例，不自動裁切、放大、轉換或替換封面。
  建議尺寸不是唯一有效 EPUB 尺寸，也不是目前商店規格的依據。
};
function 檢查素材(原始素材檔) {
  if (PNG 或 JPEG) {
    依素材檢查範圍執行對應檢查。
    if (macOS sips 可用) { 額外核對格式、尺寸與色彩空間。 }
  } else if (文字素材) {
    可靠解碼並檢查是否非空與無控制字元損壞。
  }
  if (不可讀、空白、損壞或其他檢查失敗) { return 拒收與實際原因; }
  return 實際檢查範圍與結果，不宣稱未驗證的完整解碼或商店送審符合性;
}
```
