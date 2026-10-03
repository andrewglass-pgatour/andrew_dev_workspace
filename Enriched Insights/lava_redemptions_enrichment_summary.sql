{{ config(
    materialized='table',
    tags=['source:lava', 'layer:analytics'],
    docs={'node_color': '#FF6700'},
    meta={'owner': 'DTS', 'contains_pii': true}
) }}

with lava_base as (
    select 
        first_name,
        last_name,
        lower(trim(email)) as email,
        abs(amount_redeemed) as amount_redeemed,
        date,
        coalesce(nullif(trim(reward), ''), 'Unknown Reward') as reward,
        coalesce(nullif(trim(reward_type), ''), 'Unknown Reward Type') as reward_type,
        coalesce(nullif(trim(source), ''), 'Unknown Source') as source,
        case when email is not null and trim(email) <> '' and email ilike '%@%' then 1 else 0 end as is_valid_email
    from {{ source('lava', 'lava_redemptions_as_of_20260903') if adapter.already_exists('lava', 'lava_redemptions_as_of_20260903') else 'PGAT.LAVA.LAVA_REDEMPTIONS_AS_OF_20260903' }}
    where email is not null and trim(email) <> ''
),

lava_personids as (
    select 
        l.*,
        g.personid
    from lava_base l
    left join {{ ref('golden_account_dedup_email') }} g
        on (l.is_valid_email = 1 and l.email = lower(trim(g.email)))
),

enriched as (
    select 
        l.email,
        l.reward,
        l.reward_type,
        l.source,
        l.amount_redeemed,
        l.is_valid_email,
        l.personid,
        coalesce(fan.age, enr.age) as age,
        enr.gender,
        enr.marital_status,
        enr.children_hh,
        enr.home_owner,
        enr.income_hh,
        enr.credit_range,
        enr.occupation_category
    from lava_personids l
    left join {{ ref('mops_golden_fan_master') }} fan 
        on (l.personid is not null and l.personid <> '' and l.personid = fan.personid)
    left join {{ ref('us_full_golden_record_enriched_enr') }} enr 
        on (l.personid is not null and l.personid <> '' and l.personid = enr.cid)
)

-- Overall Total Breakdown
select 
    'OVERALL' as breakdown_category,
    'All Lava Redeemers' as category_value,
    count(*) as total_redemptions,
    round(sum(amount_redeemed), 2) as total_amount_redeemed_usd,
    count(distinct email) as total_unique_emails,
    count(distinct case when is_valid_email = 1 then email end) as valid_email_redeemers,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    round(count(distinct case when personid is not null and personid <> '' then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as golden_match_rate_pct,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as enriched_match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional
from enriched

union all

-- Non-Volunteer Total Breakdown (Filtering out rewards containing 'volunteer')
select 
    'NON_VOLUNTEER' as breakdown_category,
    'Non-Volunteer Redeemers' as category_value,
    count(*) as total_redemptions,
    round(sum(amount_redeemed), 2) as total_amount_redeemed_usd,
    count(distinct email) as total_unique_emails,
    count(distinct case when is_valid_email = 1 then email end) as valid_email_redeemers,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    round(count(distinct case when personid is not null and personid <> '' then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as golden_match_rate_pct,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as enriched_match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional
from enriched
where reward not ilike '%volunteer%'

union all

-- By Reward Type Breakdown
select 
    'REWARD_TYPE' as breakdown_category,
    reward_type as category_value,
    count(*) as total_redemptions,
    round(sum(amount_redeemed), 2) as total_amount_redeemed_usd,
    count(distinct email) as total_unique_emails,
    count(distinct case when is_valid_email = 1 then email end) as valid_email_redeemers,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    round(count(distinct case when personid is not null and personid <> '' then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as golden_match_rate_pct,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as enriched_match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional
from enriched
group by 1, 2

union all

-- By Source Breakdown
select 
    'SOURCE' as breakdown_category,
    source as category_value,
    count(*) as total_redemptions,
    round(sum(amount_redeemed), 2) as total_amount_redeemed_usd,
    count(distinct email) as total_unique_emails,
    count(distinct case when is_valid_email = 1 then email end) as valid_email_redeemers,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    round(count(distinct case when personid is not null and personid <> '' then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as golden_match_rate_pct,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as enriched_match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional
from enriched
group by 1, 2

union all

-- By Reward Breakdown
select 
    'REWARD' as breakdown_category,
    reward as category_value,
    count(*) as total_redemptions,
    round(sum(amount_redeemed), 2) as total_amount_redeemed_usd,
    count(distinct email) as total_unique_emails,
    count(distinct case when is_valid_email = 1 then email end) as valid_email_redeemers,
    count(distinct case when personid is not null and personid <> '' then personid end) as matched_golden_record_members,
    round(count(distinct case when personid is not null and personid <> '' then personid end) / nullif(count(distinct case when is_valid_email = 1 then email end), 0) * 100, 2) as golden_match_rate_pct,
    count(distinct case when age is not null then personid end) as enriched_members,
    round(count(distinct case when age is not null then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as enriched_match_rate_pct,
    round(avg(age), 2) as avg_age,
    median(age) as median_age,
    count(distinct case when age between 18 and 35 then personid end) as count_18_35,
    round(count(distinct case when age between 18 and 35 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_18_35,
    round(count(distinct case when age between 13 and 34 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_35,
    round(count(distinct case when age between 13 and 44 then personid end) / nullif(count(distinct case when age is not null then personid end), 0) * 100, 2) as pct_under_45,
    round(count(distinct case when gender in ('F', 'Female', 'FEMALE') then personid end) / nullif(count(distinct case when gender is not null and gender <> '' then personid end), 0) * 100, 2) as pct_female,
    round(count(distinct case when children_hh > 0 then personid end) / nullif(count(distinct case when children_hh is not null then personid end), 0) * 100, 2) as pct_with_children,
    round(count(distinct case when marital_status ilike '%married%' then personid end) / nullif(count(distinct case when marital_status is not null then personid end), 0) * 100, 2) as pct_married,
    round(count(distinct case when home_owner ilike '%owner%' then personid end) / nullif(count(distinct case when home_owner is not null then personid end), 0) * 100, 2) as pct_homeowner,
    round(count(distinct case when income_hh ilike '%100%' or income_hh ilike '%150%' or income_hh ilike '%175%' or income_hh ilike '%200%' or income_hh ilike '%250%' or income_hh ilike '%300%' then personid end) / nullif(count(distinct case when income_hh is not null and income_hh <> '' and income_hh <> 'Unknown' then personid end), 0) * 100, 2) as pct_income_100k_plus,
    round(count(distinct case when credit_range ilike 'A.%' or credit_range ilike 'B.%' or credit_range ilike 'C.%' then personid end) / nullif(count(distinct case when credit_range is not null and credit_range <> '' and credit_range <> 'Unknown' then personid end), 0) * 100, 2) as pct_credit_700_plus,
    round(count(distinct case when occupation_category ilike '%Professional%' or occupation_category ilike '%Management%' or occupation_category ilike '%White Collar%' then personid end) / nullif(count(distinct case when occupation_category is not null and occupation_category <> '' and occupation_category <> 'Unknown' then personid end), 0) * 100, 2) as pct_management_professional
from enriched
group by 1, 2
