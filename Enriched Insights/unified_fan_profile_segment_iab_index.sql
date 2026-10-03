-- Step 1: Get Tournament Attendee segment
with unified_fan_profile as (
    select distinct personid
    from {{ ref('unified_fan_profile') }}
    where archtics_attendee = true
),

-- Step 2: Create base IAB table - tournament attendees who have ANY IAB behavior
segment_with_all_iab_behaviors as (
    select distinct 
        ufp.personid,
        ib.iab,
        beh_ref.iab_description
    from unified_fan_profile ufp
    inner join {{ source('audience_acuity', 'us_full_golden_record_enriched_idr') }} idr 
        on ufp.personid = idr.cid
    inner join {{ source('aa_sig_behaviors', 'aa_sig_behaviors') }} ib 
        on idr.aa_id = ib.id
    inner join {{ source('aa_sig_behaviors_ref', 'aa_sig_behaviors_ref')}} beh_ref 
        on ib.iab = beh_ref.iab
),

-- Step 3: Use all IAB categories from the base table (no filter - all eligible attributes)

-- Get total AA audience (all US users in Audience Acuity database)
total_aa_audience as (
    select count(distinct id) as total_aa_audience_count
    from {{ source('aa_sig_behaviors', 'aa_sig_behaviors') }}
),

-- Get all people with each IAB category in AA audience (all eligible attributes)
total_aa_audience_iab as (
    select 
        beh.iab,
        beh_ref.iab_description,
        count(distinct beh.id) as aa_audience_people_with_iab
    from {{ source('aa_sig_behaviors', 'aa_sig_behaviors') }} beh
    join {{ source('aa_sig_behaviors_ref', 'aa_sig_behaviors_ref')}} beh_ref 
        on beh.iab = beh_ref.iab
    group by beh.iab, beh_ref.iab_description
),

-- Calculate segment metrics for each IAB category
segment_iab_counts as (
    select 
        iab,
        iab_description,
        count(distinct personid) as segment_people_with_iab
    from segment_with_all_iab_behaviors
    group by iab, iab_description
),

-- Count tournament attendees who have ANY IAB behaviors (base denominator)
segment_counts as (
    select 
        count(distinct personid) as segment_count
    from segment_with_all_iab_behaviors
),

-- Calculate percentages and indexes
final as (
    select 
        'Tournament Attendees' as segment_name,
        taa_iab.iab,
        taa_iab.iab_description,
        -- Segment metrics
        coalesce(sic.segment_people_with_iab, 0) as segment_people_with_iab,
        sc.segment_count as total_segment_count,
        round(
            (coalesce(sic.segment_people_with_iab, 0)::float / nullif(sc.segment_count, 0)) * 100,
            2
        ) as segment_percentage,
        -- Total AA Audience comparison (US population baseline)
        taa_iab.aa_audience_people_with_iab,
        taa.total_aa_audience_count,
        round(
            (taa_iab.aa_audience_people_with_iab::float / nullif(taa.total_aa_audience_count, 0)) * 100,
            2
        ) as aa_audience_percentage,
        round(
            (
                (coalesce(sic.segment_people_with_iab, 0)::float / nullif(sc.segment_count, 0)) /
                nullif((taa_iab.aa_audience_people_with_iab::float / nullif(taa.total_aa_audience_count, 0)), 0)
            ) * 100,
            2
        ) as index_vs_aa_audience
    from total_aa_audience_iab taa_iab
    left join segment_iab_counts sic on taa_iab.iab = sic.iab
    cross join segment_counts sc
    cross join total_aa_audience taa
)

select * 
from final
order by index_vs_aa_audience desc, iab_description
