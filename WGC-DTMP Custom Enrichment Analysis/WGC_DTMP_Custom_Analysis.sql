-- WGC Dell Match Play Championships - Enriched Data pull 
SELECT SEASONNAME, SEASONYEAR, COUNT(*) FROM ANALYTICS.PROD_ARCHTICS.ARCHTICS_TICKETS
WHERE SEASONNAME ILIKE '%Dell%'
GROUP BY 1,2 
ORDER BY 1,2;

SELECT DISTINCT SEASONNAME FROM ANALYTICS.PROD_ARCHTICS.ARCHTICS_TICKETS ORDER BY 1;

/* 2019 Dell Technologies Match Play	2019	100203
2020 Dell Technologies Match Play	2020	53538
2021 Dell Technologies Match Play	2021	60764
2022 Dell Technologies Match Play	2022	120034
2023 Dell Technologies Match Play	2023	124388 */ 

CREATE OR REPLACE TEMPORARY TABLE PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW AS
SELECT * 
FROM ANALYTICS.PROD_ARCHTICS.ARCHTICS_TICKETS
WHERE SEASONNAME ILIKE '%DELL%MATCH%PLAY%';

SELECT * FROM PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW;

/* -------------------------------------------------------------------------
   1) CREATE PS TABLE WITH ENRICHED DEMOGRAPHICS + GEOGRAPHY + TOURNAMENT
------------------------------------------------------------------------- */
CREATE OR REPLACE TEMPORARY TABLE PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW_PS AS (
    select 
        fm.personid, 
        fm.email1,
        x.seasonname as tournament_name, -- Replace with exact tournament column from x if different (e.g., x.event_name)
        
        -- Age: Prioritize Golden Record age over Audience Acuity enrichment age
        coalesce(fm.age, aa_enr.age) as Age,
        
        -- Geography Demographics from MOPS_GOLDEN_FAN_MASTER
        fm.state as State,
        fm.country as Country,
        fm.city as City,
        fm.zip as Zip,
        fm.dma_name as DMA_Name,

        -- Audience Acuity Enrichment Attributes
        aa_enr.gender as AA_Gender,
        aa_enr.marital_status as AA_Marital_Status,
        aa_enr.children_hh as AA_HH_Children,
        aa_enr.home_owner as AA_Home_Owner,
        aa_enr.income_hh as AA_HH_Income,
        aa_enr.net_worth_hh as AA_HH_Net_Worth,
        aa_enr.credit_range as AA_Credit_Range,
        aa_enr.occupation_category as AA_Occupation_Category
    from PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW x
    left join PGAT.ARCHTICS.CUST c 
        on x.accountid = c.acct_id 
        and x.databaseid = c.database_id
        and c.primary_code = 'Primary'
        and c.main_acct_id_ind = 'Y'
    left join pgat.golden.fansource fs 
        on concat(c.cust_name_id, '-', c.name_type) = fs.sourceid 
        and fs.source = 'archtics'
    left join analytics.prod_golden.mops_golden_fan_master fm 
        on fs.personid = fm.personid 
    left join pgat.audience_acuity.us_full_golden_record_enriched_enr as aa_enr 
        on fm.personid = aa_enr.cid
);


/* -------------------------------------------------------------------------
   2) OVERALL AND PER-TOURNAMENT DISTRIBUTION (DEMOGRAPHICS + GEOGRAPHY)
------------------------------------------------------------------------- */
CREATE OR REPLACE TEMPORARY TABLE PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW_DISTRIBUTION AS (
with base as (
    select *,
        case
            when AGE between 18 and 24 then '18-24'
            when AGE between 25 and 34 then '25-34'
            when AGE between 35 and 44 then '35-44'
            when AGE between 45 and 54 then '45-54'
            when AGE between 55 and 64 then '55-64'
            when AGE >= 65 then '65+'
        end as AGE_RANGE
    from PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW_PS
),

/* ----------------------------------------
   3) DEMOGRAPHIC & GEOGRAPHIC UNPIVOT
----------------------------------------- */
demographic_unpivot as (
    -- Age & Geography
    select personid, tournament_name, 'Age_Range' as attribute, AGE_RANGE::varchar as value from base
    union all select personid, tournament_name, 'State', State::varchar from base
    union all select personid, tournament_name, 'DMA_Name', DMA_Name::varchar from base
    
    -- Core Enrichment Values
    union all select personid, tournament_name, 'AA_Gender', AA_GENDER::varchar from base
    union all select personid, tournament_name, 'AA_Marital_Status', AA_MARITAL_STATUS::varchar from base
    union all select personid, tournament_name, 'AA_Children_HH', AA_HH_CHILDREN::varchar from base
    union all select personid, tournament_name, 'AA_Home_Owner', AA_HOME_OWNER::varchar from base
    union all select personid, tournament_name, 'AA_Income_HH', AA_HH_INCOME::varchar from base
    union all select personid, tournament_name, 'AA_Net_Worth_HH', AA_HH_NET_WORTH::varchar from base
    union all select personid, tournament_name, 'AA_Credit_Range', AA_CREDIT_RANGE::varchar from base
    union all select personid, tournament_name, 'AA_Occupation_Category', AA_OCCUPATION_CATEGORY::varchar from base
),

/* ----------------------------------------
   4) OVERALL COUNTS & DISTRIBUTION (All Tournaments Combined)
----------------------------------------- */
demographic_totals_overall as (
    select 
        attribute, 
        count(*) as denom
    from demographic_unpivot
    where value is not null and value <> ''
    group by attribute
),

demographic_counts_overall as (
    select
        'Demographic' as Metric_Type,
        d.attribute as Attribute,
        d.value as Field_Value,
        count(*) as Field_Records,
        t.denom as Attribute_Total,
        count(*) / t.denom::float as Field_Distribution,
        'Overall' as Source_Type
    from demographic_unpivot d
    join demographic_totals_overall t 
        on d.attribute = t.attribute
    where d.value is not null and d.value <> ''
    group by 1, 2, 3, 5
),

/* ----------------------------------------
   5) TOURNAMENT BREAKOUT COUNTS & DISTRIBUTION
----------------------------------------- */
demographic_counts_by_tournament as (
    select
        'Demographic' as Metric_Type,
        d.attribute,
        d.value as field_value,
        d.tournament_name as source_type,
        count(*) as field_records
    from demographic_unpivot d
    where d.value is not null and d.value <> ''
      and d.tournament_name is not null
    group by 1, 2, 3, 4
),

demographic_tournament_totals as (
    select
        d.attribute,
        d.tournament_name as source_type,
        count(*) as attribute_total
    from demographic_unpivot d
    where d.value is not null and d.value <> ''
      and d.tournament_name is not null
    group by 1, 2
),

final_demographic_tournament_metrics as (
    select
        d.Metric_Type,
        d.attribute as Attribute,
        d.field_value as Field_Value,
        d.field_records as Field_Records,
        t.attribute_total as Attribute_Total,
        d.field_records / t.attribute_total::float as Field_Distribution,
        d.source_type as Source_Type
    from demographic_counts_by_tournament d
    join demographic_tournament_totals t 
        on d.attribute = t.attribute
       and d.source_type = t.source_type
)

/* ----------------------------------------
   6) COMBINED FINAL OUTPUT
----------------------------------------- */
select
    Metric_Type,
    Attribute,
    Field_Value,
    Field_Records,
    Attribute_Total,
    Field_Distribution,
    Source_Type
from demographic_counts_overall

union all

select
    Metric_Type,
    Attribute,
    Field_Value,
    Field_Records,
    Attribute_Total,
    Field_Distribution,
    Source_Type
from final_demographic_tournament_metrics
);

SELECT * FROM PGAT.ARCHTICS.WGC_DELL_MP_ENRICHMENT_OVERVIEW_DISTRIBUTION ORDER BY SOURCE_TYPE, ATTRIBUTE, FIELD_VALUE;