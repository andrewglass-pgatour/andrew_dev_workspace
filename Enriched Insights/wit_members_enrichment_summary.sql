{{ config(
    materialized='table',
    tags=['source:wit', 'layer:analytics'],
    docs={'node_color': '#FF6700'},
    meta={'owner': 'DTS', 'contains_pii': true}
) }}

with wit_members as (
    select distinct 
        personid, 
        email
    from {{ ref('wit_user_summary') }}
    where email is not null and email <> ''
),

enriched as (
    select 
        w.personid,
        w.email,
        coalesce(fan.age, enr.age) as age,
        enr.gender,
        enr.marital_status,
        enr.children_hh,
        enr.home_owner,
        enr.income_hh,
        enr.net_worth_hh,
        enr.credit_range,
        enr.occupation_category
    from wit_members w
    left join {{ ref('mops_golden_fan_master') }} fan 
        on (w.personid is not null and w.personid <> '' and w.personid = fan.personid)
    left join {{ ref('us_full_golden_record_enriched_enr') }} enr 
        on (w.personid is not null and w.personid <> '' and w.personid = enr.cid)
)

select 
    count(distinct email) as total_participants,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct email), 0) * 100, 2) as match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,

    -- Age Group Counts & Percentages
    count(distinct case when age between 13 and 17 then personid end) as age_13_17,
    round(count(distinct case when age between 13 and 17 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_13_17,
    count(distinct case when age between 18 and 24 then personid end) as age_18_24,
    round(count(distinct case when age between 18 and 24 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_24,
    count(distinct case when age between 25 and 34 then personid end) as age_25_34,
    round(count(distinct case when age between 25 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_25_34,
    count(distinct case when age between 35 and 44 then personid end) as age_35_44,
    round(count(distinct case when age between 35 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_35_44,
    count(distinct case when age between 45 and 54 then personid end) as age_45_54,
    round(count(distinct case when age between 45 and 54 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_45_54,
    count(distinct case when age between 55 and 64 then personid end) as age_55_64,
    round(count(distinct case when age between 55 and 64 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_55_64,
    count(distinct case when age >= 65 then personid end) as age_65_plus,
    round(count(distinct case when age >= 65 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_65_plus,

    -- Key Demographic Aggregations
    count(distinct case when age between 13 and 34 then personid end) as count_under_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    count(distinct case when age between 13 and 44 then personid end) as count_under_45,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,

    -- Gender Mix
    count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) as female_count,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,

    -- Family, Marital, Homeowner Signals
    count(distinct case when children_hh > 0 then personid end) as count_with_children,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    count(distinct case when marital_status ilike '%married%' then personid end) as married_cnt,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    count(distinct case when home_owner ilike '%owner%' then personid end) as homeowner_cnt,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,

    -- Household Income Highlights ($100k+)
    count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) as count_income_100k_plus,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,

    -- Credit Range Highlights (700+)
    count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) as count_credit_700_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,

    -- Occupation Category Highlights (Management & Professional)
    count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) as count_management_professional,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional

from enriched
