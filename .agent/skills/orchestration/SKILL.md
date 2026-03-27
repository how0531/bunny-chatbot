---
name: orchestration
description: 利用 CrewAI 與 LangGraph 實現多代理人協作與精準狀態循環。
---

# 協作調度技能 (Orchestration Skill)

## 🎯 核心使命

本技能旨在實現「全明星組隊模式」，讓 AI 角色能互相對話、傳遞並審核任務。

## 🛠️ 神級工具整合

- **joaomdmoura/crewAI**: 核心實作框架。
  - **Agent**: 定義角色（Sophia=Manager, Arthur=Analyst）。
  - **Task**: 定義任務目標與預期輸出。
  - **Process**: 定義順序或層級式協作流程。
- **langchain-ai/langgraph**: 狀態管理與循環邏輯。
  - 適用於「Oscar 審核不通過 -> 退回給 Arthur -> Arthur 重寫」的複雜路徑。

## 📋 專家級 SOP

1. **角色初始化**: 必須明確定義代理人的 `backstory` 與 `goal`。
2. **任務鏈接**: 任務輸出必須具備強型別約束，方便下一個代理人解析。
3. **品質門禁 (Quality Gate)**: 設置帶有 `conditional_edges` 的狀態圖，當誠信分數低於門檻時強制回流至修正節點。

## ⚠️ 關鍵守則

- **嚴禁線性單向**: 必須具備審核與退回機制，模仿人類專家的協作。
- **上下文隔離**: 確保代理人僅獲取與其任務相關的數據，降低幻覺率。
