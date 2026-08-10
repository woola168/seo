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
