# Access Control Domain

SEO 後台權限控管的領域模型與授權規則，不依賴 FastAPI、資料庫或加密套件。

## 結構

- `accounts.py`：帳號狀態與使用者模型。
- `roles.py`：角色與角色權限。
- `resources.py`：客戶、任務與受保護資源。
- `permissions.py`：系統允許的權限集合。
- `policy.py`：權限與資源範圍的授權判斷。

外部程式應從 `younilab_access_control_domain` 匯入公開型別，不直接依賴內部檔案位置。
