# SEO 負責 evidence 的逐字回溯修復

KMindHub 維持通用的 semantic extraction，只產生 mention、排名、情緒與 semantic facts；`evidenceText` 必須逐字存在於 runner raw response，則是 GEO 報表的 provenance 規則，由 `younilab-seo` 驗證與修復。若只有 `evidenceText` 無法逐字回溯，SEO 才發出第二次 Gemini LLM 呼叫；這次呼叫不是重新 extraction 或改寫 evidence，而是以 structured output 選擇 raw response 的 `sourceBlockId`。`sourceBlockId` 只在單次 request 內定位原始非空行，完成映射後即失效，不保存、不回傳前端，也不是 domain model。SEO 再由程式映射回未修改的原文，不因 evidence validation 失敗而重跑整包 extraction。KMindHub HTTP client 對 429 / 5xx 的 transport retry 不在此限制內。

KMindHub `verification.passed = false`、entity、sentiment、schema 或其他欄位錯誤不得由 focused repair 覆蓋。Repair 結果只有在每筆失敗項目順序一致、全部 block 都存在，且正規化後的 evidence 仍是 raw response substring 時才會原子套用；否則 analysis 維持失敗，不 commit KMindHub preview。
