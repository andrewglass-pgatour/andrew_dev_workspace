{{ config(materialized='table') }}

with base as (
    select *,
        case
            when AA_AGE between 18 and 24 then '18-24'
            when AA_AGE between 25 and 34 then '25-34'
            when AA_AGE between 35 and 44 then '35-44'
            when AA_AGE between 45 and 54 then '45-54'
            when AA_AGE between 55 and 64 then '55-64'
            when AA_AGE >= 65 then '65+'
        end as AGE_RANGE
    from {{ ref('unified_fan_profile') }}
),

/* ----------------------------------------
   1) DEMOGRAPHIC UNPIVOT (same as before)
----------------------------------------- */
demographic_unpivot as (
    select personid, 'AA_Age_Range' as attribute, AGE_RANGE::varchar as value from base
    union all select personid, 'AA_Gender', AA_GENDER::varchar from base
    union all select personid, 'AA_Marital_Status', AA_MARITAL_STATUS::varchar from base
    union all select personid, 'AA_Children_HH', AA_HH_CHILDREN::varchar from base
    union all select personid, 'AA_Home_Owner', AA_HOME_OWNER::varchar from base
    union all select personid, 'AA_Income_HH', AA_HH_INCOME::varchar from base
    union all select personid, 'AA_Net_Worth_HH', AA_HH_NET_WORTH::varchar from base
    union all select personid, 'AA_Credit_Range', AA_CREDIT_RANGE::varchar from base
    union all select personid, 'AA_Occupation_Category', AA_OCCUPATION_CATEGORY::varchar from base
),

/* ----------------------------------------
   2) OVERALL DEMOGRAPHIC COUNTS (existing)
----------------------------------------- */
demographic_totals as (
    select attribute, count(*) as denom
    from demographic_unpivot
    where value is not null and value <> ''
    group by attribute
),

demographic_counts as (
    select
        'Demographic' as Metric_Type,
        d.attribute as Attribute,
        d.value as Field_Value,
        count(*) as Field_Records,
        t.denom as Attribute_Total,
        count(*) / t.denom::float as Field_Distribution,
        null::varchar as Source_Type
    from demographic_unpivot d
    join demographic_totals t on d.attribute = t.attribute
    where d.value is not null and d.value <> ''
    group by 1,2,3,5
),

/* ----------------------------------------
   3) FIRST-PARTY SOURCE UNPIVOT
----------------------------------------- */
first_party_sources as (
    select personid, 'Fan Council Members' as source_type, Fan_Council_Member as source_flag from base
    union all select personid, 'PartnerOffers Subscribers' as source_type, Partner_Offers_Subscriber as source_flag from base
    union all select personid, 'Wire2Wire Subscribers', Wire_to_Wire_Subscriber as source_flag from base
    union all select personid, 'VIP Volunteer Subscribers', VIP_Volunteer_Subscriber from base
    union all select personid, 'The Early Card Subscribers', The_Early_Card_Subscriber from base
    union all select personid, 'Champions Minute Monthly Subscribers', Champions_Monthly_Minute_Subscriber from base
    union all select personid, 'Signature Scroll Subscribers', Signature_Scroll_Subscriber from base
    union all select personid, 'Fanatics Buyers', PGA_TOUR_Fan_Shop_Buyer from base
    union all select personid, 'Current Season Fantasy Players', Current_Season_Fantasy_Player from base
    union all select personid, 'TOUR Pass Member', TOUR_Pass_Member from base
    union all select personid, 'Event Attendees', Archtics_Attendee from base
    union all select personid, 'EA PGA TOUR Players', EA_PGA_TOUR_Player from base
    --union all select personid, 'Holiday Sweeps 2025 Campaign', Holiday_Sweeps_2025_Campaign from base
    --union all select personid, 'EA Sweeps 2025 Campaign', EA_Sweeps_2025_Campaign from base
    --union all select personid, 'EventAttendee', iff(Total_Tickets > 0, true, false) from base
),

valid_sources as (
    select *
    from first_party_sources
    where source_flag = true
),

/* ----------------------------------------
   4) DEMOGRAPHIC COUNTS BY SOURCE
----------------------------------------- */
demographic_by_source as (
    select
        'Demographic' as Metric_Type,
        d.attribute,
        d.value as field_value,
        s.source_type,
        count(*) as field_records
    from demographic_unpivot d
    join valid_sources s on d.personid = s.personid
    where d.value is not null and d.value <> ''
    group by 1,2,3,4
),

demographic_source_totals as (
    select
        d.attribute,
        s.source_type,
        count(*) as attribute_total
    from demographic_unpivot d
    join valid_sources s on d.personid = s.personid
    where d.value is not null and d.value <> ''
    group by 1,2
),

final_demographic_source_metrics as (
    select
        d.Metric_Type,
        d.attribute,
        d.field_value,
        d.source_type,
        d.field_records,
        t.attribute_total,
        d.field_records / t.attribute_total::float as field_distribution,
    from demographic_by_source d
    join demographic_source_totals t 
        on d.attribute = t.attribute
        and d.source_type = t.source_type
)

/* ----------------------------------------
   5) FINAL OUTPUT
----------------------------------------- */

select
    Metric_Type,
    Attribute,
    Field_Value,
    Field_Records,
    Attribute_Total,
    Field_Distribution,
    Source_Type
from demographic_counts

union all

select
    Metric_Type,
    attribute,
    field_value,
    field_records,
    attribute_total,
    field_distribution,
    source_type
from final_demographic_source_metrics

