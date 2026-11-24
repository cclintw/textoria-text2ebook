# 執行環境與相依套件

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 執行需求

```text
const 執行需求 = {
  執行本機 Textoria 腳本前必讀。
  Python >= 3.10。
  預設環境 = .textoria-text2ebook/venv/。
  必要套件 = charset-normalizer、beautifulsoup4、jinja2、markdown-it-py、pypinyin。
  Java 與完整 EPUBCheck 發行包 → 僅官方 EPUBCheck 驗證需要。
  標準網站／EPUB → 不需 SQLite 或 FTS5；不安裝額外分詞、繁簡轉換或測試套件。
};
```

## 選擇並檢查環境

```text
const 環境保護規則 = {
  Skill 改名不授權移動或重建環境。
  .textoria/venv/ 必須走明確遷移流程；啟動器含絕對路徑，不直接改名。
  檢查只回報 Python 與套件可用性，不建立環境、安裝套件或另寫日誌。
};
function 選擇並檢查環境(專案, 既有環境, 已授權任務) {
  if (.textoria-text2ebook/venv/ 存在且相容) {
    選擇該環境。
  } else if (.textoria-digital-library/venv/ 可驗證且相容) {
    原地沿用該環境。
  } else {
    return 缺少可用環境，轉入安裝批准流程;
  }
  以選定環境的實際 Python 路徑替換 PYTHON。
  if (已明確授權資料庫任務) {
    在本節檢查命令加 --check-sqlite，以檢查 FTS5。
  }
  執行本節環境檢查命令。
  if (環境就緒) { return 可直接使用的 Python 路徑; }
  return 實際缺少需求，不自動安裝;
}
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py
```

## 補足缺少需求

```text
const 安裝規則 = {
  不安裝至系統 Python；以已確認的 Python 建立專案環境。
  批准問題單獨提出，不混合章節或書目確認；不用禁止授權問題的工具。
  同一安裝已有批准時不重複詢問。
};
function 補足缺少需求(缺少項目, 安裝目的地, 保存批准, 原任務) {
  if (同一安裝尚未取得明確批准) {
    顯示實際缺少項目與目的地，依主指引互動規則詢問。
    return 等待安裝批准;
  }
  if (Python 本身缺少) {
    指出合適安裝來源或詢問可用 Python 路徑，不自動安裝。
    return 等待已授權的 Python 準備;
  }
  依已批准目的地執行本節環境建立與套件安裝命令。
  重新檢查環境。
  if (仍缺少需求或安裝失敗) { return 實際問題，不宣稱已就緒; }
  if (原任務不只要求設定環境) { 接續原任務。 }
  return 已就緒環境;
}
```

下列命令僅於獲准後使用：

```text
python3 -m venv .textoria-text2ebook/venv
.textoria-text2ebook/venv/bin/python -m pip install charset-normalizer beautifulsoup4 jinja2 markdown-it-py pypinyin
```

## 準備 EPUBCheck

```text
const 工具保存規則 = {
  不修改系統 Java 設定。
  保留完整官方 EPUBCheck 發行包、相依項目與專案工具目錄內的授權檔。
  解析順序、命令與驗證陳述依 epub-zh-TW-function.md。
};
function 準備_EPUBCheck(工具設定, 現有工具, 保存批准) {
  優先檢查 .textoria-text2ebook/tools/epub-tools.json 中的實際路徑。
  if (工具已可用) { return 可用工具路徑，不重複要求批准; }
  if (同一工具安裝尚未批准) {
    顯示安裝需求並詢問。
    return 等待安裝批准;
  }
  取得完整官方發行包與相依項目。
  if (官方提供校驗碼) {
    核對下載檔案。
    if (校驗失敗) { return 工具檔案不可使用; }
  }
  保留授權檔並檢查工具可執行性。
  return 實際可用路徑，或尚未解決的工具需求;
}
```

相關文件：[互動規則](../SKILL-zh-TW-function.md)、[EPUB](epub-zh-TW-function.md)。
