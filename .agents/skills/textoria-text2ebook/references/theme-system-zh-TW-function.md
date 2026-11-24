# 靜態閱讀主題

本文件由 Agent 依類腳本結構解讀；實際命令與執行前提依各節規定。

## 維護主題

```text
const 維護主題 = {
  來源 = Skill 的 themes/default/。
  保留白底、色彩、字體、閱讀寬度、間距與章節配置。
  一般製書不套用其他設計系統、不翻譯介面字串。
  共享範本／腳本集中修改，不只修補單本生成網站。
};
```

## 維持閱讀互動

```text
const 閱讀互動規格 = {
  頁首保留章節開關與指向閱讀入口的書名；不加頂層 Home／Browse／Search 選單。
  Find 浮層位於頁首右上方下方；搜尋留在閱讀畫面，不取代側欄。
  搜尋使用全書腳本索引，sessionStorage 逐書保存；不可用時以查詢參數跨頁延續。
  側欄初始關閉；桌面偏好在同分頁保存，縮放不覆寫桌面偏好。
  樹狀分支展開與側欄可見性分開保存，保留其他分支狀態。
};
function 維持閱讀互動(閱讀頁, 同分頁狀態, 使用者操作) {
  if (開啟 Find) {
    開啟搜尋浮層並恢復查詢與結果。
  } else if (點擊搜尋結果) {
    關閉浮層、開啟目標段落並標示符合文字，不開章節側欄。
  } else if (點浮層外部或按 Escape) {
    關閉浮層但不清除查詢。
  }
  if (桌面切換側欄) { 保存同分頁的開關偏好。 }
  if (行動版選擇章節，包括同頁錨點) { 關閉側欄。 }
  if (導航章節或重開側欄) {
    展開目前章節路徑並標示，保留其他分支狀態。
  }
  if (在同章節持續捲動) { 不反覆推翻人工收合。 }
  return 遵循規格的閱讀互動狀態;
}
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
const 路由與資源 = {
  巢狀分區與段落使用頁面錨點。
  search.html 是同一閱讀器的相容入口，不是獨立主搜尋畫面。
  search_index.js 必須先於閱讀搜尋介面載入。
  不改為依賴 fetch 的 JSON，維持 file:// 可用。
  textoria_build_site.py 從 archive 渲染範本。
  標準網站使用靜態 HTML／CSS／JavaScript；不需後端或前端框架。
  一般製書不額外加入後端或框架。
};
```

## 交付與驗證主題

```text
const 主題交付規格 = {
  主要閱讀入口：read.html；書籍介紹：index.html。
  目前靜態主題不呈現選用 EPUB 前置頁或 EPUB 下載按鈕。
  純主題更新不重新清理正文，也不重開未變章節／書目審閱。
};
function 交付與驗證主題(受影響頁面, 主題變更, 已生成 EPUB) {
  驗證受影響頁面、相對資源、索引載入、結果錨點與互動狀態。
  if (驗證失敗) { return 需修正的實際問題，不宣稱完成; }
  交付主要閱讀檔案／URL。
  if (已生成 EPUB) { 在對話提供實際檔案連結。 }
  return 實際閱讀入口與受影響範圍的檢查結果;
}
```
