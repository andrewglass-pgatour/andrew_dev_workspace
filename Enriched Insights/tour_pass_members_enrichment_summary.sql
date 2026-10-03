with gigya_enrichment_summary as (
    select
        m.personid,
        m.uid as gigyaid,
        m.email,
        m.lastlogin as gigya_last_login,
        m.created as gigya_created,
        aa_enr.cid as aa_enr_cid,
        aa_enr.age as aa_age,
        aa_enr.gender as aa_gender,
        aa_enr.marital_status as aa_marital_status,
        aa_enr.children_hh as aa_hh_children,
        aa_enr.home_owner as aa_home_owner,
        aa_enr.income_hh as aa_hh_income,
        aa_enr.net_worth_hh as aa_hh_net_worth,
        aa_enr.credit_range as aa_credit_range,
        aa_enr.occupation_category as aa_occupation_category
    from {{ ref('int_account_and_email_account') }} m
    left join {{ ref('us_full_golden_record_enriched_enr') }} as aa_enr
        on m.personid = aa_enr.cid
    where m.uid is not null
),

base as (
    select
        *,
        case
            when aa_age between 18 and 24 then '18-24'
            when aa_age between 25 and 34 then '25-34'
            when aa_age between 35 and 44 then '35-44'
            when aa_age between 45 and 54 then '45-54'
            when aa_age between 55 and 64 then '55-64'
            when aa_age >= 65 then '65+'
        end as aa_age_range
    from gigya_enrichment_summary
),

demographic_unpivot as (
    select personid, 'AA_Age_Range' as attribute, aa_age_range::varchar as value from base
    union all select personid, 'AA_Gender', aa_gender::varchar from base
    union all select personid, 'AA_Marital_Status', aa_marital_status::varchar from base
    union all select personid, 'AA_Children_HH', aa_hh_children::varchar from base
    union all select personid, 'AA_Home_Owner', aa_home_owner::varchar from base
    union all select personid, 'AA_Income_HH', aa_hh_income::varchar from base
    union all select personid, 'AA_Net_Worth_HH', aa_hh_net_worth::varchar from base
    union all select personid, 'AA_Credit_Range', aa_credit_range::varchar from base
    union all select personid, 'AA_Occupation_Category', aa_occupation_category::varchar from base
),

demographic_totals as (
    select
        attribute,
        count(*) as attribute_total
    from demographic_unpivot
    where value is not null and value <> ''
    group by attribute
),

demographic_counts as (
    select
        'DEMOGRAPHIC' as metric_type,
        d.attribute as attribute,
        d.value as field_value,
        count(*) as field_records,
        t.attribute_total,
        count(*) / nullif(t.attribute_total, 0)::float as field_distribution
    from demographic_unpivot d
    join demographic_totals t
        on d.attribute = t.attribute
    where d.value is not null and d.value <> ''
    group by 1,2,3,5
)

select
    metric_type,
    attribute,
    field_value,
    field_records,
    attribute_total,
    field_distribution
from demographic_counts
order by
    attribute,
    field_records desc