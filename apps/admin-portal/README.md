# Admin Portal

Vue 3 管理後台，依 Youni SEO 參考切版實作登入、總覽與權限管理。

## 開發

Vite 會將 `/api` 與 `/health` 代理至 `http://127.0.0.1:8000`。

```text
npm run dev:portal
npm run test:portal
npm run build:portal
```

## 資料來源

- 登入、登出、目前使用者、capabilities、使用者、角色、權限、資源存取範圍及授權判斷使用 access-control API。
- 總覽任務、通知、部門、最後登入時間及帳號來源暫時使用 `src/mocks/` 資料。
- 暫時資料均以 `mock*` 命名並標記 `TODO(API)`。

## 待補 API

- 使用者邀請或建立、基本資料編輯、停用、啟用與刪除。
- 密碼重設與邀請信重寄。
- 部門 CRUD 與使用者部門關聯。
- 使用者最後登入時間與帳號來源。
- 使用者列表的伺服器端搜尋、篩選、排序與分頁。
- 角色重新命名、刪除及全域資源權限設定。
- 總覽 KPI、任務、通知與期間篩選資料。

尚無 API 的寫入操作只顯示「尚未開放」，不會修改本地假資料。

登入頁與權限管理的現有 API、缺少功能、資料欄位及建議開發順序，請參考
[`docs/login-permissions-backend-gaps.md`](docs/login-permissions-backend-gaps.md)。
