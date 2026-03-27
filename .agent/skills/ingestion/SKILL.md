---
name: ingestion
description: 使用 crawl4ai 抓取情報並通過 Fintwit-Sentiment 進行金融情緒分析。
---

# 情報攝取技能 (Ingestion Skill)

## 🎯 核心使命

本技能賦予 Oscar 從非結構化網頁中（新聞、論壇）精準提取金融情緒與情報的能力。

## 🛠️ 神級工具整合

- **unclecode/crawl4ai**: AI 專用爬蟲。
  - 將複雜網頁轉為乾淨 Markdown，方便 LLM 讀取，避免雜訊干擾。
- **marrrcin/Fintwit-Sentiment-Analysis**: 金融情感模型。
  - 專門針對金融推文與新聞訓練。能識別 "Bullish"、"Covering shorts" 等一般模型難以處理的術語。

## 📋 專家級 SOP

1. **內容清洗**: 利用 crawl4ai 過濾掉所有的 HTML 廣告標籤，僅提取分析正文。
2. **語境分析**: 情緒分析必須優先考慮金融術語權重，避免誤判。
3. **噪音標記**: 所有的情報必須具備「實效性標籤」，過往的新聞需自動降權。

## ⚠️ 關鍵守則

- **來源追溯**: 必須保留原始網頁標題與連結。
- **防止偏誤**: 當論壇出現極端情緒時，必須交叉驗證 Arthur 的量化數據。
