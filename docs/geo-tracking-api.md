# GEO Tracking API 文件

本文整理 `geo-tracking` 服務目前提供的 API、request / response 欄位與欄位用途。  
目前定位是由 `geo-analysis` 決定何時呼叫 `geo-tracking`，`geo-tracking` 只負責 Query Research、Query Generation 與 AI 跑題執行，不負責 DB 讀寫、排程、queue job 狀態或報表分析。

## 服務邊界

`geo-analysis` 負責：

- 管理 project、brand、competitor、topic、query、provider config、schedule。
- 建立 manual / scheduled job。
- 將 job 丟入 queue / Pub/Sub。
- 呼叫 `geo-tracking` 執行跑題。
- 儲存 raw response、references、provider metadata。
- 計算 visibility、SOV、mentions、citations、sentiment 等分析指標。
- 提供報表 API 給前端。

`geo-tracking` 負責：

- 根據 brand、competitor、keyword、topic、intent、audience 等資訊產生 query draft。
- 根據 brand、competitor、keyword、market 進行 query research。
- 根據 analysis 傳入的 query 呼叫 AI provider。
- 回傳 raw response、reference URLs、provider、model、status、error。

## Base URL

目前 API prefix：

```text
/api/v1/geo-tracking
```

本機前端 Vite proxy 目前會將下列路徑導到 `http://127.0.0.1:8003`：

```text
/api/v1/geo-tracking
```

## 共用列舉

### provider

| 值 | 說明 |
| --- | --- |
| `dummy` | 本機假資料 provider，用於測試流程，不會呼叫外部 AI。 |
| `gemini` | Gemini Vertex AI provider，會依設定呼叫 Gemini。 |

### region

| 值 | 說明 |
| --- | --- |
| `TW` | 台灣市場。 |
| `US` | 美國市場。 |

### marketType

| 值 | 說明 |
| --- | --- |
| `b2c` | 一般消費者市場。 |
| `b2b_procurement` | B2B 採購或企業決策情境。 |

### timing

| 值 | 說明 |
| --- | --- |
| `run_now` | 立即執行。 |
| `next_cycle` | 下一個週期執行。現階段 tracking 只回傳此欄位，不負責排程。 |

### run result status

| 值 | 說明 |
| --- | --- |
| `completed` | provider 呼叫成功並取得結果。 |
| `failed` | provider 呼叫失敗。 |

## GET /dummy-project

提供前端或測試環境使用的 seed data。  
這個 endpoint 只適合 demo / local preview，不建議 analysis 正式流程依賴它。

### Request

無 request body。

### Response

```json
{
  "seoTaskId": "11111111-1111-4111-8111-111111111111",
  "brandName": "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
  "competitorBrands": ["CEJN Industrial Corporation"],
  "keywords": ["pneumatic tubing", "air brake hose"],
  "region": "US",
  "marketType": "b2b_procurement",
  "topics": [
    {
      "name": "Supplier Evaluation",
      "description": "Evaluate supplier qualification, quality and procurement fit."
    }
  ],
  "topicNames": ["Supplier Evaluation"]
}
```

### Response 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `seoTaskId` | string UUID | 測試用 SEO task id。正式流程應由 analysis 傳入。 |
| `brandName` | string | 自有品牌名稱。 |
| `competitorBrands` | string[] | 競品品牌名稱。 |
| `keywords` | string[] | 查詢研究或 query generation 使用的 seed keywords。 |
| `region` | string | 市場區域，目前支援 `TW` / `US`。 |
| `marketType` | string | 市場類型。 |
| `topics` | object[] | topic 名稱與描述。 |
| `topicNames` | string[] | 舊版相容欄位，只提供 topic 名稱。 |

## POST /project-discovery/inspection

Stage 1 只辨識 Project 身分，不執行 Google Search。Adapter 先以 bounded HTTP fetch 擷取 title、meta、Open Graph、canonical、JSON-LD 與有限 H1/H2，再由 URL Context 搭配 `pageMetadata` 產生可編輯草稿。

```json
{
  "projectUrl": "https://www.kaiser.com.tw/",
  "language": "zh-TW"
}
```

```json
{
  "sourceUrl": "https://www.kaiser.com.tw/",
  "retrievedUrl": "https://www.kaiser.com.tw/",
  "projectName": "港香蘭藥廠股份有限公司",
  "projectDescription": "位於台灣的中藥製藥公司。",
  "projectType": "company",
  "coreOfferings": ["科學中藥"]
}
```

`projectUrl` 必須是公開 HTTP(S) URL；`language` 長度為 1-20 字。Admin Portal 會讓使用者編輯 `projectName`、`projectDescription` 與 `coreOfferings`，不會自動執行 Stage 2。

## POST /project-discovery/suggestions

Stage 2 接收使用者確認後的 `confirmedProject`，只使用 Google Search 產生直接競品、Topics 與 non-branded seed keywords。它不重新讀取 URL，也不得重新命名 confirmed Project。

```json
{
  "confirmedProject": {
    "sourceUrl": "https://www.kaiser.com.tw/",
    "retrievedUrl": "https://www.kaiser.com.tw/",
    "projectName": "港香蘭",
    "projectDescription": "提供科學中藥與中藥保健產品。",
    "projectType": "company",
    "coreOfferings": ["科學中藥"]
  },
  "region": "TW",
  "language": "zh-TW",
  "marketType": "b2c",
  "competitorCount": 5,
  "topicCount": 5,
  "keywordCount": 5
}
```

Project Discovery 不接受 Query Generation 的 `audience`。Stage 2 只依使用者確認的 Project 身分、核心產品或服務、地區、語言、市場語境與目標數量產生建議。

```json
{
  "competitors": ["順天堂藥廠", "勝昌製藥"],
  "topics": [
    {
      "name": "科學中藥製程與品質",
      "description": "探討製程、品質與產品使用情境。"
    }
  ],
  "keywords": ["科學中藥", "漢方保健食品"],
  "references": [
    {
      "title": "Google Search: 台灣科學中藥品牌",
      "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/..."
    }
  ]
}
```

`confirmedProject` 必須包含非空名稱、描述與至少一個 core offering。數量欄位仍是 target，不保證一定補滿。`references` 優先使用 grounding chunks；只有 Search Entry Point 時顯示 Google 官方搜尋 query 與 redirect。

### 錯誤

| HTTP | code | 階段 | 說明 |
| --- | --- | --- | --- |
| `422` | `insufficient_project_context` | Stage 1 | 公開內容不足以確認名稱、描述與 core offering。 |
| `422` | `invalid_confirmed_project` | Stage 2 | 使用者確認的 Project 身分缺少必要內容。 |
| `502` | `project_url_retrieval_failed` | Stage 1 | URL Context 未成功，且 bounded HTTP metadata 沒有名稱線索。 |
| `502` | `project_url_inspection_failed` | Stage 1 | Provider 呼叫或 structured output 解析失敗。 |
| `502` | `project_market_research_not_grounded` | Stage 2 | 沒有 Google Search metadata。 |
| `502` | `project_market_research_failed` | Stage 2 | 市場搜尋或 structured output 失敗。 |

兩個 endpoint 都不讀寫 DB。Admin Portal 只保存 memory draft；重新整理頁面會遺失 Stage 1 與 Stage 2 結果。

## POST /query-research

根據品牌、競品、keyword、市場、受眾資訊，產生 query generation 可參考的研究上下文。

Gemini provider 會使用 Google Search grounding。Dummy provider 只會回傳假資料。

### Request

```json
{
  "provider": "gemini",
  "brandName": "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
  "competitorBrands": ["CEJN Industrial Corporation"],
  "keywords": ["pneumatic tubing", "air brake hose"],
  "region": "US",
  "language": "en-US",
  "marketType": "b2b_procurement",
  "intents": [
    {
      "category": "commercial_investigation",
      "description": "Compare industrial tubing suppliers for procurement decisions."
    }
  ],
  "audience": {
    "name": "B2B Procurement",
    "description": "Procurement managers evaluating industrial tubing suppliers."
  },
  "brandMentionRules": {
    "shouldMentionOwnBrand": true,
    "shouldMentionCompetitor": true
  }
}
```

### Request 欄位

| 欄位 | 型態 | 必填 | 限制 | 說明 |
| --- | --- | --- | --- | --- |
| `provider` | string | 否 | `dummy` / `gemini` | 使用哪個 provider。預設 `dummy`。 |
| `brandName` | string | 是 | 1-200 字 | 自有品牌名稱。由 analysis 從 primary brand / entity 組出。 |
| `competitorBrands` | string[] | 否 | 最多 8 筆 | 競品品牌名稱。由 analysis 從 competitor entities 組出。 |
| `keywords` | string[] | 是 | 1-10 筆 | query research 使用的 seed keywords。 |
| `region` | string | 是 | `TW` / `US` | 市場區域。 |
| `language` | string \| null | 否 | 最多 20 字 | 回覆與 query generation 使用語言，例如 `zh-TW`、`en-US`。未傳時依 region 推導。 |
| `marketType` | string | 是 | `b2c` / `b2b_procurement` | 市場情境。 |
| `intents` | object[] | 否 | 最多 8 筆 | Query intent 類型與描述。 |
| `audience` | object \| null | 否 |  | 目標受眾。 |
| `brandMentionRules` | object | 否 |  | 控制研究語境是否偏向提及自有品牌或競品，未提供時使用預設值。 |

### audience 欄位

| 欄位 | 型態 | 必填 | 說明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 受眾名稱，例如 `B2B Procurement`。 |
| `description` | string | 是 | 受眾描述，會影響 research 與後續 query generation。 |

### Response

```json
{
  "researchContext": "Procurement buyers compare tubing suppliers by certifications, lead time, material compatibility and support.",
  "searchedKeywords": [
    "pneumatic tubing supplier",
    "air brake hose manufacturer"
  ],
  "sourceUrls": [
    "https://example.com/source-a",
    "https://example.com/source-b"
  ]
}
```

### Response 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `researchContext` | string | 給 query generation 使用的市場研究摘要。analysis 可保存到 research run。 |
| `searchedKeywords` | string[] | provider 實際搜尋或建議使用的 keyword。 |
| `sourceUrls` | string[] | research 使用的來源 URL。 |

### analysis 建議保存

- research run id。
- request payload snapshot。
- `researchContext`。
- `searchedKeywords`。
- `sourceUrls`。
- provider、model、createdAt、status、error。

目前 tracking response 不含 provider model 與 status，若 analysis 需要完整稽核，後續可以擴充。

## POST /query-generation

根據品牌、競品、keyword、topic、intent、audience、brand mention rules，產生可被 analysis 接受或編輯的 query draft。

目前 response 名稱是 `queries`，但從業務流程看，analysis 應先把它視為 draft；使用者確認後再寫入正式 `geo_queries`。

### Request

```json
{
  "seoTaskId": "11111111-1111-4111-8111-111111111111",
  "provider": "gemini",
  "brandName": "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
  "competitorBrands": ["CEJN Industrial Corporation"],
  "keywords": ["pneumatic tubing"],
  "region": "US",
  "language": "en-US",
  "marketType": "b2b_procurement",
  "topics": [
    {
      "name": "Supplier Evaluation",
      "description": "Compare supplier capability, certification, product quality and procurement fit."
    }
  ],
  "topicNames": ["Supplier Evaluation"],
  "intents": [
    {
      "category": "commercial_investigation",
      "description": "Buyer is comparing vendors before procurement."
    }
  ],
  "audience": {
    "name": "B2B Procurement",
    "description": "Procurement managers evaluating industrial tubing suppliers."
  },
  "brandMentionRules": {
    "shouldMentionOwnBrand": true,
    "shouldMentionCompetitor": true
  },
  "researchContext": "Procurement buyers compare tubing suppliers by certifications, lead time and material compatibility.",
  "maxQueries": 8
}
```

### Request 欄位

| 欄位 | 型態 | 必填 | 限制 | 說明 |
| --- | --- | --- | --- | --- |
| `seoTaskId` | string UUID | 是 |  | analysis 端 SEO task id 或 project 關聯 id。tracking 不會查 DB，只原樣帶入 response。 |
| `provider` | string | 否 | `dummy` / `gemini` | query generation provider。預設 `dummy`。 |
| `brandName` | string | 是 | 1-200 字 | 自有品牌名稱。 |
| `competitorBrands` | string[] | 否 | 最多 8 筆 | 競品品牌名稱。 |
| `keywords` | string[] | 是 | 1-10 筆 | 產生 query 的核心 keyword。 |
| `region` | string | 是 | `TW` / `US` | 市場區域。 |
| `language` | string \| null | 否 | 最多 20 字 | query 語言，例如 `zh-TW`、`en-US`。 |
| `marketType` | string | 是 | `b2c` / `b2b_procurement` | 市場情境。 |
| `topics` | object[] | 否 | 最多 8 筆 | topic 名稱與描述。建議新流程使用此欄位。 |
| `topicNames` | string[] | 否 | 最多 8 筆 | 舊版相容欄位，只傳 topic 名稱。 |
| `intents` | object[] | 是 | 1-8 筆 | query intent 類型與描述。 |
| `audience` | object | 是 |  | 目標受眾。 |
| `brandMentionRules` | object | 否 |  | 控制生成 query 是否應提到自有品牌或競品。 |
| `researchContext` | string \| null | 否 | 最多 5000 字 | `/query-research` 回傳的市場研究摘要，可提升生成品質。 |
| `maxQueries` | number | 否 | 1-40 | 最多產生 query 數量。預設 12。 |

### topic 欄位

| 欄位 | 型態 | 必填 | 限制 | 說明 |
| --- | --- | --- | --- | --- |
| `name` | string | 是 | 1-120 字 | topic 名稱。 |
| `description` | string | 否 | 最多 1000 字 | topic 描述，用來限制生成方向。 |

### intent 欄位

| 欄位 | 型態 | 必填 | 說明 |
| --- | --- | --- | --- |
| `category` | string | 是 | intent 類型，例如 `informational`、`commercial_investigation`、`transactional`、`navigational`。目前程式沒有硬性限制 enum。 |
| `description` | string | 是 | intent 描述，會直接影響 query generation。 |

### brandMentionRules 欄位

| 欄位 | 型態 | 預設 | 說明 |
| --- | --- | --- | --- |
| `shouldMentionOwnBrand` | boolean | `true` | 產生 query 時是否應提到自有品牌。 |
| `shouldMentionCompetitor` | boolean | `false` | 產生 query 時是否應提到競品。 |

### Response

```json
{
  "topics": [
    {
      "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      "name": "Supplier Evaluation",
      "description": "Compare supplier capability, certification, product quality and procurement fit."
    }
  ],
  "queries": [
    {
      "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      "seoTaskId": "11111111-1111-4111-8111-111111111111",
      "text": "How does SHPI compare with CEJN for pneumatic tubing supplier evaluation?",
      "keywords": ["pneumatic tubing"],
      "topicId": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      "topicName": "Supplier Evaluation",
      "region": "US",
      "language": "en-US",
      "marketType": "b2b_procurement",
      "isBranded": true,
      "attributes": {
        "intent": {
          "category": "commercial_investigation",
          "description": "Buyer is comparing vendors before procurement."
        },
        "keyword": "pneumatic tubing",
        "topicName": "Supplier Evaluation",
        "topicDescription": "Compare supplier capability, certification, product quality and procurement fit.",
        "audience": {
          "name": "B2B Procurement",
          "description": "Procurement managers evaluating industrial tubing suppliers."
        },
        "brandMentionRules": {
          "shouldMentionOwnBrand": true,
          "shouldMentionCompetitor": true
        }
      },
      "metadata": {
        "keyword": "pneumatic tubing",
        "topic": "Supplier Evaluation",
        "topicDescription": "Compare supplier capability, certification, product quality and procurement fit.",
        "intent": "commercial_investigation",
        "marketType": "b2b_procurement"
      },
      "source": "research",
      "status": "active"
    }
  ]
}
```

### Response 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `topics` | object[] | tracking 依 request topic 產生的 topic summary。analysis 可用來建立 draft topic 或對應既有 topic。 |
| `queries` | object[] | 產生的 query draft。analysis 建議先保存為 draft，人工確認後再轉正式 query。 |

### Generated query 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `id` | string UUID | tracking 產生的 query draft id。正式落 DB 時 analysis 可保留為 source id 或重新給正式 query id。 |
| `seoTaskId` | string UUID | request 傳入的 SEO task id。 |
| `text` | string | 產生的 query 文字。 |
| `keywords` | string[] | 這筆 query 實際使用到的輸入 seed keywords。tracking 會限制只能來自 request 的 `keywords`，避免模型自行發明 keyword。 |
| `topicId` | string UUID \| null | response topic id。注意這不是 analysis DB 內的正式 topic id，除非 analysis 決定沿用。 |
| `topicName` | string | topic 名稱。 |
| `region` | string | 市場區域。 |
| `language` | string | query 語言。 |
| `marketType` | string | 市場情境。 |
| `isBranded` | boolean | 目前由 `brandMentionRules.shouldMentionOwnBrand` 推導。 |
| `attributes` | object | 生成 query 的可解釋屬性。 |
| `metadata` | object | 給 analysis 保存或篩選用的 key-value metadata。 |
| `source` | string | 目前通常為 `research`。 |
| `status` | string | 目前通常為 `active`。 |

### analysis 建議處理

- 將 response `queries` 視為 `geo_query_drafts`。
- 使用者接受 draft 後，再建立正式 `geo_queries`。
- 保存 `keywords` 作為 draft 與後續 Shortlist / Runner 的 seed keyword 關聯依據。
- 不要直接假設 `topicId` 是 analysis DB 的 topic id。
- `attributes` 建議完整保存，後續可用於報表解釋、debug prompt、重跑。

## POST /run-requests

執行一批 query，呼叫指定 provider 並回傳 raw answer 與 references。

目前是同步 API：request 送出後等待 provider 執行並直接回 response。  
正式 queue 架構下，建議由 analysis worker 呼叫此 API，並將 response 寫回 analysis DB。

### Request

```json
{
  "seoTaskId": "11111111-1111-4111-8111-111111111111",
  "provider": "gemini",
  "timing": "run_now",
  "queries": [
    {
      "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      "text": "How does SHPI compare with CEJN for pneumatic tubing supplier evaluation?",
      "topicName": "Supplier Evaluation",
      "region": "US",
      "language": "en-US",
      "marketType": "b2b_procurement",
      "isBranded": true,
      "metadata": {
        "keyword": "pneumatic tubing",
        "intent": "commercial_investigation"
      }
    }
  ]
}
```

### Request 欄位

| 欄位 | 型態 | 必填 | 限制 | 說明 |
| --- | --- | --- | --- | --- |
| `seoTaskId` | string UUID | 是 |  | analysis 端 SEO task id 或 project 關聯 id。 |
| `queries` | object[] | 是 | 1-20 筆 | 本次要跑的 queries。 |
| `provider` | string | 否 | `dummy` / `gemini` | 要呼叫的 provider。預設 `dummy`。 |
| `timing` | string | 否 | `run_now` / `next_cycle` | 執行時機。tracking 目前不排程，只回傳此欄位。 |

### query 欄位

| 欄位 | 型態 | 必填 | 說明 |
| --- | --- | --- | --- |
| `id` | string UUID | 是 | analysis 正式 query id 或 draft query id。response 會用此 id 對應結果。 |
| `text` | string | 是 | 實際要問 AI provider 的 query。 |
| `topicName` | string | 是 | query 所屬 topic 名稱，用於結果上下文。 |
| `region` | string | 是 | 市場區域。 |
| `language` | string | 是 | query 語言。 |
| `marketType` | string | 是 | 市場情境。 |
| `isBranded` | boolean | 是 | 是否為 branded query。 |
| `metadata` | object | 否 | analysis 自行附加的 key-value metadata，tracking 目前不主動分析。 |

### Response

```json
{
  "id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  "seoTaskId": "11111111-1111-4111-8111-111111111111",
  "timing": "run_now",
  "results": [
    {
      "id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
      "runRequestId": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
      "queryId": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      "provider": "gemini",
      "surface": "Gemini",
      "model": "gemini-3.1-flash-lite",
      "region": "US",
      "language": "en-US",
      "status": "completed",
      "rawResponse": "SHPI and CEJN are often compared by product range, certification, lead time and application fit...",
      "referenceUrls": [
        "https://example.com/reference"
      ],
      "references": [
        {
          "url": "https://example.com/reference",
          "title": "Example reference title"
        }
      ],
      "error": null,
      "runAt": "2026-06-23T07:00:00Z"
    }
  ]
}
```

### Response 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `id` | string UUID | tracking 產生的 run request id。analysis 可保存成 external run id。 |
| `seoTaskId` | string UUID | request 傳入的 SEO task id。 |
| `timing` | string | request 傳入或預設的 timing。 |
| `results` | object[] | 每個 query 的跑題結果。 |

### result 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `id` | string UUID | tracking 產生的 result id。 |
| `runRequestId` | string UUID | 本次 run request id。 |
| `queryId` | string UUID | request query id。analysis 用此欄位對應正式 query。 |
| `provider` | string | 實際執行 provider。 |
| `surface` | string | provider surface，例如 `Gemini`、`Dummy AI`。 |
| `model` | string | provider model，例如 `gemini-3.1-flash-lite`。 |
| `region` | string | 市場區域。 |
| `language` | string | query 語言。 |
| `status` | string | `completed` 或 `failed`。 |
| `rawResponse` | string | AI provider 原始回答。analysis 應保存，後續再萃取 mention、citation、sentiment。 |
| `referenceUrls` | string[] | grounding 或 provider 回傳的 reference URL。 |
| `references` | object[] | reference 詳細資料，目前包含 `url` 與可選 `title`。 |
| `error` | string \| null | 失敗時的錯誤代碼。目前 provider exception 會回 `provider_request_failed`。 |
| `runAt` | string datetime | tracking 執行該 query 的時間。 |

### reference 欄位

| 欄位 | 型態 | 說明 |
| --- | --- | --- |
| `url` | string | 來源網址。 |
| `title` | string \| null | 來源標題。若 provider 沒有提供，可能為 `null`。 |

### analysis 建議保存

- analysis job id。
- tracking run request id。
- tracking result id。
- query id。
- provider、surface、model。
- raw response。
- reference URLs。
- references title / url。
- status、error、runAt。
- 原始 request payload snapshot。

## 錯誤行為

目前 `geo-tracking-api` 尚未像 `geo-analysis-api` 一樣加上完整 RFC 7807 Problem Details handler。  
常見錯誤會依 FastAPI / Pydantic 預設格式回傳，例如：

- request validation error：HTTP 422。
- provider exception：在 `/run-requests` 的單筆 result 內回 `status = failed`、`error = provider_request_failed`。
- query research / query generation provider exception：目前可能直接讓 request 失敗，後續應補統一錯誤格式。

## 與 geo-analysis 的建議介接 contract

正式 queue worker 呼叫 tracking 時，建議 analysis 端維持自己的 job id，並在保存 tracking response 時建立對應：

```text
geo_query_run_jobs.id
  -> tracking runRequestResult.id
  -> tracking results[].id
  -> geo_query_run_results 或 analysis result table
```

建議 analysis 傳給 tracking 的最小資料：

```json
{
  "seoTaskId": "analysis-task-id",
  "provider": "gemini",
  "timing": "run_now",
  "queries": [
    {
      "id": "analysis-query-id",
      "text": "query text",
      "topicName": "topic name",
      "region": "TW",
      "language": "zh-TW",
      "marketType": "b2b_procurement",
      "isBranded": true,
      "metadata": {
        "analysisJobId": "analysis-job-id",
        "projectId": "analysis-project-id"
      }
    }
  ]
}
```

tracking 回傳後，analysis 再負責：

- 更新 job status。
- 寫入 raw result。
- 寫入 citations / references。
- 執行 entity mention extraction。
- 執行 sentiment / citation / visibility / SOV 等分析。
- 提供前端報表。

## 後續建議補強

目前 API 可支援 Phase 1 PoC，但若要正式成為 runner service，建議補強：

- 加入 Problem Details error response。
- 在 `/query-research` 與 `/query-generation` response 補 `provider`、`model`、`status`、`error`。
- `/run-requests` request 可加入 `analysisJobId` 或 `externalJobId`，避免只能塞在 metadata。
- 補 provider timeout、quota、rate limit、retry policy。
- 補 request / response trace id。
- 補 token usage、latency、cost metadata。
- 明確定義 provider error taxonomy，例如 `quota_exceeded`、`auth_failed`、`timeout`、`blocked_content`、`empty_response`。
