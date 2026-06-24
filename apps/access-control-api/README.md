# Access Control API

SEO 後台的登入、目前使用者、權限、角色、部門、使用者與資源授權管理 API。

開發環境預設可用下列方式啟動：

```powershell
uv run uvicorn younilab_access_control_api.main:app --port 8000 --reload
```

## 前端介接共通規則

- JSON 欄位使用 `camelCase`。
- 除登入、refresh、忘記密碼、重設密碼與接受邀請外，其他 `/api` endpoint 需帶 `Authorization: Bearer <accessToken>`。
- `POST /api/auth/login` 與 `POST /api/auth/refresh` 會回傳短效 `accessToken`，並以 HttpOnly cookie `refreshToken` 保存 refresh token。
- Refresh cookie path 為 `/api/auth`，前端呼叫 refresh/logout 相關 API 時需允許 credentials。
- 錯誤回應使用 `application/problem+json`。

Problem Details 格式：

```json
{
  "type": "about:blank",
  "title": "Authentication required",
  "status": 401,
  "detail": "The session is missing, invalid, or expired.",
  "instance": "/api/me",
  "code": "OPTIONAL_STABLE_CODE"
}
```

## Authentication

| Method | Path | Auth | Request | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/api/auth/login` | 不需 Bearer | `LoginRequest` | `TokenResponse` |
| `POST` | `/api/auth/refresh` | refresh cookie | 無 body | `TokenResponse` |
| `POST` | `/api/auth/logout` | Bearer | 無 body | `204` |
| `POST` | `/api/auth/logout-all` | Bearer | 無 body | `204` |
| `POST` | `/api/auth/password-reset-requests` | 不需 Bearer | `PasswordResetRequest` | `202` |
| `POST` | `/api/auth/password-resets` | 不需 Bearer | `ResetPasswordRequest` | `204` |
| `POST` | `/api/auth/user-invitations/accept` | 不需 Bearer | `AcceptInvitationRequest` | `204` |

Request / response shape：

```json
// LoginRequest
{
  "email": "admin@example.com",
  "password": "password"
}

// TokenResponse
{
  "accessToken": "jwt",
  "tokenType": "bearer",
  "expiresAt": "2026-06-22T10:00:00Z"
}

// PasswordResetRequest
{
  "email": "user@example.com"
}

// ResetPasswordRequest / AcceptInvitationRequest
{
  "token": "token",
  "newPassword": "at-least-12-chars"
}
```

## Current User

| Method | Path | Permission | Response |
| --- | --- | --- | --- |
| `GET` | `/api/me` | 已登入 | `UserResponse` |
| `GET` | `/api/me/capabilities` | 已登入 | `CapabilitiesResponse` |

```json
// UserResponse
{
  "id": "uuid",
  "email": "user@example.com",
  "displayName": "User Name",
  "status": "active",
  "roleIds": ["uuid"],
  "departmentId": "uuid",
  "authProvider": "password",
  "lastLoginAt": "2026-06-22T10:00:00Z",
  "invitedAt": null,
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}

// CapabilitiesResponse
{
  "permissions": ["users.read"],
  "hasGlobalResourceAccess": false,
  "customerIds": ["uuid"],
  "taskIds": ["uuid"]
}
```

## Authorization

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `POST` | `/api/authorization/evaluate` | 自查不需額外 permission；查他人需 `authorization.evaluate` | `AuthorizationRequest` | `AuthorizationDecision` |
| `POST` | `/api/authorization/batch-evaluate` | 同上 | `BatchAuthorizationRequest` | `BatchAuthorizationDecision` |

```json
// AuthorizationRequest
{
  "userId": "uuid",
  "permission": "tasks.read",
  "resource": {
    "type": "task",
    "id": "uuid",
    "customerId": "uuid"
  }
}

// AuthorizationDecision
{
  "allowed": true,
  "reasonCode": "allowed"
}
```

`resource.type` 目前支援 `customer` 與 `task`。Batch request 最多 100 筆。

## Access Management

### Permissions / Roles

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/api/permissions` | `permissions.read` | 無 | `string[]` |
| `GET` | `/api/roles` | `roles.read` | 無 | `RoleResponse[]` |
| `POST` | `/api/roles` | `roles.manage` | `CreateRoleRequest` | `201 RoleResponse` |
| `PUT` | `/api/roles/{roleId}/permissions` | `roles.manage` | `ReplacePermissionsRequest` | `RoleResponse` |
| `DELETE` | `/api/roles/{roleId}` | `roles.manage` | 無 | `204` |

```json
// CreateRoleRequest / ReplacePermissionsRequest
{
  "name": "Editor",
  "permissions": ["tasks.read", "tasks.update"]
}

// RoleResponse
{
  "id": "uuid",
  "name": "Editor",
  "permissions": ["tasks.read"],
  "isSystem": false,
  "hasGlobalResourceAccess": false
}
```

### Users / Invitations

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/api/users` | `users.read` + `access-grants.read` | 無 | `UserAccessResponse[]` |
| `GET` | `/api/users/{userId}` | `users.read` + `access-grants.read` | 無 | `UserAccessResponse` |
| `PATCH` | `/api/users/{userId}` | `users.manage` | `UpdateUserRequest` | `UserAccessResponse` |
| `PATCH` | `/api/users/{userId}/status` | `users.manage` | `UpdateUserStatusRequest` | `UserAccessResponse` |
| `DELETE` | `/api/users/{userId}` | `users.manage` | 無 | `204` |
| `POST` | `/api/users/{userId}/sessions/revoke` | `users.manage` | 無 | `204` |
| `POST` | `/api/users/{userId}/password-reset` | `users.manage` | 無 | `202` |
| `POST` | `/api/user-invitations` | `users.manage` | `CreateInvitationRequest` | `201 UserInvitationResponse` |
| `POST` | `/api/user-invitations/{invitationId}/resend` | `users.manage` | 無 | `202 UserInvitationResponse` |
| `DELETE` | `/api/user-invitations/{invitationId}` | `users.manage` | 無 | `204` |

```json
// UpdateUserRequest
{
  "displayName": "User Name",
  "departmentId": "uuid"
}

// UpdateUserStatusRequest
{
  "status": "active"
}

// CreateInvitationRequest
{
  "email": "new-user@example.com",
  "displayName": "New User",
  "departmentId": "uuid",
  "roleIds": ["uuid"],
  "customerIds": ["uuid"],
  "taskIds": ["uuid"],
  "sendInvitation": true
}

// UserAccessResponse
{
  "id": "uuid",
  "email": "user@example.com",
  "displayName": "User Name",
  "status": "active",
  "roleIds": ["uuid"],
  "departmentId": "uuid",
  "authProvider": "password",
  "lastLoginAt": null,
  "invitedAt": null,
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z",
  "customerIds": ["uuid"],
  "taskIds": ["uuid"]
}
```

### Departments

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `GET` | `/api/departments` | `departments.read` | 無 | `DepartmentResponse[]` |
| `POST` | `/api/departments` | `departments.manage` | `SaveDepartmentRequest` | `201 DepartmentResponse` |
| `PATCH` | `/api/departments/{departmentId}` | `departments.manage` | `SaveDepartmentRequest` | `DepartmentResponse` |
| `DELETE` | `/api/departments/{departmentId}` | `departments.manage` | 無 | `204` |

```json
// SaveDepartmentRequest
{
  "name": "SEO Team",
  "description": "SEO operations"
}

// DepartmentResponse
{
  "id": "uuid",
  "name": "SEO Team",
  "description": "SEO operations",
  "memberCount": 3,
  "createdAt": "2026-06-22T10:00:00Z",
  "updatedAt": "2026-06-22T10:00:00Z"
}
```

### Resource Grants

| Method | Path | Permission | Request | Response |
| --- | --- | --- | --- | --- |
| `PUT` | `/api/users/{userId}/roles` | `users.manage` | `ReplaceRolesRequest` | `UserAccessResponse` |
| `PUT` | `/api/users/{userId}/customer-access-grants` | `access-grants.manage` | `ReplaceCustomerGrantsRequest` | `UserAccessResponse` |
| `PUT` | `/api/users/{userId}/task-access-grants` | `access-grants.manage` | `ReplaceTaskGrantsRequest` | `UserAccessResponse` |

```json
// ReplaceRolesRequest
{
  "roleIds": ["uuid"]
}

// ReplaceCustomerGrantsRequest
{
  "customerIds": ["uuid"]
}

// ReplaceTaskGrantsRequest
{
  "taskIds": ["uuid"]
}
```

## Health

| Method | Path | Auth | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | 不需 Bearer | `{ "status": "ok" }` |
