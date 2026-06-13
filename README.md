# 台股國運基金 · 00631L Dashboard

合資定期定額投資 00631L（元大台灣50正2）的即時儀表板與管理系統。

## 功能

- **📊 即時儀表板** — 總覽資產、持股比重、指數比較、歷史淨值
- **📋 團員管理** — 各成員投資明細、報酬率
- **📄 基金 Factsheet** — 完整投資策略與規則說明

## 連結

- [📊 即時儀表板](https://asdfghjkl010100.github.io/00631l-2000w/)
- [📄 Google Sheets 資料源](https://docs.google.com/spreadsheets/d/11YFB8SQk-0QYW4NbYXzdv8WrMDkuQG2inYflXdtwJgI/edit?usp=sharing)
- [📄 Fund Factsheet](台股國運基金_Factsheet_sanitized.docx)

## 技術架構

- 純前端靜態頁面（HTML + Chart.js）
- 資料來源：Google Sheets CSV（發布到網路）
- 部署：GitHub Pages
- 無需後端伺服器

---

## 🤖 LINE Bot 自動通知

Google Sheets 資料有更新時，會自動透過 LINE Bot 推播通知到群組。

### 功能

- 📊 **即時查詢** — 在 LINE 輸入「查詢」取得基金總覽
- 👤 **團員明細** — 輸入「查 團員名稱」查詢個別團員
- 🔔 **自動推播** — 資料變更時自動發送更新通知

### 部署方式

1. 到 [LINE Developers Console](https://developers.line.biz/console/) 建立 Messaging API Channel
2. 取得 Channel Secret 與 Channel Access Token
3. 將 Bot 加入群組，取得群組 ID
4. 複製 .env.example 為 .env 並填入設定
5. 部署到 Render / Heroku / Fly.io 等平台

### 技術架構

- **Flask** — Webhook 伺服器
- **LINE Messaging API SDK** — LINE Bot 整合
- **APScheduler** — 定期檢查 Google Sheets 變更
- **Google Sheets CSV** — 資料來源（與前端共用）

| 檔案 | 說明 |
|------|------|
| linebot/app.py | Flask Webhook 主程式 |
| linebot/sheets_monitor.py | Google Sheets 擷取與變更偵測 |
| linebot/messages.py | LINE 訊息模板 |
| linebot/config.py | 設定檔 |
| linebot/monitor_worker.py | 獨立監控 Worker |
| .env.example | 環境變數範本 |
| Procfile | 平台部署設定 |
| equirements.txt | Python 相依套件 |
