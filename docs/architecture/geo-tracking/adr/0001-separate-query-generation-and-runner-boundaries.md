# 分離 Query Generation 與 Runner 的責任邊界

`geo-tracking` 的核心流程只有兩段：Query Generation 根據品牌、競品、keyword、地區、語言、topic、intent、audience 與品牌提及規則產生候選 query；Runner 接收已生成或已保存的 query，呼叫 AI / SERP 平台取得跑題結果。PDF 與討論中的 Query Research 在本輪應理解為 query 生成工具的產品語意，也就是依目標市場語氣與生成約束產生問句，而不是必須在前端曝光的獨立搜尋步驟。

我們決定 Query Generation 只能根據輸入 JSON 與可選背景脈絡產生 structured query draft，不使用 Google Search、web search 或 SERP adapter；它也不得自行改寫 intent、推論 SERP intent，或把 `sourceUrls`、`searchedKeywords`、SERP、evidence 類資料寫入 query attributes。Structured output 的每筆 draft 必須保留輸入導向的 `attributes`，再輸出 `query`，最後輸出 `keywords`；`keywords` 只能來自輸入 seed keywords。

Runner 才是 provider execution 邊界，可以呼叫 Gemini grounding、Google AIO via SerpApi，以及後續 ChatGPT、Claude、Perplexity 等 provider。Runner result 必須標示 `provider`、`surface`、`model`、`rawResponse` 與 references，讓後續分析或 UI 能知道結果來自哪個 AI / SERP surface。

Google AIO 是 Runner-only provider，provider code 為 `google_aio`，目前透過 SerpApi 取得 Google AI Overview；它不能被 Query Generation 使用。Google AIO 執行時先呼叫 `engine=google`，必要時用同次回應提供的短效 `page_token` 立刻呼叫 `engine=google_ai_overview`，若沒有 AI Overview 則回 `no_google_aio_result`，不 fallback 成 organic results；地區語系由 request 的 `region` / `language` 轉成 SerpApi `hl`、`gl`、`location` profile，目前支援台灣與美國，並保留日本等後續市場擴充。

因此 `geo-tracking` 的 application contract 必須在 provider 能力上防呆：Query Generation 只能接受支援 query 生成的 provider；Runner 才能接受 `gemini`、`google_aio` 等跑題 provider。正式資料庫、排程、queue job 狀態、project/topic/query CRUD 與分析指標持久化不屬於這個 ADR 的決策內容；本 ADR 只定義 `geo-tracking` 內部 Query Generation 與 Runner adapter 的責任邊界。
