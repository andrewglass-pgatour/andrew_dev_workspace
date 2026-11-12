-- Load cred_data_enriched_20261019.json -> pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test
-- Source: s3://pgatour-datalake-us-east-1-cred-investments/cred_data_enriched_20261019.json
-- File format: newline-delimited JSON, 22,644 rows, ~91 MB. companyId is NOT unique (397 repeated ids), so no primary key.

CREATE TABLE pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test (
    companyid                       VARCHAR(20),
    sourceid_a                      VARCHAR(30),
    source                          VARCHAR(20),
    name                            VARCHAR(500),
    financialhealthscore            DOUBLE PRECISION,
    sponsorshipdealscount           INTEGER,
    sportssponsorshipdealscount     INTEGER,
    numberofemployees               INTEGER,
    salesteamsize                   INTEGER,
    marketingteamsize               INTEGER,
    salesteamproportion             DOUBLE PRECISION,
    marketingteamproportion         DOUBLE PRECISION,
    hasexecutivegolfinterest        BOOLEAN,
    employees_per_city              SUPER,            -- array of {city, value}; up to ~430 KB per row, too big for VARCHAR(65535)
    topmarkets                      VARCHAR(max),
    demographyfit                   DOUBLE PRECISION,
    ciq_id                          VARCHAR(30),
    golfsponsorshipdealscount       INTEGER,
    currentlysponsorsgolf           BOOLEAN,
    overallfit                      DOUBLE PRECISION,
    executivescount                 INTEGER,
    executivesgolfinterestcount     INTEGER,
    employeesperoffice              VARCHAR(max),
    hqlocation                      VARCHAR(500),
    hasregionaloffices              BOOLEAN,
    regionaloffices                 VARCHAR(max)
);

-- Role RedshiftS3 is associated with the cluster/workgroup. If COPY returns access denied, the role lacks read on the bucket.
-- Redshift JSON 'auto ignorecase' matches keys case-insensitively (camelCase keys -> lowercase columns).
-- SUPER column needs 'auto ignorecase' or a jsonpaths file; objects/arrays load as SUPER automatically.
COPY pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test
FROM 's3://pgatour-datalake-us-east-1-cred-investments/cred_data_enriched_20261019.json'
IAM_ROLE 'arn:aws:iam::746763610437:role/RedshiftS3'
FORMAT AS JSON 'auto ignorecase'
REGION 'us-east-1'
TRUNCATECOLUMNS
TIMEFORMAT 'auto';

-- Validation (expect 22644 rows)
SELECT COUNT(*) AS row_count
FROM pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test;
-- 22,644 rows

SELECT top 100 *
FROM pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test;

-- Check for load errors if COPY fails
-- SELECT * FROM stl_load_errors ORDER BY starttime DESC LIMIT 20;


/* Insert new file into old table... */
-- Insert pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test (one column per field)
-- into pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2 (json_data, etl_proc_date).
--
-- Format matched to the old table:
--   * json_data = one JSON object per row; NULL fields are omitted (old rows never contain "key":null)
--   * count / size / financialHealthScore fields are JSON strings ("13"); proportions, fit scores are JSON numbers; booleans are true/false
--   * keys keep the old camelCase / snake_case names (topMarkets, hasExecutiveGolfInterest, ciq_id, ...)
--   * employees_per_city is a JSON array, [] when null
--   * etl_proc_date = load timestamp
 
-- 1) Preview first (no insert):
-- SELECT json_data, etl_proc_date FROM ( <the SELECT below> ) LIMIT 5;
 
-- employees_per_city is capped to the first 200 cities (source is sorted by headcount, largest first).
-- Reason: serializing the whole SUPER array fails ("SUPER value exceeds export size") because 89 rows exceed the
-- 65,535-byte VARCHAR limit (largest is ~390 KB). The old table's largest json_data is ~12 KB / 212 cities.
-- Change "idx < 200" to adjust the cap.
INSERT INTO pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2 (json_data, etl_proc_date)
WITH src AS (
    SELECT t.*, ROW_NUMBER() OVER (ORDER BY companyid, sourceid_a) AS rn
    FROM pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test t
),
cities AS (
    SELECT s.rn,
           LISTAGG('{"city":' || JSON_SERIALIZE(c.city) || ',"value":' || JSON_SERIALIZE(c."value"), ',')
               WITHIN GROUP (ORDER BY idx) AS arr
    FROM src s, s.employees_per_city AS c AT idx
    WHERE idx < 200
    GROUP BY s.rn
)
SELECT
    '{' || SUBSTRING(frags, 2) || '}' AS json_data,
    GETDATE()                         AS etl_proc_date
FROM (
    SELECT
        -- strings
        CASE WHEN companyid  IS NULL THEN '' ELSE ',"companyId":'  || JSON_SERIALIZE(companyid::VARCHAR::SUPER)  END ||
        CASE WHEN sourceid_a IS NULL THEN '' ELSE ',"sourceid_a":' || JSON_SERIALIZE(sourceid_a::VARCHAR::SUPER) END ||
        CASE WHEN source     IS NULL THEN '' ELSE ',"source":'     || JSON_SERIALIZE(source::VARCHAR::SUPER)     END ||
        CASE WHEN name       IS NULL THEN '' ELSE ',"name":'       || JSON_SERIALIZE(name::VARCHAR::SUPER)       END ||
        -- numbers stored as JSON strings in the old table
        CASE WHEN financialhealthscore        IS NULL THEN '' ELSE ',"financialHealthScore":'        || JSON_SERIALIZE(financialhealthscore::VARCHAR::SUPER)        END ||
        CASE WHEN sponsorshipdealscount       IS NULL THEN '' ELSE ',"sponsorshipDealsCount":'       || JSON_SERIALIZE(sponsorshipdealscount::VARCHAR::SUPER)       END ||
        CASE WHEN sportssponsorshipdealscount IS NULL THEN '' ELSE ',"sportsSponsorshipDealsCount":' || JSON_SERIALIZE(sportssponsorshipdealscount::VARCHAR::SUPER) END ||
        CASE WHEN golfsponsorshipdealscount   IS NULL THEN '' ELSE ',"golfSponsorshipDealsCount":'   || JSON_SERIALIZE(golfsponsorshipdealscount::VARCHAR::SUPER)   END ||
        CASE WHEN numberofemployees           IS NULL THEN '' ELSE ',"numberOfEmployees":'           || JSON_SERIALIZE(numberofemployees::VARCHAR::SUPER)           END ||
        CASE WHEN salesteamsize               IS NULL THEN '' ELSE ',"salesTeamSize":'               || JSON_SERIALIZE(salesteamsize::VARCHAR::SUPER)               END ||
        CASE WHEN marketingteamsize           IS NULL THEN '' ELSE ',"marketingTeamSize":'           || JSON_SERIALIZE(marketingteamsize::VARCHAR::SUPER)           END ||
        CASE WHEN executivescount             IS NULL THEN '' ELSE ',"executivesCount":'             || JSON_SERIALIZE(executivescount::VARCHAR::SUPER)             END ||
        CASE WHEN executivesgolfinterestcount IS NULL THEN '' ELSE ',"executivesGolfInterestCount":' || JSON_SERIALIZE(executivesgolfinterestcount::VARCHAR::SUPER) END ||
        -- real JSON numbers
        CASE WHEN salesteamproportion     IS NULL THEN '' ELSE ',"salesTeamProportion":'     || salesteamproportion::VARCHAR     END ||
        CASE WHEN marketingteamproportion IS NULL THEN '' ELSE ',"marketingTeamProportion":' || marketingteamproportion::VARCHAR END ||
        CASE WHEN demographyfit           IS NULL THEN '' ELSE ',"demographyFit":'           || demographyfit::VARCHAR           END ||
        CASE WHEN overallfit              IS NULL THEN '' ELSE ',"overallFit":'              || overallfit::VARCHAR              END ||
        -- booleans
        CASE WHEN hasexecutivegolfinterest IS NULL THEN '' ELSE ',"hasExecutiveGolfInterest":' || CASE WHEN hasexecutivegolfinterest THEN 'true' ELSE 'false' END END ||
        CASE WHEN currentlysponsorsgolf    IS NULL THEN '' ELSE ',"currentlySponsorsGolf":'    || CASE WHEN currentlysponsorsgolf    THEN 'true' ELSE 'false' END END ||
        CASE WHEN hasregionaloffices       IS NULL THEN '' ELSE ',"hasRegionalOffices":'       || CASE WHEN hasregionaloffices       THEN 'true' ELSE 'false' END END ||
        -- more strings
        CASE WHEN ciq_id             IS NULL THEN '' ELSE ',"ciq_id":'            || JSON_SERIALIZE(ciq_id::VARCHAR::SUPER)             END ||
        CASE WHEN topmarkets         IS NULL THEN '' ELSE ',"topMarkets":'        || JSON_SERIALIZE(topmarkets::VARCHAR::SUPER)         END ||
        CASE WHEN employeesperoffice IS NULL THEN '' ELSE ',"employeesPerOffice":' || JSON_SERIALIZE(employeesperoffice::VARCHAR::SUPER) END ||
        CASE WHEN hqlocation         IS NULL THEN '' ELSE ',"hqLocation":'        || JSON_SERIALIZE(hqlocation::VARCHAR::SUPER)         END ||
        CASE WHEN regionaloffices    IS NULL THEN '' ELSE ',"regionalOffices":'   || JSON_SERIALIZE(regionaloffices::VARCHAR::SUPER)    END ||
        -- array (old table uses [] when empty)
        ',"employees_per_city":[' || COALESCE(ci.arr, '') || ']'
        AS frags
    FROM src
    LEFT JOIN cities ci ON ci.rn = src.rn
) x;
 
-- Verify
SELECT COUNT(*) FROM pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2_test; -- 22,644
select ETL_PROC_DATE, COUNT(*) from pgat_cp_prospecting_x.prospecting_database_consolidated_enriched_v2 group by 1 order by 1;