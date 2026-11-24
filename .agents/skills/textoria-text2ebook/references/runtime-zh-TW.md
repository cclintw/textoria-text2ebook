# 執行環境與相依套件

## 執行需求

```text
執行本機 Textoria 腳本前必讀。
Python >= 3.10。
預設環境 = .textoria-text2ebook/venv/。
必要套件 = charset-normalizer、beautifulsoup4、jinja2、markdown-it-py、pypinyin。
Java 與完整 EPUBCheck 發行包 → 僅官方 EPUBCheck 驗證需要。
標準網站／EPUB → 不需 SQLite 或 FTS5；不安裝額外分詞、繁簡轉換或測試套件。
```

## 選擇並檢查環境

```text
優先沿用相容的 .textoria-text2ebook/venv/。
不存在時 → 可驗證並原地沿用 .textoria-digital-library/venv/。
Skill 改名不授權移動或重建環境。
.textoria/venv/ → 需明確遷移流程；啟動器含絕對路徑，不可直接改名。
以選定環境的實際 Python 路徑替換 PYTHON，執行下列命令。
```

```text
PYTHON .agents/skills/textoria-text2ebook/scripts/textoria_runtime_check.py
```

```text
結果 = Python 與套件可用性。
此檢查不建立環境、不安裝套件、不另寫環境日誌。
環境就緒 → 直接使用。
僅對明確授權的資料庫任務 → 加 --check-sqlite 檢查 FTS5。
```

## 補足缺少需求

```text
安裝 Python、建立環境或安裝套件前：
  顯示實際缺少項目與目的地。
  依主指引互動規則取得明確批准；單獨提問，不混合章節或書目確認。
  不使用禁止授權問題的提問工具。
已批准同一安裝 → 不重複詢問。
獲准 → 以確認的 Python 建立環境，僅安裝至該環境，不裝入系統 Python。
Python 本身缺少 → 指出合適安裝來源或詢問既有路徑，不自動安裝。
設定成功 → 自動接續原任務，除非要求僅設定環境。
```

下列命令僅於獲准後使用：

```text
python3 -m venv .textoria-text2ebook/venv
.textoria-text2ebook/venv/bin/python -m pip install charset-normalizer beautifulsoup4 jinja2 markdown-it-py pypinyin
```

## 準備 EPUBCheck

```text
優先使用 .textoria-text2ebook/tools/epub-tools.json 中的實際路徑。
不修改系統 Java 設定。
現有或已授權工具 → 不再提出等同的批准要求。
需新安裝 → 先取得批准，再取得完整官方 EPUBCheck 發行包及相依項目。
官方提供校驗碼時 → 核對下載檔案。
在專案工具目錄保留授權檔。
解析順序、命令及驗證陳述 → 依 epub-zh-TW.md。
```

相關文件：[互動規則](../SKILL-zh-TW.md)、[EPUB](epub-zh-TW.md)。
