-- Roles they already hold
SELECT role_name FROM svv_user_grants WHERE user_name = 'pgat_referenceusername';

-- Legacy groups they to
SELECT groname FROM pg_group
WHERE (SELECT usesysid FROM pg_user WHERE usename = 'pgat_referenceusername') = ANY(grolist);

-- Database, schema and table/view privileges granted directly to them
SELECT n.nspname AS schema_name,
       has_schema_privilege('pgat_referenceusername', n.nspname, 'USAGE')  AS can_use,
       has_schema_privilege('pgat_referenceusername', n.nspname, 'CREATE') AS can_create
FROM pg_namespace n
WHERE n.nspname NOT LIKE 'pg\\_%' AND n.nspname NOT IN ('information_schema')
  AND has_schema_privilege('pgat_referenceusername', n.nspname, 'USAGE')
ORDER BY 1;

-- Tables/views they can read, summarized per schema
SELECT schemaname,
       COUNT(*) AS readable_tables
FROM (
  SELECT schemaname, tablename FROM pg_tables
  UNION ALL
  SELECT schemaname, viewname FROM pg_views
) t
WHERE schemaname NOT LIKE 'pg\\_%' AND schemaname <> 'information_schema'
  AND has_table_privilege('pgat_referenceusername', schemaname || '.' || tablename, 'SELECT')
GROUP BY 1
ORDER BY 1;