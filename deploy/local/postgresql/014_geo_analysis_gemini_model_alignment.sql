UPDATE geo_ai_platform
SET
    default_model = 'gemini-3.1-flash-lite',
    updated_at = now()
WHERE code = 'gemini'
  AND default_model IS DISTINCT FROM 'gemini-3.1-flash-lite';
