# GEO Analysis Scheduler

常駐的每日排程服務。系統會在 `03:00 Asia/Taipei`，依當下 active Project × active Query × active Platform 建立不可變的執行 snapshot，再發布到各 provider queue。任何非 active Platform 都不會納入，query-platform assignment 不參與 daily scheduler。

Scheduler 每 60 秒輪詢一次，只 materialize 當日批次，不回補歷史日期。批次與 scheduled job 的資料庫唯一索引是主要去重機制，因此重啟或誤開兩個 instance 仍不會建立重複工作；正式部署仍只啟動一個 instance。

必要環境變數：

- `GEO_ANALYSIS_DATABASE_URL`
- `GEO_ANALYSIS_RABBITMQ_URL`
- `GEO_ANALYSIS_CALLBACK_BASE_URL`

排程環境變數：

- `GEO_SCHEDULER_TIMEZONE`，預設 `Asia/Taipei`
- `GEO_SCHEDULER_DAILY_TIME`，預設 `03:00`
- `GEO_SCHEDULER_POLL_SECONDS`，預設 `60`

Provider credential 不應注入此服務。各 Platform 必須在對應執行服務完成 credential 注入與 smoke test 後，才將狀態改為 `active`。

Provider 已執行但結果無法保存時，Worker 會記錄 structured exception 並 ack message，不會重新呼叫 Provider，也不會將此情境送入 DLQ。Job 會維持 `running_external`，待 reconciliation 標記為 `execution_outcome_unknown`。DLQ 僅用於 Provider 尚未開始前、超過 delivery 次數的 message。
