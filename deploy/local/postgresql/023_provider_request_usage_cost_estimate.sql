BEGIN;

ALTER TABLE provider_request
    ADD COLUMN IF NOT EXISTS provider_region varchar(64),
    ADD COLUMN IF NOT EXISTS traffic_type varchar(64),
    ADD COLUMN IF NOT EXISTS usage_capture_status varchar(16),
    ADD COLUMN IF NOT EXISTS input_token_count bigint,
    ADD COLUMN IF NOT EXISTS output_token_count bigint,
    ADD COLUMN IF NOT EXISTS total_token_count bigint,
    ADD COLUMN IF NOT EXISTS cached_input_token_count bigint,
    ADD COLUMN IF NOT EXISTS reasoning_token_count bigint,
    ADD COLUMN IF NOT EXISTS tool_input_token_count bigint,
    ADD COLUMN IF NOT EXISTS usage_metadata jsonb,
    ADD COLUMN IF NOT EXISTS meter_usage jsonb;

UPDATE provider_request
SET usage_capture_status = CASE
        WHEN provider_code = 'google_vertex_ai' THEN 'unavailable'
        ELSE 'not_applicable'
    END
WHERE usage_capture_status IS NULL;

UPDATE provider_request
SET meter_usage = '{}'::jsonb
WHERE meter_usage IS NULL;

ALTER TABLE provider_request
    ALTER COLUMN usage_capture_status SET DEFAULT 'not_applicable',
    ALTER COLUMN usage_capture_status SET NOT NULL,
    ALTER COLUMN meter_usage SET DEFAULT '{}'::jsonb,
    ALTER COLUMN meter_usage SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_provider_request_usage_capture_status'
          AND conrelid = 'provider_request'::regclass
    ) THEN
        ALTER TABLE provider_request
            ADD CONSTRAINT ck_provider_request_usage_capture_status
            CHECK (
                usage_capture_status IN (
                    'pending', 'recorded', 'unavailable', 'not_applicable'
                )
            );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_provider_request_token_counts'
          AND conrelid = 'provider_request'::regclass
    ) THEN
        ALTER TABLE provider_request
            ADD CONSTRAINT ck_provider_request_token_counts
            CHECK (
                (input_token_count IS NULL OR input_token_count >= 0)
                AND (output_token_count IS NULL OR output_token_count >= 0)
                AND (total_token_count IS NULL OR total_token_count >= 0)
                AND (
                    cached_input_token_count IS NULL
                    OR cached_input_token_count >= 0
                )
                AND (
                    reasoning_token_count IS NULL
                    OR reasoning_token_count >= 0
                )
                AND (
                    tool_input_token_count IS NULL
                    OR tool_input_token_count >= 0
                )
            );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_provider_request_usage_metadata'
          AND conrelid = 'provider_request'::regclass
    ) THEN
        ALTER TABLE provider_request
            ADD CONSTRAINT ck_provider_request_usage_metadata
            CHECK (
                usage_metadata IS NULL
                OR jsonb_typeof(usage_metadata) = 'object'
            );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_provider_request_meter_usage'
          AND conrelid = 'provider_request'::regclass
    ) THEN
        ALTER TABLE provider_request
            ADD CONSTRAINT ck_provider_request_meter_usage
            CHECK (jsonb_typeof(meter_usage) = 'object');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS provider_pricing_rate (
    id uuid PRIMARY KEY,
    platform_code varchar(64) NOT NULL,
    provider_code varchar(64) NOT NULL,
    model varchar(128) NOT NULL,
    provider_region_class varchar(16) NOT NULL,
    traffic_type varchar(64) NOT NULL,
    meter_code varchar(64) NOT NULL,
    unit_quantity numeric(20, 4) NOT NULL,
    unit_price_usd numeric(20, 10) NOT NULL,
    effective_from timestamptz NOT NULL,
    effective_to timestamptz,
    source_url text NOT NULL,
    source_checked_at date NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ux_provider_pricing_rate_version
        UNIQUE (
            platform_code, provider_code, model, provider_region_class,
            traffic_type, meter_code, effective_from
        ),
    CONSTRAINT ck_provider_pricing_rate_region
        CHECK (provider_region_class IN ('global', 'non_global', 'any')),
    CONSTRAINT ck_provider_pricing_rate_meter
        CHECK (
            meter_code IN (
                'input_token', 'cached_input_token', 'output_token',
                'google_web_search_query'
            )
        ),
    CONSTRAINT ck_provider_pricing_rate_values
        CHECK (
            unit_quantity > 0
            AND unit_price_usd >= 0
            AND (effective_to IS NULL OR effective_to > effective_from)
        )
);

INSERT INTO provider_pricing_rate (
    id, platform_code, provider_code, model, provider_region_class,
    traffic_type, meter_code, unit_quantity, unit_price_usd,
    effective_from, effective_to, source_url, source_checked_at
) VALUES
    (
        '30000000-0000-4000-8000-000000000001', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'global', 'ON_DEMAND',
        'input_token', 1000000, 0.25, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000002', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'global', 'ON_DEMAND',
        'cached_input_token', 1000000, 0.025, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000003', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'global', 'ON_DEMAND',
        'output_token', 1000000, 1.50, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000004', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'non_global', 'ON_DEMAND',
        'input_token', 1000000, 0.275, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000005', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'non_global', 'ON_DEMAND',
        'cached_input_token', 1000000, 0.0275, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000006', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'non_global', 'ON_DEMAND',
        'output_token', 1000000, 1.65, '2026-07-01T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    ),
    (
        '30000000-0000-4000-8000-000000000007', 'gemini',
        'google_vertex_ai', 'gemini-3.1-flash-lite', 'any', 'any',
        'google_web_search_query', 1000, 14, '2026-01-05T00:00:00Z', NULL,
        'https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing',
        '2026-07-24'
    )
ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS ix_provider_pricing_rate_lookup
    ON provider_pricing_rate (
        platform_code, provider_code, model, meter_code, effective_from
    );

CREATE INDEX IF NOT EXISTS ix_provider_request_usage_status
    ON provider_request (usage_capture_status, started_at);

CREATE OR REPLACE VIEW provider_request_cost_estimate AS
WITH usage_quantities AS (
    SELECT
        request.*,
        CASE
            WHEN lower(coalesce(request.provider_region, '')) = 'global'
                THEN 'global'
            WHEN request.provider_region IS NOT NULL THEN 'non_global'
            ELSE NULL
        END AS provider_region_class,
        greatest(
            coalesce(request.input_token_count, 0)
                - coalesce(request.cached_input_token_count, 0),
            0
        ) + CASE
            WHEN request.uses_grounding THEN 0
            ELSE coalesce(request.tool_input_token_count, 0)
        END AS billable_input_token_count,
        coalesce(request.cached_input_token_count, 0)
            AS billable_cached_input_token_count,
        coalesce(request.output_token_count, 0)
            + coalesce(request.reasoning_token_count, 0)
            AS billable_output_token_count,
        CASE
            WHEN jsonb_typeof(
                request.meter_usage -> 'google_web_search_query'
            ) = 'number'
            THEN (request.meter_usage ->> 'google_web_search_query')::bigint
            ELSE 0
        END AS google_web_search_query_count
    FROM provider_request AS request
), matched_rates AS (
    SELECT
        usage.*,
        input_rate.id AS input_rate_id,
        input_rate.unit_quantity AS input_unit_quantity,
        input_rate.unit_price_usd AS input_unit_price_usd,
        cached_rate.id AS cached_input_rate_id,
        cached_rate.unit_quantity AS cached_input_unit_quantity,
        cached_rate.unit_price_usd AS cached_input_unit_price_usd,
        output_rate.id AS output_rate_id,
        output_rate.unit_quantity AS output_unit_quantity,
        output_rate.unit_price_usd AS output_unit_price_usd,
        search_rate.id AS search_rate_id,
        search_rate.unit_quantity AS search_unit_quantity,
        search_rate.unit_price_usd AS search_unit_price_usd
    FROM usage_quantities AS usage
    LEFT JOIN LATERAL (
        SELECT rate.*
        FROM provider_pricing_rate AS rate
        WHERE rate.platform_code = usage.platform_code
          AND rate.provider_code = usage.provider_code
          AND rate.model = usage.model
          AND (
              rate.provider_region_class = usage.provider_region_class
              OR rate.provider_region_class = 'any'
          )
          AND (
              rate.traffic_type = usage.traffic_type
              OR rate.traffic_type = 'any'
          )
          AND rate.meter_code = 'input_token'
          AND rate.effective_from <= usage.started_at
          AND (rate.effective_to IS NULL OR rate.effective_to > usage.started_at)
        ORDER BY
            (rate.provider_region_class = usage.provider_region_class) DESC,
            (rate.traffic_type = usage.traffic_type) DESC,
            rate.effective_from DESC
        LIMIT 1
    ) AS input_rate ON true
    LEFT JOIN LATERAL (
        SELECT rate.*
        FROM provider_pricing_rate AS rate
        WHERE rate.platform_code = usage.platform_code
          AND rate.provider_code = usage.provider_code
          AND rate.model = usage.model
          AND (
              rate.provider_region_class = usage.provider_region_class
              OR rate.provider_region_class = 'any'
          )
          AND (
              rate.traffic_type = usage.traffic_type
              OR rate.traffic_type = 'any'
          )
          AND rate.meter_code = 'cached_input_token'
          AND rate.effective_from <= usage.started_at
          AND (rate.effective_to IS NULL OR rate.effective_to > usage.started_at)
        ORDER BY
            (rate.provider_region_class = usage.provider_region_class) DESC,
            (rate.traffic_type = usage.traffic_type) DESC,
            rate.effective_from DESC
        LIMIT 1
    ) AS cached_rate ON true
    LEFT JOIN LATERAL (
        SELECT rate.*
        FROM provider_pricing_rate AS rate
        WHERE rate.platform_code = usage.platform_code
          AND rate.provider_code = usage.provider_code
          AND rate.model = usage.model
          AND (
              rate.provider_region_class = usage.provider_region_class
              OR rate.provider_region_class = 'any'
          )
          AND (
              rate.traffic_type = usage.traffic_type
              OR rate.traffic_type = 'any'
          )
          AND rate.meter_code = 'output_token'
          AND rate.effective_from <= usage.started_at
          AND (rate.effective_to IS NULL OR rate.effective_to > usage.started_at)
        ORDER BY
            (rate.provider_region_class = usage.provider_region_class) DESC,
            (rate.traffic_type = usage.traffic_type) DESC,
            rate.effective_from DESC
        LIMIT 1
    ) AS output_rate ON true
    LEFT JOIN LATERAL (
        SELECT rate.*
        FROM provider_pricing_rate AS rate
        WHERE rate.platform_code = usage.platform_code
          AND rate.provider_code = usage.provider_code
          AND rate.model = usage.model
          AND (
              rate.provider_region_class = usage.provider_region_class
              OR rate.provider_region_class = 'any'
          )
          AND (
              rate.traffic_type = usage.traffic_type
              OR rate.traffic_type = 'any'
          )
          AND rate.meter_code = 'google_web_search_query'
          AND rate.effective_from <= usage.started_at
          AND (rate.effective_to IS NULL OR rate.effective_to > usage.started_at)
        ORDER BY
            (rate.provider_region_class = usage.provider_region_class) DESC,
            (rate.traffic_type = usage.traffic_type) DESC,
            rate.effective_from DESC
        LIMIT 1
    ) AS search_rate ON true
), cost_components AS (
    SELECT
        rates.*,
        rates.billable_input_token_count
            / nullif(rates.input_unit_quantity, 0)
            * rates.input_unit_price_usd AS estimated_input_cost_usd,
        rates.billable_cached_input_token_count
            / nullif(rates.cached_input_unit_quantity, 0)
            * rates.cached_input_unit_price_usd
            AS estimated_cached_input_cost_usd,
        rates.billable_output_token_count
            / nullif(rates.output_unit_quantity, 0)
            * rates.output_unit_price_usd AS estimated_output_cost_usd,
        rates.google_web_search_query_count
            / nullif(rates.search_unit_quantity, 0)
            * rates.search_unit_price_usd AS estimated_search_cost_usd
    FROM matched_rates AS rates
), classified AS (
    SELECT
        costs.*,
        CASE
            WHEN costs.provider_code <> 'google_vertex_ai' THEN 'not_supported'
            WHEN costs.status = 'failed' AND costs.http_status BETWEEN 400 AND 599
                THEN 'not_billable'
            WHEN costs.status <> 'succeeded' THEN 'billing_uncertain'
            WHEN costs.usage_capture_status <> 'recorded'
                OR costs.input_token_count IS NULL
                OR costs.output_token_count IS NULL
                THEN 'usage_unavailable'
            WHEN costs.input_rate_id IS NULL
                OR costs.output_rate_id IS NULL
                OR (
                    costs.billable_cached_input_token_count > 0
                    AND costs.cached_input_rate_id IS NULL
                )
                OR (
                    costs.google_web_search_query_count > 0
                    AND costs.search_rate_id IS NULL
                )
                THEN 'rate_missing'
            ELSE 'estimated'
        END AS estimation_status
    FROM cost_components AS costs
)
SELECT
    classified.*,
    CASE
        WHEN estimation_status = 'not_billable' THEN 0::numeric
        WHEN estimation_status = 'estimated' THEN
            coalesce(estimated_input_cost_usd, 0)
            + coalesce(estimated_cached_input_cost_usd, 0)
            + coalesce(estimated_output_cost_usd, 0)
            + coalesce(estimated_search_cost_usd, 0)
        ELSE NULL
    END AS estimated_list_cost_usd
FROM classified;

CREATE OR REPLACE VIEW provider_request_daily_cost_estimate AS
SELECT
    (started_at AT TIME ZONE 'Asia/Taipei')::date AS usage_date,
    platform_code,
    provider_code,
    model,
    provider_region,
    traffic_type,
    use_case,
    request_kind,
    count(*) AS request_count,
    count(*) FILTER (WHERE estimation_status = 'estimated')
        AS estimated_request_count,
    count(*) FILTER (
        WHERE estimation_status NOT IN ('estimated', 'not_billable')
    ) AS unestimated_request_count,
    count(*) FILTER (WHERE estimation_status = 'billing_uncertain')
        AS billing_uncertain_request_count,
    sum(coalesce(input_token_count, 0)) AS input_token_count,
    sum(coalesce(output_token_count, 0)) AS output_token_count,
    sum(coalesce(total_token_count, 0)) AS total_token_count,
    sum(coalesce(reasoning_token_count, 0)) AS reasoning_token_count,
    sum(coalesce(cached_input_token_count, 0)) AS cached_input_token_count,
    sum(coalesce(tool_input_token_count, 0)) AS tool_input_token_count,
    sum(billable_input_token_count) AS billable_input_token_count,
    sum(billable_cached_input_token_count)
        AS billable_cached_input_token_count,
    sum(billable_output_token_count) AS billable_output_token_count,
    sum(google_web_search_query_count) AS google_web_search_query_count,
    sum(estimated_input_cost_usd)
        FILTER (WHERE estimation_status = 'estimated')
        AS estimated_input_cost_usd,
    sum(estimated_cached_input_cost_usd)
        FILTER (WHERE estimation_status = 'estimated')
        AS estimated_cached_input_cost_usd,
    sum(estimated_output_cost_usd)
        FILTER (WHERE estimation_status = 'estimated')
        AS estimated_output_cost_usd,
    sum(estimated_search_cost_usd)
        FILTER (WHERE estimation_status = 'estimated')
        AS estimated_search_cost_usd,
    sum(estimated_list_cost_usd) AS estimated_list_cost_usd
FROM provider_request_cost_estimate
GROUP BY
    (started_at AT TIME ZONE 'Asia/Taipei')::date,
    platform_code,
    provider_code,
    model,
    provider_region,
    traffic_type,
    use_case,
    request_kind;

COMMIT;
