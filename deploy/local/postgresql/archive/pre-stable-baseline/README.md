# Pre-Stable PostgreSQL History

此目錄保留 stable baseline 建立前的 schema、patch 與資料轉換 SQL，僅供歷史追溯及既有環境稽核。

新環境不得執行這些檔案；請改用 `../../baseline/`。已完成這些 patches 的既有環境也不得重跑 baseline。後續 active migration 從 `deploy/local/postgresql/027_*.sql` 開始。
