# Access Control Application

負責登入、角色管理、資源授權與權限判斷的 Use Case 與外部能力介面。

## 結構

- `use_cases/`：Authentication、Authorization 與 Access Management 流程。
- `interfaces/repositories.py`：Repository 能力與各 Use Case 專用組合介面。
- `interfaces/security.py`：Password Hasher 與 Token Provider。
- `interfaces/runtime.py`：Clock 與 ID Generator。
- `models.py`：Application 層輸入輸出與 Session 模型。
- `errors.py`：Application 層錯誤。

`AccessControlRepository` 是完整 Adapter 的相容總合介面。各 Use Case 應依賴
`AuthenticationRepository`、`AuthorizationRepository` 或
`AccessManagementRepository`，避免要求不需要的能力。
