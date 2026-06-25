# 登入頁與權限管理後端缺口

本文只整理 Admin Portal 的登入頁與權限管理，不包含總覽、任務、通知或其他後台模組。

## 目前已串接 API

### 登入與 Session

| 功能 | API | 前端使用狀態 |
| --- | --- | --- |
| 帳號密碼登入 | `POST /api/auth/login` | 已串接 |
| 更新 Access Token | `POST /api/auth/refresh` | 已串接，使用 HttpOnly refresh cookie |
| 登出目前 Session | `POST /api/auth/logout` | 已串接 |
| 登出所有 Session | `POST /api/auth/logout-all` | API 已存在，登入頁目前沒有操作入口 |
| 目前使用者 | `GET /api/me` | 已串接 |
| 目前使用者能力 | `GET /api/me/capabilities` | 已串接 |

### 權限管理

| 功能 | API | 需要的 Permission |
| --- | --- | --- |
| 查詢 Permission 清單 | `GET /api/permissions` | `permissions.read` |
| 查詢角色 | `GET /api/roles` | `roles.read` |
| 建立角色 | `POST /api/roles` | `roles.manage` |
| 更新角色 Permission | `PUT /api/roles/{roleId}/permissions` | `roles.manage` |
| 查詢員工 | `GET /api/users` | `users.read` |
| 查詢單一員工 | `GET /api/users/{userId}` | `users.read` |
| 更新員工角色 | `PUT /api/users/{userId}/roles` | `users.manage` |
| 更新客戶存取範圍 | `PUT /api/users/{userId}/customer-access-grants` | `access-grants.manage` |
| 更新任務存取範圍 | `PUT /api/users/{userId}/task-access-grants` | `access-grants.manage` |
| 執行授權判斷 | `POST /api/authorization/evaluate` | 判斷自己不需要額外 Permission；判斷他人需要 `authorization.evaluate` |

## 登入頁缺口

### P0：畫面已有入口但尚無功能

#### Google 登入

目前「使用 Google 帳號登入」只顯示尚未開放。

後端需要提供 Google OAuth／OIDC 流程，完成後應回到與帳密登入相同的 Session 契約：

- Google authorize URL 或導向端點。
- OAuth callback 或 authorization code exchange 端點。
- Google 帳號與系統使用者的綁定規則。
- 不存在、未啟用或尚未獲准帳號的處理規則。
- 成功後簽發 access token 與 refresh cookie。

建議回傳或保存的資料：

- `provider`
- `providerSubject`
- `email`
- `displayName`
- `accountStatus`
- `accessToken`
- `expiresAt`

#### 忘記密碼與重設密碼

目前「忘記密碼」只顯示尚未開放。

建議 API：

| 功能 | 建議 API | 必要資料 |
| --- | --- | --- |
| 申請密碼重設 | `POST /api/auth/password-reset-requests` | `email` |
| 確認重設密碼 | `POST /api/auth/password-resets` | `token`、`newPassword` |

安全要求：

- 申請端點不應洩漏 Email 是否存在，統一回傳 `202 Accepted`。
- Token 必須有期限、只能使用一次，並可在重設成功後撤銷既有 Session。
- 密碼規則與欄位錯誤應以可辨識的 Problem Details 回傳。

#### 記住我

目前 checkbox 只保存前端狀態，沒有影響 Session 有效期限；access token 固定存於 `sessionStorage`。

後端需要先定義 Session 策略：

- 登入 request 增加 `rememberMe`，由後端決定 refresh session 有效期限；或
- 提供固定的短期／長期 Session policy。

回應應明確提供：

- `expiresAt`：沿用現有 access token 到期欄位
- `refreshSessionExpiresAt`
- `remembered`

### P1：頁面資料或流程尚未完成

#### 申請試用

目前「申請試用」只顯示尚未開放。

建議建立獨立的申請流程，不直接建立 active 使用者：

| 功能 | 建議 API | 必要資料 |
| --- | --- | --- |
| 建立試用申請 | `POST /api/trial-requests` | 聯絡人、Email、公司／團隊名稱、需求說明 |
| 查詢申請狀態 | `GET /api/trial-requests/{requestId}` | `requestId` 或安全查詢憑證 |

建議狀態：

- `submitted`
- `reviewing`
- `approved`
- `rejected`

#### 系統狀態與版本

登入頁目前固定顯示「系統狀態：正常 · v0.1.0」。現有 `/health` 只足以判斷服務是否可用，版本仍是前端常數。

建議擴充 health／status response：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development"
}
```

## 權限管理缺口

### P0：員工生命週期

目前「新增員工」與「更多操作」只顯示尚未開放。

建議 API：

| 功能 | 建議 API | 建議 Permission |
| --- | --- | --- |
| 邀請員工 | `POST /api/user-invitations` | `users.manage` |
| 重寄邀請 | `POST /api/user-invitations/{invitationId}/resend` | `users.manage` |
| 取消邀請 | `DELETE /api/user-invitations/{invitationId}` | `users.manage` |
| 編輯員工基本資料 | `PATCH /api/users/{userId}` | `users.manage` |
| 啟用／停用帳號 | `PATCH /api/users/{userId}/status` | `users.manage` |
| 刪除帳號 | `DELETE /api/users/{userId}` | `users.manage` |
| 管理員觸發密碼重設 | `POST /api/users/{userId}/password-reset` | `users.manage` |
| 撤銷員工所有 Session | `POST /api/users/{userId}/sessions/revoke` | `users.manage` |

邀請／建立員工至少需要：

- `email`
- `displayName`
- `departmentId`
- `roleIds`
- `customerIds`
- `taskIds`
- `sendInvitation`

狀態至少需要支援：

- `invited`
- `active`
- `disabled`

刪除、停用自己或最後一位管理員時，後端必須有明確保護規則。

### P0：員工列表查詢

目前搜尋、角色／部門／狀態篩選、排序及分頁全部在前端處理。資料量增加後需要改為伺服器端查詢。

建議擴充：

```text
GET /api/users
  ?search=
  &roleId=
  &departmentId=
  &status=
  &sort=displayName|email|role|department|status|lastLoginAt
  &direction=asc|desc
  &page=1
  &pageSize=20
```

建議 response：

```json
{
  "items": [],
  "page": 1,
  "pageSize": 20,
  "total": 0,
  "totalPages": 0
}
```

員工列表目前缺少的正式資料：

- `departmentId`
- `departmentName`
- `lastLoginAt`
- `source` 或 `authProvider`
- `createdAt`
- `updatedAt`
- `invitedAt`

目前 `department`、`lastLogin`、`source` 由前端 mock 補入。

### P0：Access Grant 讀取授權

目前 `GET /api/users` 與 `GET /api/users/{userId}` 只要求 `users.read`，但 response 同時包含 `customerIds` 與 `taskIds`。現有 `access-grants.read` 尚未真正保護這些資料。

後端應選擇一種契約：

1. 查詢使用者時同時要求 `users.read` 與 `access-grants.read`。
2. 使用者 response 不回傳 grants，另提供受 `access-grants.read` 保護的端點：

```text
GET /api/users/{userId}/access-grants
```

第二種方式能讓員工基本資料與資源授權資料的權限邊界更清楚。

### P0：部門管理

目前部門名稱、說明與成員數都是假資料，「管理部門」尚未開放。現有 Permission 清單也沒有部門專用權限。

建議新增 Permission：

- `departments.read`
- `departments.manage`

建議 API：

| 功能 | 建議 API |
| --- | --- |
| 查詢部門 | `GET /api/departments` |
| 建立部門 | `POST /api/departments` |
| 編輯部門 | `PATCH /api/departments/{departmentId}` |
| 刪除部門 | `DELETE /api/departments/{departmentId}` |
| 指派員工部門 | `PUT /api/users/{userId}/department` |

部門資料至少需要：

- `id`
- `name`
- `description`
- `memberCount`
- `createdAt`
- `updatedAt`

刪除仍有成員的部門時，需要定義拒絕、清空或移轉規則。

### P1：角色完整管理

目前只能建立角色及替換 Permission，缺少以下功能：

| 功能 | 建議 API |
| --- | --- |
| 角色重新命名 | `PATCH /api/roles/{roleId}` |
| 設定全域資源權限 | `PATCH /api/roles/{roleId}` |
| 刪除角色 | `DELETE /api/roles/{roleId}` |

更新 request 建議支援：

```json
{
  "name": "Content Reviewer",
  "hasGlobalResourceAccess": false
}
```

後端需要保護：

- `isSystem=true` 的角色不可刪除，或只能進行受限修改。
- 角色仍被使用者引用時，刪除應回傳 `409 Conflict`。
- 角色名稱重複應回傳 `409 Conflict`，並提供穩定錯誤代碼。

### P1：客戶與任務選擇資料

目前資源範圍與授權判斷只能手動輸入 UUID，無法顯示客戶或任務名稱。

需要由客戶／任務服務提供可搜尋的選擇資料：

| 資料 | 必要欄位 |
| --- | --- |
| 客戶 | `id`、`name`、`status` |
| 任務 | `id`、`name`、`customerId`、`customerName`、`status` |

建議查詢能力：

```text
GET /api/customers?search=&page=&pageSize=
GET /api/tasks?search=&customerId=&page=&pageSize=
```

access-control API 仍只保存資源 ID；資源名稱與狀態應由資源所屬服務維護。

### P1：錯誤契約

目前重複角色名稱等錯誤只會得到通用的 `400 Invalid request`，前端無法針對欄位顯示原因。

建議 Problem Details 增加穩定欄位：

```json
{
  "type": "https://example.com/problems/role-name-conflict",
  "title": "Role name already exists",
  "status": 409,
  "detail": "A role with this name already exists.",
  "code": "ROLE_NAME_CONFLICT",
  "errors": {
    "name": ["角色名稱已被使用"]
  }
}
```

優先需要區分：

- Email 已存在。
- 邀請已存在或已失效。
- 角色名稱重複。
- 系統角色不可修改或刪除。
- 角色仍被使用。
- UUID 格式錯誤。
- 客戶或任務不存在。
- 不允許修改自己或最後一位管理員。

## 建議開發順序

1. 補上 Access Grant 讀取授權邊界。
2. 完成員工邀請、狀態管理與基本資料編輯。
3. 將員工列表改為伺服器端搜尋、篩選、排序與分頁。
4. 完成部門 CRUD、員工部門關聯與部門 Permission。
5. 完成密碼重設、Google 登入與記住我 Session 策略。
6. 補齊角色重新命名、全域資源權限與刪除。
7. 串接客戶／任務選擇資料，取代 UUID 手動輸入。
8. 完成申請試用、系統狀態與版本資料。
