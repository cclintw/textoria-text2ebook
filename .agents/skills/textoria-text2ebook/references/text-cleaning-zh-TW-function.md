# 編碼、擷取與文本清理

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 清理範圍

```text
const 清理範圍 = {
  轉碼、擷取、清理或重新清理前必讀。
  目前 CLI 使用 cc_text_cleaner；沒有可選的保守清理設定。
};
```

## 保存來源與工作文本

```text
const 文本保存規則 = {
  新集合工作文本為 content/全文.md；舊集合才沿用 clean/cleaned_text.md。
  詳細權責依 file-contracts-zh-TW-function.md。
  一般製書不另增轉碼／擷取報告；階段紀錄寫 state.json。
  清理完成不代表章節確認。
};
function 保存來源與工作文本(實際輸入, 集合, 人工修改狀態, 明確任務) {
  for (來源 in 實際輸入) { 檢查並保存來源副本。 }
  if (來源位元組或選項變更 && 將覆寫人工修改) {
    if (未取得明確重新清理決定) { return 等待重新清理決定，不覆寫; }
  }
  if (明確轉碼任務) {
    寫 prepared/<stem>.utf8.<ext>。
  } else if (明確擷取任務) {
    寫 intermediate/plain_text.md。
  } else {
    UTF-8 準備與擷取 Markdown 留在記憶體。
  }
  return 保存來源、唯一工作文本與階段狀態;
}
```

## 解碼與正規化

```text
const 解碼規則 = {
  實作：textoria_utf8_converter.py；Big5 解碼優先 HKSCS。
  嚴格解碼成功不保證語意正確；可疑文本仍須檢查。
  不保證所有私用字或亂碼偵測與還原；目前無自動原字形重建。
  NFKC 也會影響稍後受保護行中的相容字元與標點；保留原始檔供比較。
};
function 解碼與正規化(來源位元組) {
  for (編碼 in [UTF-8 BOM／UTF-8, Big5-HKSCS, Big5, Shift JIS, GB2312]) {
    依實作嚴格嘗試解碼。
    if (解碼成功) { 採用該結果並結束此探測迴圈。 }
  }
  if (全部嚴格探測失敗) {
    諮詢 charset-normalizer，最後回退 Big5。
  }
  將 CRLF／CR 正規化為 LF，移除 BOM 與指定控制字元。
  將 Unicode replacement character 替換為 ■，套用 NFKC。
  return 正規化文本與實際編碼診斷，不推定所有字元正確;
}
```

## 依格式擷取

| 格式 | 處理 |
|---|---|
| TXT／Markdown | 以準備後文本作為工作串流。 |
| HTML／HTM | 移除 script/style/head/svg/nav、註解；擷取標題、段落、清單、引文、表格、圖片參照。 |
| CSV | 必須以 `--text-column` 指定存在欄位；依列序用空行連接非空值。 |

```text
const 擷取限制 = {
  書目試算表另行處理；CSV 正文欄位不是書目匯入。
  不支援 XML/XHTML、PDF、DOCX 或圖片 OCR 作為正文輸入。
  HTML 不保證保留原連結目標、豐富樣式、任意巢狀標記或細緻排版，
  也不宣稱全面消毒所有可能 URL。
};
function 依格式擷取(已準備文本, 格式, 選項) {
  if (格式是 TXT 或 Markdown) {
    return 已準備文本作為工作串流;
  } else if (格式是 HTML 或 HTM) {
    依本節表格移除指定元素與註解、擷取各類內容。
    產生 Markdown 標題、簡單清單／引文、首列後有分隔列的表格與圖片參照。
    將行內文字扁平化。
    return 擷取結果與已知保真限制;
  } else if (格式是 CSV) {
    if (未以 --text-column 指定存在欄位) { return 需要有效正文欄位; }
    依列序以空行連接非空值。
    return CSV 正文串流;
  }
  return 不支援的正文格式;
}
```

## 清理文本

實作：`textoria_clean_text.py`。

| 輸入 | 輸出 |
|---|---|
| `﹃`／`﹄` | `『`／`』` |
| `﹁`／`﹂` | `「`／`」` |
| `︿`／`﹀` | `〈`／`〉` |
| `︽`／`︾` | `《`／`》` |

```text
const 清理規則 = {
  實作：textoria_clean_text.py；直排標點依本節對照表轉換。
  一般正文依 HALFWIDTH_PUNCT 轉換逗號、句號、冒號、括號、方括號、斜線等 ASCII 標點。
  直雙引號逐行交替轉開／閉直角引號；彎雙引號轉直角引號。
  移除半形空白與 tab，但保留 ASCII 字母／數字之間一個空白。
  不自動繁簡轉換、刪註腳／頁面附屬文字或修復歷史標點。
  不宣稱所有字面標記都會被辨識為損壞。
};
function 清理文本(工作串流) {
  正規化文本並轉換本節指定直排標點。
  for (行 in 工作串流) {
    if (屬於圍欄程式碼、Markdown 標題、管線表格、註腳定義或含 Markdown 圖片語法) {
      不做正文標點與空白轉換；先前正規化仍有效。
    } else {
      依清理規則處理正文標點與空白。
    }
  }
  移除行尾空白，合併過多空行，結果以一個換行結尾。
  return 清理文本，不宣稱位元組保真的 Markdown 往返;
}
```

## 記錄並轉交審閱

```text
const 診斷界線 = {
  處理統計不是每個字元正確的證據。
};
function 記錄並轉交審閱(清理結果, 處理診斷) {
  記錄所選設定、偵測編碼、正規化、規則、字元／行統計與標記數量。
  if (問題影響下一項決策) { 呈現具體問題與可比較的來源。 }
  保留來源。
  return 下一步為章節審閱，不直接生成最終成果;
}
```

相關文件：[檔案契約](file-contracts-zh-TW-function.md)、[工作流程](workflow-zh-TW-function.md)。
