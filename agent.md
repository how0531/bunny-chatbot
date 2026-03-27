# AI 投資助理團隊架構與功能藍圖 v2.0

本文件定義虛擬代理人 (Agents) 職責、技能矩陣與功能專案的開發規劃，目標是打造市場上最實用、每日必備的 AI 投資工具。

---

## 🕵️‍♂️ 虛擬投資團隊 (The Agent Squad)

### 1. 👩‍💼 Sophia (蘇菲亞) - 專案總監 & 用戶窗口

> _"Your Personal Chief Investment Officer (CIO)"_

| 職責領域 | 功能描述                       | 狀態      |
| -------- | ------------------------------ | --------- |
| 意圖識別 | 解析自然語言，判斷用戶需求類型 | ✅ 已上線 |
| 任務分發 | 將請求路由至正確的Agent處理    | ✅ 已上線 |
| 報告整合 | 匯總數據成易讀的圖表與文字     | ✅ 已上線 |
| 動態決策 | 根據市場狀態調整推薦策略       | 🔄 開發中 |
| 用戶記憶 | 記住用戶偏好與歷史查詢         | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Multi-Agent Orchestration | `crewAI` | 定義代理人角色、指派任務、監督協作 |
| Final QC & Formatting | `ReportFormatter` | 確保報告兼具數據深度與美感 |

**實作位置**: `backend/app/agents/sophia_orchestrator.py`

---

### 2. 👨‍💻 Arthur (亞瑟) - 資深量化分析師

> _"The Quantitative Alpha Seeker"_

| 職責領域   | 功能描述                                 | 狀態      |
| ---------- | ---------------------------------------- | --------- |
| 多因子評分 | BunnyGood綜合評分模型 (技術/籌碼/基本面) | ✅ 已上線 |
| 數據挖掘   | 從MongoDB/ClickHouse撈取低估標的         | ✅ 已上線 |
| 市場強度   | 計算多空強度分數 (0-10)                  | ✅ 已上線 |
| 條件篩選   | 執行Dynamic Rule Engine查詢              | ✅ 已上線 |
| 技術分析   | 均線/型態識別                            | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Institutional Data Mining | `OpenBB SDK`, `yfinance` | 獲取法人級基本面與總經數據 |
| Technical Quantitative Evaluation | `TA-Lib` | 計算RSI/MACD等量化指標 |

**實作位置**: `backend/app/services/stock_service.py`, `backend/app/services/rule_engine.py`

---

### 3. 👩‍🔬 Isabella (伊莎貝拉) - 市場研究員

> _"The Qualitative Researcher (FinRobot Powered)"_

| 職責領域   | 功能描述                          | 狀態      |
| ---------- | --------------------------------- | --------- |
| 即時情報   | 網路新聞/法說會/傳聞搜尋 (Tavily) | ✅ 已上線 |
| 事件分析   | 營收公告/配息等利多利空解讀       | ✅ 已上線 |
| 概念股搜尋 | 依產業/題材查找相關標的           | ✅ 已上線 |
| 情緒分析   | 新聞情緒量化評分                  | 🔄 開發中 |
| 社群監控   | PTT/Dcard財經版爬蟲               | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Web Intelligence Ingestion | `crawl4ai` | 高效抓取財經論壇內容 |
| Financial Sentiment Decoding | `Fintwit-Sentiment` | 解析帶有金融術語的網路情緒 |

**實作位置**: `backend/app/agents/finrobot_agents.py`

---

### 4. 👮‍♂️ Oscar (奧斯卡) - 風控官 & 品管

> _"The Risk & Compliance Officer"_

| 職責領域   | 功能描述                     | 狀態      |
| ---------- | ---------------------------- | --------- |
| 防幻覺檢查 | 核對LLM數據與資料庫一致性    | ✅ 已上線 |
| 雜訊過濾   | 剔除無關新聞干擾             | ✅ 已上線 |
| 風險標籤   | 標注處置股/警示股/流動性風險 | ⏳ 待開發 |
| 回測驗證   | 策略歷史績效驗證             | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Hallucination Guardrail | `Arize Phoenix` | 監控Agent推理過程，攔截數據幻覺 |
| Strategy Backtesting | `Backtrader` | 對分析師建議進行歷史勝率驗證 |

**實作位置**: `backend/app/agents/sophia_orchestrator.py` (Review Logic)

---

### 5. 🛠️ Leo (里歐) - 全端互動工程師

> _"The Full-Stack Interaction Engineer"_

| 職責領域 | 功能描述               | 狀態      |
| -------- | ---------------------- | --------- |
| 流式UI   | 打字機效果與推理鏈展示 | ⏳ 待開發 |
| 動態圖表 | 量化數據轉化為互動圖表 | ✅ 已上線 |
| PWA支援  | 行動裝置離線存取       | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Streaming Insight UI | `Vercel AI SDK` | 實作打字機效果與推理鏈流式展示 |
| Dynamic Data Visualization | `Recharts` | 將量化數據轉化為動態圖表 |

**實作位置**: `backend/app/templates/`, `backend/app/static/js/`

---

### 6. 🧠 Diana (黛安娜) - AI策略架構師

> _"The AI Strategy Architect"_

| 職責領域   | 功能描述                 | 狀態      |
| ---------- | ------------------------ | --------- |
| 狀態管理   | 複雜任務循環流程設計     | ⏳ 待開發 |
| 工作流設計 | 審核失敗後重做的狀態轉移 | ⏳ 待開發 |

**技能矩陣**:
| Skill | Tool | Description |
|-------|------|-------------|
| Complex State Management | `LangGraph` | 設計複雜任務循環流程 |

---

## 🚀 功能專案開發規劃

### 📁 Project 1: Early Bird (每日晨報) ☀️

**目標**: 開盤前3分鐘掌握全域，決定今日攻守策略

| 功能項目     | 描述                   | 狀態 | 負責Agent |
| ------------ | ---------------------- | ---- | --------- |
| 美股收盤掃描 | 道瓊/那指/費半漲跌分析 | ✅   | Arthur    |
| 台股趨勢預測 | 加權指數支撐壓力位     | ✅   | Arthur    |
| 法人籌碼動向 | 外資/投信前日佈局      | ✅   | Arthur    |
| 市場溫度計   | 強度分數與紅綠燈號     | ✅   | Arthur    |

**開發計劃**:

- [ ] 增加期貨未平倉分析
- [ ] 新增VIX恐慌指數連動

**測試規劃**:

- 觸發指令: `投資早報`, `盤前報告`, `早安`
- 驗證項目: 美股數據正確性、法人數據時效性
- 成功標準: 3秒內回應、數據延遲<24小時

---

### 📁 Project 2: Eagle Eye (智慧選股) 🦅

**目標**: 用一句話找出潛力股，取代複雜的篩選器

| 功能項目     | 描述             | 狀態 | 負責Agent |
| ------------ | ---------------- | ---- | --------- |
| 自然語言篩選 | 複合條件股票篩選 | ✅   | Arthur    |
| 投信認養雷達 | 投信買超比重排序 | ✅   | Arthur    |
| 概念股搜尋   | 依產業題材查找   | ✅   | Isabella  |
| 強勢族群熱圖 | 資金流向板塊     | ✅   | Arthur    |

**開發計劃**:

- [ ] K線型態辨識 (W底、突破盤整)
- [ ] 技術指標篩選 (RSI、MACD)
- [ ] 籌碼連續天數條件

**測試規劃**:

- 觸發指令: `找出本益比<15的股票`, `封測概念股`, `投信認養`
- 驗證項目: 篩選結果準確性、概念股對應正確
- 成功標準: 10秒內回應、結果≥5檔

---

### 📁 Project 3: Deep Dive (個股深度儀表板) 📊

**目標**: 法人等級的單一股票健診報告

| 功能項目     | 描述              | 狀態 | 負責Agent  |
| ------------ | ----------------- | ---- | ---------- |
| 360度評分    | 1-10分綜合評估    | ✅   | Arthur     |
| 事件驅動分析 | 漲跌原因解析      | ✅   | Isabella   |
| 籌碼視覺化   | 買賣超圖表+累積線 | ✅   | Arthur/Leo |
| 法說會解讀   | 即時網路搜尋      | ✅   | Isabella   |
| 基本面數據   | PE/PB/ROE/殖利率  | ✅   | Arthur     |

**開發計劃**:

- [ ] 同業比較功能
- [ ] 歷史評分趨勢
- [ ] PDF報告輸出

**測試規劃**:

- 觸發指令: `2330`, `台積電分析`, `2317深度`
- 驗證項目: 評分合理性、圖表渲染、數據時效
- 成功標準: 5秒內回應、UI無錯誤

---

### 📁 Project 4: Guardian (持股衛士) 🛡️

**目標**: 買進後的監控與出場建議

| 功能項目 | 描述                  | 狀態 | 負責Agent |
| -------- | --------------------- | ---- | --------- |
| 庫存匯入 | 用戶輸入持股清單      | ⏳   | Sophia    |
| 每日追蹤 | 自動檢查持股狀態      | ⏳   | Oscar     |
| 停損提醒 | 跌破支撐/法人賣超警示 | ⏳   | Oscar     |
| 獲利了結 | 乖離過大建議減碼      | ⏳   | Oscar     |

**開發計劃**:

1. 設計庫存資料結構 (MongoDB)
2. 實作每日監控排程
3. 建立通知推播機制

**測試規劃**:

- 觸發指令: `加入庫存 2330 100張`, `我的持股`
- 驗證項目: 資料持久化、警示觸發邏輯
- 成功標準: 警示準確率>90%

---

### 📁 Project 5: Insight (市場雷達) 📡

**目標**: 即時掌握市場脈動與異常訊號

| 功能項目     | 描述           | 狀態 | 負責Agent |
| ------------ | -------------- | ---- | --------- |
| 即時新聞搜尋 | Tavily網路搜尋 | ✅   | Isabella  |
| 法說會追蹤   | 重大訊息解讀   | ✅   | Isabella  |
| 異常量偵測   | 爆量股票警示   | ⏳   | Arthur    |
| 主力動向     | 分點籌碼追蹤   | ⏳   | Arthur    |

**開發計劃**:

- [ ] 盤中異常量即時偵測
- [ ] 分點進出資料整合
- [ ] 訂閱制推播通知

**測試規劃**:

- 觸發指令: `旺宏法說會`, `今天有什麼消息`
- 驗證項目: 搜尋結果相關性、回應速度
- 成功標準: 15秒內回應、內容相關度>80%

---

## 📅 開發優先順序

| 優先級 | 專案               | 預估工時 | 備註         |
| ------ | ------------------ | -------- | ------------ |
| 🔴 P0  | Deep Dive 同業比較 | 2天      | 用戶高頻需求 |
| 🔴 P0  | Eagle Eye 技術指標 | 3天      | 差異化功能   |
| 🟡 P1  | Guardian 基礎建設  | 5天      | 創造黏著度   |
| 🟡 P1  | Insight 異常量偵測 | 2天      | 盤中價值     |
| 🟢 P2  | Frontend PWA化     | 5天      | 行動體驗     |

---

## ✅ 測試檢查清單

每次功能更新後執行:

1. [ ] 單元測試通過
2. [ ] API回應時間<5秒
3. [ ] UI渲染無錯誤
4. [ ] 數據時效性驗證
5. [ ] 錯誤處理覆蓋

---

## 📂 程式碼檔案位置對照表

### 🤖 Agents (代理人層)

| Agent                 | 檔案路徑                                    |
| --------------------- | ------------------------------------------- |
| Sophia (Orchestrator) | `backend/app/agents/sophia_orchestrator.py` |
| Isabella (Research)   | `backend/app/agents/finrobot_agents.py`     |

### ⚙️ Services (服務層)

| 服務名稱        | 檔案路徑                                   | 功能說明                         |
| --------------- | ------------------------------------------ | -------------------------------- |
| StockService    | `backend/app/services/stock_service.py`    | 核心股票分析、評分、YFinance整合 |
| MetabaseService | `backend/app/services/metabase_service.py` | ClickHouse資料查詢、概念股搜尋   |
| RuleEngine      | `backend/app/services/rule_engine.py`      | 自然語言篩選條件解析與執行       |
| MCPService      | `backend/app/services/mcp_service.py`      | Tavily搜尋、Crawl4AI爬蟲工具     |
| ReportFormatter | `backend/app/services/report_formatter.py` | 晨報格式化輸出                   |
| SectorAnalyzer  | `backend/app/services/sector_analyzer.py`  | 強勢族群分析                     |

### 🌐 API (路由層)

| 檔案路徑                    | 功能說明                         |
| --------------------------- | -------------------------------- |
| `backend/app/api/routes.py` | Flask 主路由、意圖識別、請求分發 |

### 🎨 Frontend (前端層)

| 檔案路徑                           | 功能說明        |
| ---------------------------------- | --------------- |
| `backend/app/templates/index.html` | 主頁面模板      |
| `backend/app/static/js/`           | JavaScript 邏輯 |
| `backend/app/static/css/`          | 樣式表          |

### 🔧 Core (核心模組)

| 檔案路徑                         | 功能說明       |
| -------------------------------- | -------------- |
| `backend/app/core/config.py`     | 環境變數與設定 |
| `backend/app/core/constants.py`  | 常數定義       |
| `backend/app/core/logger.py`     | 日誌系統       |
| `backend/app/core/exceptions.py` | 自訂例外       |
| `backend/app/core/utils.py`      | 工具函數       |

### 📁 專案結構總覽

```
mongo_project/
├── backend/
│   ├── app/
│   │   ├── agents/          # 代理人邏輯
│   │   ├── api/             # Flask 路由
│   │   ├── core/            # 核心配置
│   │   ├── services/        # 業務邏輯
│   │   ├── static/          # 靜態資源
│   │   └── templates/       # HTML 模板
│   └── run.py               # 啟動入口
├── .agent/
│   ├── skills/              # 技能定義
│   └── workflows/           # 工作流程
├── .env                     # 環境變數
├── agent.md                 # 本文件
└── requirements.txt         # 依賴套件
```
