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

## Rollout Slice

1. 新增 contracts 與 `GeoRunResultAnalyzer` port。
2. 新增 fake analyzer for use case tests。
3. 新增 analysis facts persistence。
4. 實作 `AnalyzeRunResult` use case。
5. 新增 KMindHub HTTP adapter。
6. 用已保存 Gemini 或 Google AIO result 做 optional live smoke。

## Open Decisions

- KMindHub endpoint 名稱與正式 API shape。
- KMindHub 是否直接支援 nested mention/sentiment/semantic structured output，或先回多個 item facts。

## Acceptance

- completed run result 可產生 mention / sentiment / semantic facts。
- failed run result 不呼叫 analyzer。
- analyzer failure 會保存 failed analysis status 與 error。
- mention facts 可回溯 `run_result_id` 與 evidence text。
- sentiment MVP 只接受 `positive` / `negative`，不接受 `neutral`。
- semantic facts 只接受 `product`、`service`、`topic`、`common_statement`。
