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
