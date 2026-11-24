# 靜態閱讀主題

## 維護主題

```text
來源 = Skill 的 themes/default/。
保留白底、色彩、字體、閱讀寬度、間距與章節配置。
一般製書不套用其他設計系統、不翻譯介面字串。
共享範本／腳本集中修改，不只修補單本生成網站。
```

## 維持閱讀互動

```text
頁首：
  保留章節開關與指向閱讀入口的書名。
  不加入頂層 Home／Browse／Search 導覽選單。
搜尋：
  右側 Find 在頁首右上方下方開啟浮層。
  搜尋留在閱讀畫面，不取代章節側欄。
  使用全書腳本索引；再次開啟時恢復查詢與結果。
  點結果 → 關閉浮層、開啟目標段落、標示符合文字，不開側欄。
  點外部或 Escape → 關閉但不清除查詢。
  以 sessionStorage 逐書保存；儲存不可用時用查詢參數跨頁延續。
章節側欄：
  初始關閉。
  桌面跨章節保留同分頁的開關偏好。
  行動版選章後關閉，包括同頁錨點；縮放不覆寫桌面偏好。
樹狀分支：
  展開狀態與側欄可見性分開保存。
  導航或重開側欄 → 展開目前章節路徑並標示，保留其他分支狀態。
  同章節內持續捲動 → 不反覆推翻人工收合。
```

## 路由與資源

保留下列實際檔案：

```text
index.html
read.html
search.html
read/<top-level-division-id>.html
assets/css/style.css
assets/js/reader.js
assets/js/reader-search.js
data/search_index.js
```

```text
巢狀分區與段落使用頁面錨點。
search.html 是同一閱讀器的相容入口，不是獨立主搜尋畫面。
search_index.js 必須先於閱讀搜尋介面載入。
不改為依賴 fetch 的 JSON，維持 file:// 可用。
textoria_build_site.py 從 archive 渲染範本。
標準網站使用靜態 HTML／CSS／JavaScript；不需後端或前端框架。
一般製書不額外加入後端或框架。
```

## 交付與驗證主題

```text
主要閱讀檔／URL = read.html。
index.html = 書籍介紹。
目前靜態主題不呈現選用 EPUB 前置頁或 EPUB 下載按鈕。
生成 EPUB → 在對話提供實際檔案連結。
相關主題變更後 → 驗證受影響頁、相對資源、索引載入、結果錨點與互動狀態。
純主題更新 → 不重新清理正文、不重開未變的章節／書目審閱。
```
