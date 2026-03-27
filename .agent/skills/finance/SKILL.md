---
name: finance
description: 使用 OpenBB, yfinance 與 TA-Lib 進行法人級別的金融量化分析。
---

# 金融分析技能 (Finance Skill)

## 🎯 核心使命

本技能賦予 Arthur 強大的數據權威，使分析不再依賴 LLM 的過時記憶，而是實時的量化數據。

## 🛠️ 神級工具整合

- **OpenBB-finance/OpenBBTerminal**: 「開源版彭博終端機」。
  - 用於獲取全球基本面、加密貨幣與總體經濟數據。
- **ranaroussi/yfinance**: 輕量級台美股數據源。
  - 用於獲取即時報價、EPS 、股利政策等 MVP 核心數據。
- **TA-Lib/ta-lib-python**: 極速量化運算庫。
  - 用於計算 RSI, MACD, 布林通道等技術指標，為個股進行科學評分。

## 📋 專家級 SOP

1. **數據獲取**: 分析前必須先調用 SDK 獲取最新財報與價格。
2. **量化校驗**: 使用 TA-Lib 計算多維技術因子，驗證上漲動力。
3. **數據來源標註**: 報告中必須明確區分基礎數據 (yfinance) 與 深度研究 (OpenBB)。

## ⚠️ 關鍵守則

- **誠信底線**: 嚴禁在數據獲取失敗時憑空想像股價或 PE 值。
- **計算精準**: 利用 TA-Lib 的高效運算取代手動公式，防止計算錯誤。
