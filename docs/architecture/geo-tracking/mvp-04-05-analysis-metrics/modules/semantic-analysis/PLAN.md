# Semantic Analysis Plan

## Responsibility

Semantic Analysis 負責把單筆 `geo_run_result.raw_response` 轉成需要語意理解的 structured facts：

- 自有品牌與專案競品是否被提及。
- 自有品牌與競品在整個 raw response 中第一次出現的順序。
- 正面 / 負面輿情 statement。
- 產品、服務、主題與常見陳述 semantic labels。

此 module 不處理 runner references，不計算 KPI，不保存 dashboard snapshot。

## Architecture

`geo-analysis` 定義 `GeoRunResultAnalyzer` interface，KMindHub HTTP adapter 是第一個實作。測試可使用 fake analyzer。

```text
AnalyzeRunResult
  -> load run result + query/topic/project/entities
  -> build AnalyzeGeoRunResultCommand
  -> GeoRunResultAnalyzer.analyze(command)
  -> save analysis status + mention/sentiment/semantic facts
```

`evidenceText` 的逐字 provenance 是 GEO 報表規則，不是 KMindHub 的通用 extraction 規則。KMindHub preview 通過自己的 verification 後，GEO 先以 deterministic substring 驗證 evidence；只有無法逐字回溯的 evidence 才透過 `EvidenceTextRepairer` 發出第二次 Gemini LLM 呼叫。這次呼叫只選擇原文來源，不重跑 extraction、不改寫 evidence，也不重新生成其他已正確 facts。

## KMindHub Scope

KMindHub capability 的責任：

- 接收 raw response、品牌與競品清單。
- 接收 query/topic/project context，包含 topic description。
- 用 structured output 解析 mention、position、sentiment 與 semantic labels。
- 回傳 facts，不產生 citations 或 dashboard metrics。

KMindHub 不應：

- 計算 Visibility / SOV / Used % / Share %。
- 接收 runner references 來計算 URL / domain 指標。
- 進行 URL/domain normalization、owned domain classification、By URL / By Domain aggregation。
- 保存 GEO project / query / provider lifecycle。
- 決定前期比較區間。
- 知道 dashboard 篩選維度。
- 實作 GEO 專用的 exact-substring repair 或 block-ID 規則。

## Evidence Source Selection Scope

SEO repair adapter 的責任：

- 把 raw response 切成帶 request-scoped ID 的非空原始行；ID 只在單次呼叫內有效，不保存也不曝光。
- 只把 raw response、失敗的 `itemIndex` / `wrongEvidenceText` 與 source blocks 交給 Gemini。
- Structured output 只接收 `itemIndex` / `sourceBlockId`，再由程式取回 untouched source text。
- 不使用 Google Search 或任何外部搜尋工具。
- 共用單一 `google-genai[aiohttp]` client / session，並由 API 或 worker lifecycle 關閉。

Repair 不應處理 KMindHub verification、entity ID、sentiment、fact type 或 schema 錯誤，也不接受 semantic similarity 作為 provenance。

## Rollout Slice

1. 新增 contracts 與 `GeoRunResultAnalyzer` port。
2. 新增 fake analyzer for use case tests。
3. 新增 analysis facts persistence。
4. 實作 `AnalyzeRunResult` use case。
5. 新增 KMindHub HTTP adapter。
6. 以 focused repair adapter 處理非逐字 evidence，並用已保存的真實 result 做 live regression。

## Acceptance

- completed run result 可產生 mention / sentiment / semantic facts。
- failed run result 不呼叫 analyzer。
- analyzer failure 會保存 failed analysis status 與 error。
- mention facts 可回溯 `run_result_id` 與 evidence text。
- sentiment MVP 只接受 `positive` / `negative`，不接受 `neutral`。
- semantic facts 只接受 `product`、`service`、`topic`、`common_statement`。
- KMindHub 每次 analysis 只做一次 logical preview，不因 evidence 失敗重跑整包 extraction；429 / 5xx transport retry 仍可依 HTTP client policy 執行。
- Gemini 只回 request-scoped block ID，最終 evidence 必須是 raw response 的 exact normalized substring。
- Repair 缺筆、重排、重複 index、未知 block 或非逐字文字時整批拒絕，且不部分修改 preview。
