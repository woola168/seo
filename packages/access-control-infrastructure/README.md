# Access Control Infrastructure

實作 Access Control Application 所定義的 PostgreSQL、Memory、密碼與 Token Adapter。

## 結構

- `persistence/postgres/`：SQLModel 資料表、Repository 與連線建立。
- `persistence/memory.py`：本機開發與測試用 Repository。
- `security/passwords.py`：Argon2 密碼雜湊。
- `security/tokens.py`：JWT 與 Refresh Token。
- `runtime.py`：系統時間與 UUID 產生器。
- `config.py`：環境變數設定。

外部程式應優先從 `younilab_access_control_infrastructure` 匯入公開 Adapter。
