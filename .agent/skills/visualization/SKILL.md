---
name: visualization
description: 使用 Vercel AI SDK 實作流式推理鏈並透過 Recharts 展示動態數據。
---

# 展示交互技能 (Visualization Skill)

## 🎯 核心使命

本技能負責將後端代理人的複雜協作與海量數據，轉化為具備「生命感」的用戶介面。

## 🛠️ 神級工具整合

- **vercel/ai-sdk**: React 前端串流核心。
  - 實作打字機效果與推理鏈 (Reasoning Chain) 的步驟化流式展示。
- **recharts/recharts**: 基於 D3 的視覺化庫。
  - 用於將 Arthur 獲取的技術面指標（RSI, MACD）與 籌碼數據自動繪製為動態圖表。

## 📋 專家級 SOP

1. **異步串流**: 利用 AI SDK 的 `useChat` 讓用戶即時看見協作進度。
2. **圖表驅動**: 每項量化指標必須具備對應的 Recharts 組件，拒絕純文字呈現。
3. **Glassmorphism 適配**: 所有的視覺繪製必須對齊團隊的「尊榮黑金」與「毛玻璃」設計語義。

## ⚠️ 關鍵守則

- **拒絕假數據**: 展示的圖表線條必須 100% 映射自底層數據源。
- **響應優先**: 視覺組件必須自動適配行動端與桌面端。
