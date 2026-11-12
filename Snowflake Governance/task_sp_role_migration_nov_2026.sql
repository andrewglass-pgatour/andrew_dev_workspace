/* =====================================================================
   Snowflake Trust Center: move stored procedure / task ownership off
   ACCOUNTADMIN / SECURITYADMIN
   ---------------------------------------------------------------------
   Pattern: inventory -> map to domain roles -> dry run -> migrate (logged)
            -> backfill privileges -> verify -> (rollback if needed)

   Design choices (governance first):
   * One owner role PER DOMAIN, not one global role. A single "new" role
     owning everything just recreates ACCOUNTADMIN's blast radius. DSAR /
     PII-deletion procs get their own role so their grants are auditable.
   * GRANT OWNERSHIP ... COPY CURRENT GRANTS so existing EXECUTE/USAGE
     grants to callers are not wiped.
   * Owner roles get NO MANAGE GRANTS, CREATE INTEGRATION, etc. by default.
     Procs that truly need them are isolated in section 7 for review.
   * Run sections 1-5 as ACCOUNTADMIN once (only a current owner or
     MANAGE GRANTS can transfer ownership). After this, nothing new
     should be created under ACCOUNTADMIN.
   ===================================================================== */

-- ---------------------------------------------------------------------
-- 0. WORKSPACE
-- ---------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
CREATE SCHEMA IF NOT EXISTS GOVERNANCE_DB.ROLE_MIGRATION;
USE SCHEMA GOVERNANCE_DB.ROLE_MIGRATION;

-- ---------------------------------------------------------------------
-- 1. DOMAIN MAP  (edit me; first match by PRIORITY wins)
--    TARGET_ROLE = 'EXCLUDE' -> skipped (vendor/Snowflake-managed)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE OWNER_MAP (
  DB_PATTERN VARCHAR, SCHEMA_PATTERN VARCHAR, TARGET_ROLE VARCHAR, PRIORITY INT, NOTE VARCHAR);

INSERT INTO OWNER_MAP VALUES
 ('SAMOOHA_BY_SNOWFLAKE_LOCAL_DB','%','EXCLUDE',1,'Snowflake-managed app DB. Do not alter; raise Trust Center exception / Snowflake support'),
 ('HABU_CLEAN_ROOM_COMMON','%','EXCLUDE',2,'Habu-installed framework. Confirm with vendor BEFORE moving ownership (see sec. 7)'),
 ('SIDECAR','%','EXCLUDE',3,'Review: unknown purpose, confirm owner team'),
 ('ONETRUST_ADMIN','%','PROC_OWNER_PRIVACY',10,'Needs MANAGE GRANTS-like work; see sec. 7'),
 ('PGAT','ONETRUST','PROC_OWNER_PRIVACY',11,'DSAR / PII deletion'),
 ('GOVERNANCE_DB','SCH','PROC_OWNER_PRIVACY',12,'OneTrust builders; AUTO_TAG_CLASSIFICATION may need its own role'),
 ('PGAT','GOVERNANCE','PROC_OWNER_GOV_GRANTS',13,'Grant-issuing procs; sec. 7'),
 ('%GOLDEN%','%','PROC_OWNER_GOLDEN',20,'Golden record (PII identity resolution)'),
 ('PGAT','GR_TESTING','PROC_OWNER_GOLDEN',21,''),
 ('PGAT_UAT','GOLDEN','PROC_OWNER_GOLDEN',22,''),
 ('GCP','GOLDEN','PROC_OWNER_GOLDEN',23,''),
 ('PGAT','GIGYA','PROC_OWNER_GIGYA',30,'External sync / registration PII'),
 ('BRAZE_CLOUD_PRODUCTION','%','PROC_OWNER_BRAZE',31,'External API'),
 ('PGAT','BRAZE','PROC_OWNER_BRAZE',32,''),
 ('PGAT','KORE%','PROC_OWNER_INGEST',40,'Airbyte loads'),
 ('PGAT','AIRBYTE%','PROC_OWNER_INGEST',41,''),
 ('PGAT','FLYWHEEL_DATASETS','PROC_OWNER_FLYWHEEL',50,''),
 ('PGAT','LAVA','PROC_OWNER_FLYWHEEL',51,''),
 ('GALE%','%','PROC_OWNER_GALE',60,''),
 ('PGAT','GALE%','PROC_OWNER_GALE',61,''),
 ('PGAT','ARCHTICS%','PROC_OWNER_TICKETING',70,'S3 unload procs; need storage integration USAGE'),
 ('PGAT','VOLUNTEERS','PROC_OWNER_TICKETING',71,''),
 ('PGAT','TOURNAMENT_MARKETING','PROC_OWNER_TICKETING',72,''),
 ('PGAT','%','PROC_OWNER_PGAT_MISC',99,'Catch-all: DAZN, MARKETO, LOOKUP, FORMSTACK, WIT, GENIUS_FANTASY, CUSTOM_IDENTITY'),
 ('%','%','PROC_OWNER_UNMAPPED',100,'Anything else: review before use');

-- ---------------------------------------------------------------------
-- 2. INVENTORY  (procedures + tasks currently owned by the risky roles)
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE INVENTORY (
  OBJ_TYPE VARCHAR, DB VARCHAR, SCH VARCHAR, NAME VARCHAR, ARG_TYPES VARCHAR,
  OWNER VARCHAR, TASK_STATE VARCHAR, IS_ROOT BOOLEAN, WAREHOUSE VARCHAR);

-- Procedures (ACCOUNT_USAGE lags up to ~2h; use SHOW PROCEDURES per DB if you need real time)
INSERT INTO INVENTORY
SELECT 'PROCEDURE', PROCEDURE_CATALOG, PROCEDURE_SCHEMA, PROCEDURE_NAME,
       -- "(A VARCHAR, B NUMBER)" -> "(VARCHAR, NUMBER)"
       REGEXP_REPLACE(ARGUMENT_SIGNATURE, '(\\(|, )[A-Za-z0-9_]+ ', '\\1'),
       PROCEDURE_OWNER, NULL, NULL, NULL
FROM SNOWFLAKE.ACCOUNT_USAGE.PROCEDURES
WHERE DELETED IS NULL AND PROCEDURE_OWNER IN ('ACCOUNTADMIN','SECURITYADMIN');

-- Tasks
SHOW TASKS IN ACCOUNT;
INSERT INTO INVENTORY
SELECT 'TASK', "database_name", "schema_name", "name", NULL, "owner", "state",
       COALESCE("predecessors",'[]') IN ('[]',''), "warehouse"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
WHERE "owner" IN ('ACCOUNTADMIN','SECURITYADMIN');

CREATE OR REPLACE VIEW RESOLVED AS
SELECT i.*, m.TARGET_ROLE
FROM INVENTORY i
JOIN OWNER_MAP m ON i.DB ILIKE m.DB_PATTERN AND i.SCH ILIKE m.SCHEMA_PATTERN
QUALIFY ROW_NUMBER() OVER (PARTITION BY i.OBJ_TYPE,i.DB,i.SCH,i.NAME,COALESCE(i.ARG_TYPES,'') ORDER BY m.PRIORITY) = 1;

-- Sanity: counts per role; review PROC_OWNER_UNMAPPED / EXCLUDE before continuing
SELECT TARGET_ROLE, OBJ_TYPE, COUNT(*) N FROM RESOLVED GROUP BY ALL ORDER BY 1,2;

-- ---------------------------------------------------------------------
-- 3. CREATE OWNER ROLES  (under SYSADMIN, never ACCOUNTADMIN)
-- ---------------------------------------------------------------------
USE ROLE USERADMIN;
EXECUTE IMMEDIATE $$
BEGIN
  FOR r IN (SELECT DISTINCT TARGET_ROLE AS ROLE_NAME
            FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED WHERE TARGET_ROLE <> 'EXCLUDE') DO
    EXECUTE IMMEDIATE 'CREATE ROLE IF NOT EXISTS ' || r.ROLE_NAME
      || ' COMMENT = ''Least-privilege owner for stored procs/tasks. Created by Trust Center remediation.''';
    EXECUTE IMMEDIATE 'GRANT ROLE ' || r.ROLE_NAME || ' TO ROLE SYSADMIN';
  END FOR;
END;
$$;

-- Account-level privilege tasks need (no MANAGE GRANTS / CREATE INTEGRATION here)
USE ROLE ACCOUNTADMIN;
EXECUTE IMMEDIATE $$
BEGIN
  FOR r IN (SELECT DISTINCT TARGET_ROLE AS ROLE_NAME
            FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
            WHERE TARGET_ROLE <> 'EXCLUDE' AND OBJ_TYPE = 'TASK') DO
    EXECUTE IMMEDIATE 'GRANT EXECUTE TASK ON ACCOUNT TO ROLE ' || r.ROLE_NAME;
  END FOR;
END;
$$;

-- ---------------------------------------------------------------------
-- 4. PRIVILEGE BACKFILL  (do BEFORE migrating or jobs will fail)
--    Procs defined EXECUTE AS OWNER run with the NEW owner's rights.
--    Check each: DESCRIBE PROCEDURE <db>.<sch>.<name>(<types>);  -> "execute as"
--    EXECUTE AS CALLER procs are unaffected by owner change.
-- ---------------------------------------------------------------------
-- Template per role (repeat per DB/schema the role's objects touch):
-- GRANT USAGE ON DATABASE   <db>               TO ROLE PROC_OWNER_X;
-- GRANT USAGE ON SCHEMA     <db>.<sch>         TO ROLE PROC_OWNER_X;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA <db>.<sch> TO ROLE PROC_OWNER_X;  -- only what is needed
-- GRANT SELECT ON FUTURE TABLES IN SCHEMA <db>.<sch> TO ROLE PROC_OWNER_X;                       -- only if needed
-- GRANT USAGE ON WAREHOUSE  <wh>               TO ROLE PROC_OWNER_X;   -- also each task's WAREHOUSE (see INVENTORY)
-- GRANT USAGE ON INTEGRATION <storage_or_api_integration> TO ROLE PROC_OWNER_X;  -- S3 unloads, Braze/Gigya API
-- GRANT READ ON SECRET / USAGE ON NETWORK RULE ...  -- external access integrations
--
-- Find what a proc actually touches: SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
-- (run the proc in test under the new role and read QUERY_HISTORY errors).

-- ---------------------------------------------------------------------
-- 5. DRY RUN: the exact statements that will execute
-- ---------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
SELECT OBJ_TYPE, TARGET_ROLE,
  CASE OBJ_TYPE
    WHEN 'PROCEDURE' THEN
      'GRANT OWNERSHIP ON PROCEDURE "'||DB||'"."'||SCH||'"."'||NAME||'"'||ARG_TYPES||
      ' TO ROLE '||TARGET_ROLE||' COPY CURRENT GRANTS'
    ELSE
      'GRANT OWNERSHIP ON TASK "'||DB||'"."'||SCH||'"."'||NAME||'"'||
      ' TO ROLE '||TARGET_ROLE||' COPY CURRENT GRANTS'
  END AS STMT
FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
WHERE TARGET_ROLE NOT IN ('EXCLUDE')
ORDER BY TARGET_ROLE, OBJ_TYPE, DB, SCH, NAME;

-- ---------------------------------------------------------------------
-- 6. MIGRATE  (logged, per-object error handling, task-safe)
--    Recommended: pilot one role first by adding AND TARGET_ROLE = '<role>'
--    to the three loop queries.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS MIGRATION_LOG (
  TS TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP, OBJ_TYPE VARCHAR, FQN VARCHAR,
  OLD_OWNER VARCHAR, NEW_OWNER VARCHAR, STATUS VARCHAR, ERR VARCHAR);

EXECUTE IMMEDIATE $$
DECLARE
  fqn VARCHAR;
BEGIN
  -- 6a. Procedures
  FOR p IN (SELECT * FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
            WHERE OBJ_TYPE='PROCEDURE' AND TARGET_ROLE <> 'EXCLUDE') DO
    fqn := '"'||p.DB||'"."'||p.SCH||'"."'||p.NAME||'"'||p.ARG_TYPES;
    BEGIN
      EXECUTE IMMEDIATE 'GRANT OWNERSHIP ON PROCEDURE '||fqn||' TO ROLE '||p.TARGET_ROLE||' COPY CURRENT GRANTS';
      INSERT INTO GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG (OBJ_TYPE,FQN,OLD_OWNER,NEW_OWNER,STATUS)
        VALUES ('PROCEDURE', :fqn, :p.OWNER, :p.TARGET_ROLE, 'OK');
    EXCEPTION WHEN OTHER THEN
      INSERT INTO GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG (OBJ_TYPE,FQN,OLD_OWNER,NEW_OWNER,STATUS,ERR)
        VALUES ('PROCEDURE', :fqn, :p.OWNER, :p.TARGET_ROLE, 'FAILED', :SQLERRM);
    END;
  END FOR;

  -- 6b. Tasks: suspend (roots first) -> transfer -> resume (children first, roots last)
  FOR t IN (SELECT * FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
            WHERE OBJ_TYPE='TASK' AND TARGET_ROLE <> 'EXCLUDE' AND TASK_STATE='started'
            ORDER BY IS_ROOT DESC) DO
    fqn := '"'||t.DB||'"."'||t.SCH||'"."'||t.NAME||'"';
    BEGIN EXECUTE IMMEDIATE 'ALTER TASK '||fqn||' SUSPEND'; EXCEPTION WHEN OTHER THEN NULL; END;
  END FOR;

  FOR t IN (SELECT * FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
            WHERE OBJ_TYPE='TASK' AND TARGET_ROLE <> 'EXCLUDE') DO
    fqn := '"'||t.DB||'"."'||t.SCH||'"."'||t.NAME||'"';
    BEGIN
      EXECUTE IMMEDIATE 'GRANT OWNERSHIP ON TASK '||fqn||' TO ROLE '||t.TARGET_ROLE||' COPY CURRENT GRANTS';
      INSERT INTO GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG (OBJ_TYPE,FQN,OLD_OWNER,NEW_OWNER,STATUS)
        VALUES ('TASK', :fqn, :t.OWNER, :t.TARGET_ROLE, 'OK');
    EXCEPTION WHEN OTHER THEN
      INSERT INTO GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG (OBJ_TYPE,FQN,OLD_OWNER,NEW_OWNER,STATUS,ERR)
        VALUES ('TASK', :fqn, :t.OWNER, :t.TARGET_ROLE, 'FAILED', :SQLERRM);
    END;
  END FOR;

  -- Resume only tasks that were running before; children first, roots last
  FOR t IN (SELECT * FROM GOVERNANCE_DB.ROLE_MIGRATION.RESOLVED
            WHERE OBJ_TYPE='TASK' AND TARGET_ROLE <> 'EXCLUDE' AND TASK_STATE='started'
            ORDER BY IS_ROOT ASC) DO
    fqn := '"'||t.DB||'"."'||t.SCH||'"."'||t.NAME||'"';
    BEGIN
      -- Resume must run as the new owner (or a role holding OPERATE on the task)
      EXECUTE IMMEDIATE 'GRANT OPERATE ON TASK '||fqn||' TO ROLE ACCOUNTADMIN';
      EXECUTE IMMEDIATE 'ALTER TASK '||fqn||' RESUME';
    EXCEPTION WHEN OTHER THEN
      INSERT INTO GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG (OBJ_TYPE,FQN,OLD_OWNER,NEW_OWNER,STATUS,ERR)
        VALUES ('TASK_RESUME', :fqn, :t.OWNER, :t.TARGET_ROLE, 'FAILED', :SQLERRM);
    END;
  END FOR;
  RETURN 'done - review MIGRATION_LOG';
END;
$$;

SELECT * FROM MIGRATION_LOG WHERE STATUS <> 'OK' ORDER BY TS DESC;   -- fix privileges (sec. 4), re-run sec. 2 + 6

-- ---------------------------------------------------------------------
-- 7. HIGH-RISK / SPECIAL HANDLING  (do not blindly migrate)
-- ---------------------------------------------------------------------
-- a) GRANT-issuing procs: GRANT_CORP_PARTNERSHIPS_ANALYST_ACCESS, GRANT_TABLEAU_READER_ACCESS,
--    SP_GRANT_AIRBYTE_ACCESS, SYNC_ONETRUST_SCAN_GRANTS.
--    They need MANAGE GRANTS or ownership of the target objects. MANAGE GRANTS is itself an
--    escalation path (similar to SECURITYADMIN). Preferred: make the grantee-object owner role
--    own the proc, or scope with future grants / database roles. If MANAGE GRANTS is unavoidable,
--    give it to ONE dedicated role (PROC_OWNER_GOV_GRANTS), no human users, alert on its usage.
-- b) Habu clean room (HABU_CLEAN_ROOM_COMMON, ~45 procs: CREATE_NEW_WAREHOUSE, shares, INIT_FRAMEWORK,
--    stream tasks). Installed/driven by Habu (LiveRamp); it needs CREATE WAREHOUSE, CREATE/IMPORT SHARE,
--    CREATE DATABASE. Ask the vendor for a documented least-privilege role; otherwise document a
--    risk-accepted exception in Trust Center rather than breaking the clean room.
-- c) SAMOOHA_BY_SNOWFLAKE_LOCAL_DB: Snowflake-managed; excluded. Exception only.
-- d) DSAR / DELETE procs (DSAR_DATA_DELETION, DSAR_REDACT_BY_EMAIL, DSAR_REMOVAL, DROP_*): keep in
--    PROC_OWNER_PRIVACY; grant DELETE/UPDATE only on the target PII tables; log via ACCESS_HISTORY.
-- e) S3 unloads (UNLOAD_DATA_TO_S3*): USAGE on the storage integration only; owner role must not
--    be able to ALTER it. Dated copies (…_AUG_06_2025) look like cleanup candidates.
-- f) Cleanup candidates: *_ORIGINAL, *_V2 duplicates, TEST_*, *_DOB_TEST, LOAD_NEW_FILES_TEST,
--    PGAT.GR_TESTING / PGAT_UAT copies. Dropping dead procs shrinks this finding faster than migrating.
-- g) AUTO_TAG_CLASSIFICATION: needs SNOWFLAKE.CLASSIFICATION_ADMIN (database role) + APPLY TAG:
--    GRANT DATABASE ROLE SNOWFLAKE.CLASSIFICATION_ADMIN TO ROLE PROC_OWNER_PRIVACY;
--    GRANT APPLY TAG ON ACCOUNT TO ROLE PROC_OWNER_PRIVACY;

-- ---------------------------------------------------------------------
-- 8. VERIFY
-- ---------------------------------------------------------------------
-- Anything left under risky owners (procs, via ACCOUNT_USAGE after lag; tasks live):
SELECT PROCEDURE_CATALOG||'.'||PROCEDURE_SCHEMA||'.'||PROCEDURE_NAME AS PROC, PROCEDURE_OWNER
FROM SNOWFLAKE.ACCOUNT_USAGE.PROCEDURES
WHERE DELETED IS NULL AND PROCEDURE_OWNER IN ('ACCOUNTADMIN','SECURITYADMIN');

SHOW TASKS IN ACCOUNT;
SELECT "database_name","schema_name","name","owner","state"
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "owner" IN ('ACCOUNTADMIN','SECURITYADMIN');

-- Then: watch TASK_HISTORY / QUERY_HISTORY for failures (privilege errors) for 1-2 cycles, and
-- re-run the Trust Center scanner (Snowsight > Governance & security > Trust Center).
-- Also stop recurrence: have deploy pipelines/humans use SYSADMIN-descended roles, never ACCOUNTADMIN.

-- ---------------------------------------------------------------------
-- 9. ROLLBACK (per object, from the log)
-- ---------------------------------------------------------------------
-- SELECT 'GRANT OWNERSHIP ON '||OBJ_TYPE||' '||FQN||' TO ROLE '||OLD_OWNER||' COPY CURRENT GRANTS;'
-- FROM GOVERNANCE_DB.ROLE_MIGRATION.MIGRATION_LOG WHERE STATUS='OK' AND OBJ_TYPE IN ('PROCEDURE','TASK');
