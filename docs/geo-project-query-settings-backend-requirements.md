# GEO Project Query Settings 後端需求

> 狀態（2026-07-19）：後端 API、persistence、migration、OpenAPI 與測試已完成；Admin Portal 的新增 Project、Project Edit 與 Query Research 預帶／更新串接仍待開發。正式環境需先執行 `019_geo_project_query_settings.sql`。

## 目的

標準版 GEO 分析的新增 Project 第二步可設定 Query Research 與 Generation 的預設值。後端目前除了 Project、品牌、競品、別名與 Topics，也已提供 Project Query Settings GET／PUT；Admin Portal 尚未串接，因此前端目前仍只在當次表單保留這些值，不會宣稱已保存。

後端已讓每個 Project 可擁有一份 `GeoProjectQuerySettings`。保存設定不得觸發 Query Research、Query Generation 或建立正式 Query；使用者進入 Query Search 時才載入預設值並自行執行。

## 資料契約

JSON 屬性使用 `camelCase`：

```json
{
  "projectId": "uuid",
  "researchProvider": "gemini",
  "runProvider": "gemini",
  "keywords": ["維他命", "益生菌"],
  "marketType": "b2b_procurement",
  "maxQueries": 8,
  "audience": {
    "name": "B2B 採購",
    "description": "正在評估供應商、產品規格與導入風險的採購或決策者"
  },
  "intent": {
    "category": "商業評估",
    "description": "比較供應商、產品方案或導入條件"
  },
  "shouldMentionOwnBrand": true,
  "shouldMentionCompetitor": true,
  "updatedAt": "2026-07-18T00:00:00Z"
}
```

Topics 已由既有 `/api/geo/projects/{projectId}/topics` 管理，不應在 Query Settings 重複保存。

## API

### `GET /api/geo/projects/{projectId}/query-settings`

- 權限：`geo.projects.read`，並沿用既有 tenant、customer、task 與 Project scope。
- 成功回傳 `200 GeoProjectQuerySettings`。
- Project 存在但尚未建立設定時回 `404` Problem Details；前端使用產品預設值。
- Project 不存在或無存取權時維持既有 Project 資源的隱藏策略。

### `PUT /api/geo/projects/{projectId}/query-settings`

- 權限：`geo.projects.update`，並沿用既有 Project scope。
- Request 採完整替換；成功建立或更新後回傳 `200 GeoProjectQuerySettings`。
- 寫入設定不得呼叫 `geo-tracking`、建立 research/generation run、draft、Query、Job 或 Schedule。
- 驗證失敗使用 RFC 7807 Problem Details 與可對應欄位的錯誤資訊。

## 驗證規則

- `researchProvider`、`runProvider` 必須來自後端 allowlist；初期至少支援 `gemini`。
- `keywords` 去除前後空白、空字串與重複值；數量上限沿用 Query Research 的正式限制。
- `marketType` 使用既有 `b2c`、`b2b_procurement` enum。
- `maxQueries` 必須為正整數，且不得超過 Query Generation 的正式上限。
- Audience 與 Intent 的名稱、描述需設定穩定的長度上限；禁止只含空白。
- 布林提及規則必須明確提供，不以缺少欄位推導值。

## 前端串接點

- 新增 Project：Project、Entities、Aliases、Topics 成功後再 PUT Query Settings；設定保存失敗不得回滾已建立的核心資料，但必須顯示部分失敗。
- Project Edit：GET 後預帶，使用者保存時更新。
- Query Search：GET 後作為可修改的初始值；若回 `404`，沿用前端產品預設值。
- 設定 API 尚未部署或暫時失敗時，既有 Project 建立、編輯與 Query Search 手動輸入仍須可用。

## 後端驗收

- 同一 tenant 的有權使用者可建立、讀取及完整替換設定。
- 缺少讀取或更新權限、跨 tenant、超出 customer/task scope 時不可取得或修改資料。
- 重複 PUT 相同 payload 產生相同可觀察結果，不建立額外 run 或 Query。
- 驗證 provider、keywords、market type、max queries、Audience 與 Intent 邊界。
- Project 刪除時設定依既有 Project 子資源策略清除；Project 下架時設定保留。
- API 測試涵蓋 404、422、權限拒絕、tenant 隔離與完整替換。

## Migration 與回復

- Migration 應建立 Project 一對一設定資料與唯一 `project_id` 約束，並遵循既有 tenant 隔離與外鍵策略。
- 不回填推測值；既有 Project 在沒有設定時由 GET 回 `404`。
- Rollback 只移除新增的設定資源，不得修改或刪除既有 Project、Entity、Alias、Topic、Query 或 run 資料。
