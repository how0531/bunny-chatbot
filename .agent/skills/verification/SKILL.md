---
name: verification
description: 使用 Arize Phoenix 監控幻覺並透過 Backtrader 驗證回測勝率。
---

# 品質保證技能 (Verification Skill)

## 🎯 核心使命

本技能是團隊的「防禦大腦」，負責檢驗 Arthur 是否在胡說八道，並驗證策略的歷史可行性。

## 🛠️ 神級工具整合

- **mementum/backtrader**: 工業級回測框架。
  - 用於驗證 Arthur 建議的投資組合在過往三年的真實績效。
- **Arize-ai/phoenix**: 幻覺與 Trace 監控。
  - 直接監控 Agent 的決策過程，找出幻覺產生的時間點，並建立品質監控儀表板。

## 📋 專家級 SOP

1. **策略預審**: 所有的選股策略在推出前，必須經過 Backtrader 的冷啟動測試。
2. **決策追蹤**: 利用 Phoenix 的 Trace 能力單步調試 Agent 的邏輯推演過程。
3. **幻覺攔截**: 一旦偵測到輸出數據與底層 DB 不符，立即觸發「重寫」循環。

## ⚠️ 關鍵守則

- **勝率為王**: 績效回測不達標的策略，僅能標註為「實驗性」。
- **透明至上**: 幻覺檢測日誌對 PM (Sophia) 與 用戶 完全公開。
