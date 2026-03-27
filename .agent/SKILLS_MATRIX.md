# 戰隊精英技能矩陣 (The All-Star Skill Matrix)

本文件定義戰隊成員在 Sprint 3 中所掌握的核心技能（Skills），這些技能將通過指定的技術棧實現。

## 👑 Sophia (Project Manager / Agent Manager)

- **Skill: Multi-Agent Orchestration**
  - **Tool**: `crewAI`
  - **Description**: 負責定義代理人角色、指派任務，並監督 Arthur 與 Oscar 的協作產出。
- **Skill: Final QC & Formatting**
  - **Tool**: `ReportFormatter` v3.0
  - **Description**: 確保最終交付報告兼具數據深度與美感。

## 📈 Arthur (Senior Quantitative Analyst)

- **Skill: Institutional Data Mining**
  - **Tool**: `OpenBB SDK`, `yfinance`
  - **Description**: 獲取法人級別的基本面與總經數據。
- **Skill: Technical Quantitative Evaluation**
  - **Tool**: `TA-Lib`
  - **Description**: 計算 RSI, MACD 等量化指標，為個股進行科學打分。

## 🛡️ Oscar (Data Integrity & Sentiment Officer)

- **Skill: Web Intelligence Ingestion**
  - **Tool**: `crawl4ai`
  - **Description**: 高效抓取財經論壇內容並轉換為 LLM 友善格式。
- **Skill: Financial Sentiment Decoding**
  - **Tool**: `Fintwit-Sentiment-Analysis`
  - **Description**: 精準解析帶有金融術語的網路情緒（Bullish/Bearish）。

## 🛠️ Leo (Full-Stack Interaction Engineer)

- **Skill: Streaming Insight UI**
  - **Tool**: `Vercel AI SDK`
  - **Description**: 實作打字機效果與推理鏈的流式展示。
- **Skill: Dynamic Data Visualization**
  - **Tool**: `Recharts`
  - **Description**: 將 Arthur 的量化數據轉化為動態圖表。

## 🧪 Kevin (Quality Assurance)

- **Skill: Hallucination Guardrail**
  - **Tool**: `Arize Phoenix`
  - **Description**: 監控 Agent 推理過程，攔截任何數據幻覺。
- **Skill: Strategy Backtesting**
  - **Tool**: `Backtrader`
  - **Description**: 對分析師建議進行歷史勝率驗證。

## 🧠 Diana (AI Strategy Architect)

- **Skill: Complex State Management**
  - **Tool**: `LangGraph`
  - **Description**: 設計複雜的任務循環流程（例如：審核失敗後重做的狀態轉移）。
