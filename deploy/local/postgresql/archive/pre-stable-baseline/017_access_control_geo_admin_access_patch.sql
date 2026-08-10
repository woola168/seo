UPDATE role
SET permissions = permissions || '["geo.admin.access"]'::jsonb
WHERE is_system = true
  AND lower(name) = 'admin'
  AND NOT permissions ? 'geo.admin.access';
