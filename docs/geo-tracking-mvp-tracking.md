# GEO MVP 模組 A/B/C 追蹤清單

本文件整理截至目前實作與討論結果，只涵蓋 Phase 1 MVP 需要的模組 A/B/C。Phase 2、Phase 3 項目不列入本輪開發範圍。

## 已完成項目

- 新增 `geo-tracking` bounded context 雛形，分成 domain、application、infrastructure、FastAPI API app。
- 新增 Query Generation use case、contract、provider interface 與 dummy provider。
- 新增 Query Research use case、contract、provider interface 與 dummy provider。
- 新增跑題 Run Engine use case，可依 request provider 選擇 dummy、Gemini 或 Google AIO answer provider。
- 新增 Gemini Query Generation adapter，使用 structured output，不掛 Google Search tool。
- 新增 Gemini Query Research backend adapter，使用 structured output 並掛 Google Search tool；前端目前不再曝光獨立「取得搜尋脈絡」步驟。
- 新增 Gemini Run Answer adapter，使用 Google Search grounding，回傳 `referenceUrls`。
- 新增 Google AIO Run Answer adapter，透過 SerpApi 取得 Google AI Overview，回傳 `rawResponse`、`referenceUrls` 與 `references[{ title, url }]`。
- Run Answer result 已保留 `provider`、`surface`、`model`，可標示結果來自哪個 AI / 平台；另新增 `references[{ title, url }]` 結構化來源，前端優先顯示 title，並保留舊 `referenceUrls` 相容欄位。
- Gemini Run Answer 若第一輪沒有 grounding references，會自動 retry 一次，使用較強的 reference prompt。
- 預設 Gemini model 調整為 `gemini-3.1-flash-lite`。
- Query Generation attributes 已收斂為生成引導欄位：`intent`、`keyword`、`topicName`、`topicDescription`、`audience`、`brandMentionRules`。
- Query Generation structured output 已調整為每筆 draft 先輸出 `attributes`、接著 `query`、最後 `keywords`；`keywords` 代表該 prompt 實際使用到的輸入 seed keywords。
- Query Generation attributes 已移除 `sourceUrls`、`searchedKeywords`、SERP intent、evidence 類欄位。
- Query Research output 保留 `researchContext`、`searchedKeywords`、`sourceUrls`。
- API 新增 `/api/v1/geo-tracking/query-generation`、`/query-research`、`/run-requests`、`/dummy-project`。
- Admin Portal 新增 GEO 跑題頁，可輸入品牌、競品、keywords、地區、語言、市場語境、topic 名稱與描述、intent、audience、brand mention rules。
- Admin Portal 已新增 `/geo-tracking` GEO 測試頁面，作為 Phase 1 MVP 串接 Query Research、Query Generation、Run Engine 的本機操作入口。
- Admin Portal 右側流程已對齊 PDF 架構：`Query Research 工具` 負責用輸入與背景設定生成 query draft；`Query / Topic 管理紀錄` 只呈現已生成/暫存紀錄；`Runner 跑題引擎` 才負責把 query 送到 AI provider 取得結果。
- Admin Portal Query / Topic 管理預覽表格已對齊客戶澄清欄位：`Prompt`、`Keywords`、`Intent`、`動作`。
- Admin Portal 的 Intent 欄位使用 `N / I / C / T` 圓圈標記，對應客戶提供分類名稱：導航、資訊、商業、交易。
- Admin Portal 的 `+ Shortlist` 目前是前端 local state，作為本輪 Runner 選取來源；尚未做後端 CRUD / 持久化。
- Admin Portal 支援 Query Generation provider 選擇 dummy / Gemini，Run provider 選擇 dummy / Gemini / Google AIO (SerpApi)；Query Research backend provider 保留在 API，但前端目前不提供獨立 provider 選擇或搜尋脈絡按鈕。
- Admin Portal 已移除右側「取得搜尋脈絡」功能，避免誤解為 Query Generation 需要先跑 Google Search。
- 移除 UI 原始碼中的 `Kinsan SEO` 顯示字樣，改為 `Younilab SEO`。
- 台灣 / `zh-TW` dummy query 會產生繁體中文語境，不再固定英文。
- 後端 contract 已限制 Google AIO 只支援 Run Request；Query Generation / Query Research 若直接帶 `google_aio` 會回 422，避免繞過前端造成 provider registry error。

## 已確認決策

- Query Generation 不使用 web search、Google Search tool、SERP adapter。
- Query Research 才能使用 Google Search grounding，用來取得市場語氣、搜尋語句、reference URL。
- Run Engine / Answer adapter 可使用 Google Search grounding，因為它是在跑題回答階段。
- Intent 是使用者選擇的生成角度，不是 LLM 自行分類結果。
- SERP intent 判斷是未來獨立 adapter/API，不參與 Query Generation attributes，也不影響其他 LLM adapter 邏輯。
- Intent 分類以客戶提供名稱為主：導航、資訊、商業、交易。
- B2B 採購差異不新增獨立分類，先放在 prompt description、audience、marketType 裡引導。
- `shouldMentionOwnBrand`、`shouldMentionCompetitor` 是「是否要求 query 提及」的生成前限制，不是生成後分類。
- `audience` 是正式輸入參數，前端與 prompt payload 都需要帶入。
- `isBranded` 目前先以自身品牌提及規則推導，後續若要更準確，應改由 query text / brand alias 判斷。
- Shortlist 依客戶最新澄清，先視為每條 prompt 右側的「加入收藏 / 候選清單」操作；不是 intent。本輪只做前端 local state，不做後端 CRUD。
- Generated prompt 的 `keywords` 是該 prompt 實際使用到的輸入 seed keywords，透過 Query Generation structured output 在 `query` 後方回傳；後端需限制在原始輸入 keyword 清單內。
- Source URLs 只出現在 Query Research / Run Answer 結果；若 Gemini grounding metadata 沒有 URL，允許空陣列，但流程不能失敗。
- 模組 A 的 Google Ads API / Keyword Planner 搜尋量資料本輪略過。
- 模組 B 的手動輸入、多題輸入、metadata、排程、CRUD、DB 持久化先交接後端設計。
- 模組 C 已完成 Gemini 真 adapter 與 Google AIO (SerpApi) runner adapter；其他 provider 保留 dummy 或後續 adapter。
- 解析提及 / 排名 / 引用 / 輿情，以及優化行動建議，本輪暫不規劃。

## Live Gemini 驗證

- 使用本機 Vertex credentials JSON 進行 live test；憑證內容與檔案不進 source。
- Admin Portal 測試頁面路由：`http://127.0.0.1:5174/geo-tracking`。
- 測試頁面用途：暫時替代完整 CRUD 後台，用同一頁完成 dummy project 載入、Query Research 工具生成 query、Query / Topic 暫存紀錄預覽、選取 query、Runner 執行與 raw result 檢視。
- `gemini-3.1-flash-lite` 可執行 Query Generation structured output。
- Query Generation live result：成功回傳 2 筆 query；attributes 保留使用者選定 intent；沒有 source URL attributes。
- `gemini-3.1-flash-lite` 可執行 Query Research structured output + Google Search grounding。
- Query Research live result：成功回傳 research context、8 筆 searched keywords、6 筆 source URLs。
- Runner live references 測試限制：若超過 2 輪測試仍無法達到 95% references 成功率就停止。
- Runner live references 第 1 輪：27/31 筆有 grounding references，成功率 87.1%，未達 95%。主要問題是部分 Gemini response 沒有 grounding chunks；另有一個本機 script 輸出遇到 cp950 encoding 問題。
- Runner live references 第 2 輪：加入無 references 時 retry 一次的 prompt 後，30/30 筆有 grounding references，成功率 100%，達標。
- 技術修正：Vertex 不接受 application DTO 產出的完整 Pydantic schema 約束，因此 infrastructure adapter 使用 Gemini 專用簡化 schema，再轉回 application contract。

## Live Google AIO / SerpApi 驗證

- Google AIO runner provider code：`google_aio`，前端顯示 `Google AIO (SerpApi)`。
- 使用 `SERPAPI_API_KEY` 環境變數提供 SerpApi key；key 不進 source、不寫入文件。
- Google AIO adapter 使用 `aiohttp.ClientSession`，provider instance 內重用同一個 session；FastAPI lifespan shutdown 會關閉 provider session。
- Gemini SDK dependency 已改為 `google-genai[aiohttp]>=1.0`，並保留 `aiohttp>=3.12,<4` 作為 SerpApi adapter runtime dependency。
- Locale profile 目前支援台灣與美國，結構保留後續日本 / 日文擴充：
  - `TW`: `hl=zh-tw`、`gl=tw`、`location=Taiwan`
  - `US`: `hl=en`、`gl=us`、`location=United States`
- SerpApi locations live check：`Taiwan`、`Taipei`、`Taipei City`、`New Taipei City` 可查到 `country_code=TW`；中文地名 `台灣`、`台北` 查 locations API 回空陣列，因此 location profile 先使用英文 canonical location。
- Google AIO adapter 流程：
  1. 先打 `engine=google`，帶入 `q`、`hl`、`gl`、`location`。
  2. 若 `ai_overview.text_blocks` 已存在，直接組成 `rawResponse`。
  3. 若只有 `ai_overview.page_token`，立刻打 `engine=google_ai_overview` 取得完整 AIO；`page_token` 是短效 token，不做長期保存。
  4. 若沒有 AIO，回傳 provider error code `no_google_aio_result`，不 fallback 成 organic results。
- Live query：`黃連膏 推薦`，`TW / zh-TW`。
- Live result：`google_aio` 成功回傳 `rawResponse` 463 字、6 筆 references，references 含 title 與完整 URL。
- Live API route result：使用最新版 `younilab_geo_tracking_api.main:app` 啟動本機臨時 server 後，`/api/v1/geo-tracking/run-requests` 回 `status=completed`、`provider=google_aio`、`surface=Google AI Overview`、`model=serpapi-google-ai-overview`、`rawResponse` 463 字、6 筆 references。OpenAPI `ProviderCode` enum 已包含 `dummy, gemini, google_aio`。
- 本機注意：若 `http://127.0.0.1:8002/openapi.json` 的 `ProviderCode` 仍只有 `dummy, gemini`，表示 8002 是舊 process，需重啟 geo-tracking API 才能讓前端 Runner 選 Google AIO 後正常送出。

## 模組 A：Query Research 工具

### 目前完成

- 關鍵字輸入最多 10 個的 API contract 與前端基本驗證。
- 地區支援台灣 / 美國。
- 語言 UI 支援 `zh-TW` / `en-US`，地區切換會帶入預設語言。
- 市場語境支援 `b2c` / `b2b_procurement`。
- 使用者可設定多個 topic name / description，topic description 會作為 Query Generation 的生成約束。
- 使用者可設定 intent category / description 作為 query 生成角度。
- 使用者可設定 audience name / description。
- 使用者可設定 branded / competitor mention rules。
- Query Research 工具在前端語意上負責生成 query draft，不再要求先透過 Gemini grounding 取得搜尋脈絡。
- Query Research backend adapter 仍支援 structured output + Google Search grounding，可作為未來市場語氣或來源脈絡的後端能力，但目前不是前端流程的必要步驟。
- Query Generation 可透過 Gemini structured output 產生多筆 query。

### 尚未完成，交接後端

- Query Research request / result 的 CRUD 與持久化設計。
- Keyword list CRUD：新增、編輯、刪除、排序、最多 10 個限制、重複字檢查。
- Intent template CRUD：使用者可維護 intent 分類、描述、適用市場、排序、啟停。
- Audience template CRUD：使用者可維護 audience 名稱、描述、適用市場、排序、啟停。
- Topic template / topic library CRUD：使用者可維護 topic 名稱、描述、排序、啟停，並在生成 query 時選用。
- Brand / competitor alias CRUD：自身品牌、競品品牌、品牌別名、英文名、縮寫。
- Region / language 設定 CRUD：台灣、美國先做，schema 保留其他地區與語言擴充。
- Research context history：保存每次 Query Research 的輸入、provider、model、searched keywords、source URLs、raw metadata、建立時間。
- Generated query draft CRUD：保存生成出的 query draft、attributes、使用者採納狀態、淘汰原因。
- Shortlist 資料模型：需保存使用者加入 Shortlist 的 prompt/query、keywords、intent、topic、建立者、建立時間、狀態；目前前端 local state 不會持久化。

### 尚未完成，表單設計

- Keyword 輸入表單：多行輸入、上限提示、去重、批次貼上。
- 地區 / 語言表單：地區選擇、語言預設、允許手動覆寫。
- Topic 約束表單：topic name、topic description、多筆新增 / 刪除。
- Intent 管理表單：分類、描述、B2B prompt description、啟用狀態。
- Audience 管理表單：名稱、描述、預設市場類型。
- Brand mention rules 表單：自身品牌、競品、泛用 query 生成策略。
- Research result 表單：顯示 research context、searched keywords、source URLs，並允許將 context 帶入 query generation。
- Generated prompts 表格：主欄位對齊 `Prompt`、`Keywords`、`Intent`、`動作`；topic、audience、brand rules、market metadata 可放在 detail、tooltip 或次要資訊。
- Shortlist 動作表單：每筆 prompt 右側提供 `+ Shortlist`，本輪為 local state；後續需補持久化、取消收藏、批次操作與權限規則。

### 本輪略過

- Google Ads API / Keyword Planner 搜尋量。
- Show More Prompts 與相關關鍵字自動擴展尚未設計，需要先釐清輸出與保存方式。

## 後端 Table Schema / CRUD 建議

以下是讓模組 A/B/C 從目前 demo flow 變成可持久化 MVP 需要補齊的建議資料表。欄位命名可依後端既有 migration 風格調整，但概念邊界建議保留。

### Project / Brand 設定

`geo_projects`

- `id`
- `seo_task_id`
- `brand_name`
- `market_type`
- `default_region`
- `default_language`
- `status`
- `created_at`
- `updated_at`

`geo_brand_aliases`

- `id`
- `project_id`
- `brand_type`: `own_brand | competitor`
- `brand_name`
- `alias`
- `region`
- `language`
- `is_primary`
- `created_at`

CRUD / actions：

- Project 設定讀取 / 更新。
- 自身品牌 alias CRUD。
- 競品品牌 CRUD。

### 模組 A：Query Research 輸入與模板

`geo_keywords`

- `id`
- `project_id`
- `keyword`
- `region`
- `language`
- `status`
- `sort_order`
- `created_at`
- `updated_at`

`geo_intent_templates`

- `id`
- `project_id`
- `category`: `informational | commercial_investigation | transactional | navigational`
- `description`
- `market_type`
- `region`
- `language`
- `is_default`
- `status`
- `sort_order`
- `created_at`
- `updated_at`

`geo_audience_templates`

- `id`
- `project_id`
- `name`
- `description`
- `market_type`
- `region`
- `language`
- `status`
- `sort_order`
- `created_at`
- `updated_at`

CRUD / actions：

- Keyword CRUD，含最多 10 個限制與重複 keyword 檢查。
- Intent template CRUD，只保存分類與描述，不設計 intent name。
- Audience template CRUD。
- Region / language 預設設定更新。

### 模組 A：Query Research 執行紀錄

`geo_query_research_runs`

- `id`
- `project_id`
- `provider`
- `model`
- `brand_name_snapshot`
- `competitor_brands_snapshot` JSON
- `keywords_snapshot` JSON
- `region`
- `language`
- `market_type`
- `audience_snapshot` JSON
- `research_context`
- `searched_keywords` JSON
- `source_urls` JSON
- `raw_metadata` JSON
- `status`: `completed | failed`
- `error_code`
- `created_at`

CRUD / actions：

- Create research run。
- List research runs。
- Get research run detail。
- Delete / archive research run。

### 模組 B：Topic / Query 管理

`geo_topics`

- `id`
- `project_id`
- `name`
- `description`
- `sort_order`
- `status`
- `created_at`
- `updated_at`

`geo_queries`

- `id`
- `project_id`
- `topic_id`
- `text`
- `region`
- `language`
- `market_type`
- `intent_category`
- `intent_description`
- `audience_name`
- `audience_description`
- `should_mention_own_brand`
- `should_mention_competitor`
- `is_branded`
- `source`: `manual | generated | imported`
- `source_research_run_id`
- `status`: `active | paused | archived`
- `created_at`
- `updated_at`

`geo_query_metadata`

- `id`
- `query_id`
- `key`
- `value`
- `source`: `system | user`
- `created_at`
- `updated_at`

CRUD / actions：

- Topic CRUD。
- Query CRUD。
- Query batch create。
- Query enable / pause / archive。
- Query metadata CRUD。
- Generated query 採納 / 編輯 / 淘汰。

### 模組 A/B：Query Generation Draft

建議把 LLM 生成結果先保存成 draft，使用者採納後才進正式 `geo_queries`。

`geo_query_generation_runs`

- `id`
- `project_id`
- `research_run_id`
- `provider`
- `model`
- `input_payload` JSON
- `status`: `completed | failed`
- `error_code`
- `created_at`

`geo_query_drafts`

- `id`
- `generation_run_id`
- `topic_name`
- `keywords` JSON
- `intent_category`
- `intent_description`
- `audience_name`
- `audience_description`
- `brand_mention_rules` JSON
- `query_text`
- `shortlisted_at`
- `shortlisted_by_user_id`
- `decision`: `pending | accepted | rejected | edited`
- `accepted_query_id`
- `created_at`
- `updated_at`

CRUD / actions：

- Create generation run。
- List drafts。
- Add draft to Shortlist。
- Remove draft from Shortlist。
- Accept draft as query。
- Reject draft。
- Edit draft then accept。

### 模組 C：Run Engine / Provider 執行

`geo_provider_configs`

- `id`
- `project_id`
- `provider`: `gemini | openai | claude | perplexity | google_aio`
- `model`
- `surface`
- `region`
- `is_enabled`
- `default_schedule`
- `cost_policy` JSON
- `created_at`
- `updated_at`

`geo_run_requests`

- `id`
- `project_id`
- `provider`
- `timing`: `run_now | next_cycle`
- `status`: `queued | running | completed | failed | cancelled`
- `created_at`
- `started_at`
- `finished_at`

`geo_run_request_queries`

- `id`
- `run_request_id`
- `query_id`
- `created_at`

`geo_run_results`

- `id`
- `run_request_id`
- `query_id`
- `provider`
- `surface`
- `model`
- `region`
- `language`
- `status`: `completed | failed`
- `raw_response`
- `reference_urls` JSON
- `grounding_metadata` JSON
- `error_code`
- `run_at`

CRUD / actions：

- Provider config CRUD。
- Create run request。
- List run requests。
- Get run result detail。
- Rerun query。
- Cancel queued run。
- Archive old runs。

### 建議後端實作順序

1. `geo_projects`、`geo_topics`、`geo_queries`。
2. `geo_query_research_runs`。
3. `geo_query_generation_runs`、`geo_query_drafts`。
4. `geo_run_requests`、`geo_run_results`。
5. `geo_provider_configs`。
6. Metadata、scheduling、archive 細節。

## 模組 B：Query / Topic 管理

### 目前完成

- Query / Topic 的 API response shape 與前端預覽。
- Generated query 目前包含 prompt text、keywords、topic、region、language、marketType、isBranded、metadata、status。
- 前端表格主欄位已對齊客戶澄清的 `Prompt / Keywords / Intent / 動作`。
- 前端可用 `+ Shortlist` 把 prompt 加入 local Shortlist，並將 Shortlist 內容送進 Run Engine。
- Dummy project 可提供前端載入範例資料。

### 尚未完成，交接後端

- Topic CRUD：新增、編輯、刪除、排序、啟停、與 SEO task/project 關聯。
- Query CRUD：新增、編輯、刪除、啟停、掛 topic、地區、語言、市場語境。
- 多題輸入：批次建立 query、批次掛 topic、批次設定地區 / 語言。
- Query metadata CRUD：標籤、來源、生成 attributes、採納狀態、備註。
- Shortlist CRUD：保存、取消、列表、批次操作、與 project / user / query draft 的關聯。
- Brand flag / query classification：品牌字、競品字、泛用 query 的判斷與保存規則。
- Query scheduling 設定：立即跑、下個週期跑、啟停、頻率、品牌字降頻。
- Tracking metrics 設定欄位：PDF 有提到追蹤指標勾選，但本輪先略過，需要後端決定是否以 query-level 或 project-level 保存。
- Query versioning：query 修改後是否保留歷史版本，需後端定義。

### 尚未完成，表單設計

- Topic 管理表單：topic name、description、排序、啟停。
- Query 編輯表單：query text、topic、region、language、marketType、status、metadata tags。
- Shortlist 狀態 UI：顯示已加入、取消加入、批次加入、依使用者或 project 過濾。
- 多題輸入表單：textarea / CSV paste、逐行 validation、批次 topic / region / language。
- Metadata 標籤表單：tag key/value、系統標籤與自訂標籤區分。
- 排程表單：run now、next cycle、週期、降頻規則。
- Query list filter：topic、region、language、status、brand flag、provider run status。

## 模組 C：跑題引擎 + AI 平台

### 目前完成

- Run Request API 可接收多筆 query 並依 provider 執行。
- Dummy Answer provider 可回傳穩定 raw response。
- Gemini Answer provider 可使用 Google Search grounding。
- Google AIO provider 可透過 SerpApi 取得 Google AI Overview；支援第一段直接 AIO 與第二段 `page_token` 流程。
- Run result 包含 provider、surface、model、region、language、status、rawResponse、referenceUrls、error、runAt。
- Run result 另包含 `references[{ title, url }]`，Gemini grounding 可從 web chunk 擷取 title，Google AIO 可從 SerpApi `references[].title/link` 擷取；若 provider 未提供 title，前端 fallback 顯示 domain / URL。
- Run failure 會回傳安全錯誤碼；未知錯誤為 `provider_request_failed`，Google AIO 無結果為 `no_google_aio_result`，並保留空 `referenceUrls`。
- 前端可選取 generated queries，使用 dummy / Gemini / Google AIO provider 跑題。

### 尚未完成，交接後端

- Run request / run result CRUD 與 DB 持久化。
- Job queue / worker 設計：同步 API 只適合 MVP demo，正式跑題應改背景工作。
- Provider adapter registry：Perplexity、ChatGPT、Claude 的正式 adapter 設計；Gemini 與 Google AIO 已有 MVP adapter，仍需補正式 provider config / credential 管理。
- Provider credential 管理：不可進 source；需設計 env / secret manager / per-workspace config。
- Provider model / surface 設定 CRUD：model name、地區支援、成本、啟停。
- Google AIO SERP vendor abstraction：目前採 SerpApi；若後續評估 DataForSEO，需抽象 vendor response contract。
- Cost control：每題每平台每日一次、品牌字降頻、重試與 timeout 策略。
- Run scheduling：立即跑、下個週期、每日排程、手動重跑。
- Grounding metadata 保存：web search queries、grounding chunks、source URLs、raw provider metadata。
- Reference URL normalization：URL 去重、domain 擷取、canonicalization。
- Provider error taxonomy：quota、auth、timeout、invalid request、blocked content、empty response。
- Observability：run status、duration、token/cost metadata、provider latency、錯誤紀錄。

### 尚未完成，表單設計

- Provider 設定表單：provider 啟停、model、region、預設頻率、credential 狀態。
- Run request 表單：選擇 queries、provider、run now / next cycle。
- Run result list：query、provider、status、runAt、reference count、error。
- Run result detail：raw response、reference URLs、grounding search queries、provider metadata。
- AIO SERP 設定表單：gl、hl、location、device、SERP API vendor。

## 驗證指令

- `uv tool run ruff format apps/geo-tracking-api packages/geo-tracking-application packages/geo-tracking-domain packages/geo-tracking-infrastructure`
- `uv tool run ruff check --target-version py312 --select E,F,I,UP --fix apps/geo-tracking-api packages/geo-tracking-application packages/geo-tracking-domain packages/geo-tracking-infrastructure`
- `uv run --package younilab-geo-tracking-infrastructure pytest packages/geo-tracking-infrastructure/tests`
- `uv run --package younilab-geo-tracking-api pytest apps/geo-tracking-api/tests`
- `npm run test:portal`
- `npm run build:portal`
- Google AIO live smoke test：設定 `SERPAPI_API_KEY` 後，用 `SerpApiGoogleAioAnswerProvider` 跑 `黃連膏 推薦` / `TW` / `zh-TW`，確認 `rawResponse` 與 `references` 非空。
- Google AIO API route smoke test：設定 `SERPAPI_API_KEY` 後，用最新版 app 呼叫 `/api/v1/geo-tracking/run-requests`，確認 `provider=google_aio`、`status=completed`、`references[{ title, url }]` 非空。

## 目前風險與注意事項

- 尚未設計資料庫，因此目前 Query Research、Generated Queries、Run Results 都不是正式持久化資料。
- Gemini grounding source URLs 依模型 metadata 而定，本輪 live test 有拿到 URL，但程式仍需允許空陣列。
- Google AIO 代表 Google SERP 上實際出現的 AI Overview surface；若 query 沒有 AIO，會回 `no_google_aio_result`，不會 fallback organic results。
- SerpApi free plan 可能一題消耗兩段 request：`engine=google` 加上必要時的 `engine=google_ai_overview`。
- Query Generation adapter 會強制把 attributes 對齊使用者輸入，避免模型改寫 intent/audience/brand rules。
- 前端目前是 MVP 操作面，不是完整 CRUD 後台。
- `workduo-survey/` 是探索資料與 PDF 來源，本輪未納入程式碼變更範圍。
