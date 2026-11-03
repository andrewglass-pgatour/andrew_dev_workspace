/* =====================================================================
   THE PLAYERS attendee Fan Profile (2025-2027 tournaments, incl. parking)
   Run in Snowsight: select all and Run All (creates 3 temp tables),
   then run each numbered query at the bottom on its own to see results.
   Logic mirrors unified_fan_profile_source_distribution.sql, filtered to cohort.
   ===================================================================== */

use warehouse ANALYTICS_WH;  -- <-- change to a warehouse you have access to (or delete this line)

/* ---------------------------------------------------------------------
   0) COHORT: personids with a PLAYERS ticket/parking record
--------------------------------------------------------------------- */
create or replace temporary table players_cohort as
select distinct personid
from analytics.prod_archtics.archtics_tournament_summary
where personid <> ''
  and tournament in (
      '2025 THE PLAYERS', '2025 THE PLAYERS Parking',
      '2026 THE PLAYERS', '2026 THE PLAYERS Parking',
      '2027 THE PLAYERS', '2027 THE PLAYERS Parking'
  );

/* ---------------------------------------------------------------------
   1) COHORT FAN PROFILE: unified_fan_profile rows + age range
--------------------------------------------------------------------- */
create or replace temporary table players_cohort_profile as
select
    u.*,
    case
        when AA_AGE between 18 and 24 then '18-24'
        when AA_AGE between 25 and 34 then '25-34'
        when AA_AGE between 35 and 44 then '35-44'
        when AA_AGE between 45 and 54 then '45-54'
        when AA_AGE between 55 and 64 then '55-64'
        when AA_AGE >= 65 then '65+'
    end as AGE_RANGE
from analytics.prod_golden.unified_fan_profile u
join players_cohort c on u.personid = c.personid;

/* ---------------------------------------------------------------------
   2) GEOGRAPHY: ZIP -> DMA for the cohort (zip comes from golden fan master)
--------------------------------------------------------------------- */
create or replace temporary table players_cohort_geo as
with person_zip as (
    select
        s.personid,
        max(s.country) as country,
        max(s.state) as state,
        max(left(trim(s.zip), 5)) as zip
    from analytics.prod_archtics.archtics_tournament_summary s
    join players_cohort c on s.personid = c.personid
    where nullif(trim(s.zip), '') is not null   -- drops NULL and blank/whitespace zips
    group by s.personid
)
select
    p.personid,
    -- blanks and 'Unknown' are nulled rather than labelled
    nullif(upper(coalesce(nullif(trim(z.country), ''), nullif(trim(p.country), ''))), 'UNKNOWN') as country,
    nullif(upper(coalesce(nullif(trim(z.state), ''), nullif(trim(p.state), ''))), 'UNKNOWN') as state,
    nullif(upper(trim(z.dma_name)), 'UNKNOWN') as dma_name,
    z.dma_code,
    nullif(upper(trim(z.primary_city)), 'UNKNOWN') as city,
    nullif(p.zip, '') as zip
from person_zip p
join pgat.lookup.us_zip_code_to_dma z on p.zip = z.zip   -- inner join: only zips that resolve to a DMA
where nullif(upper(trim(z.dma_name)), 'UNKNOWN') is not null
  and trim(z.dma_name) <> '';


/* =====================================================================
   RESULT QUERIES - run each one separately
===================================================================== */

-- 1) Cohort summary
select
    count(*)                                         as cohort_fans,
    sum(Total_Tickets)                               as total_tickets_all_years,   -- all tournaments, not only PLAYERS
    sum(Total_Ticket_Spend)                          as total_ticket_spend_all_years,
    count_if(TOUR_Pass_Member)                       as tour_pass_members,
    count_if(PGA_TOUR_Fan_Shop_Buyer)                as fan_shop_buyers,
    count_if(AA_AGE is not null)                     as with_audience_acuity_match
from players_cohort_profile;

-- 2) Demographic distribution (same shape as unified_fan_profile_source_distribution)
with demographic_unpivot as (
    select personid, 'AA_Age_Range' as attribute, AGE_RANGE::varchar as value from players_cohort_profile
    union all select personid, 'AA_Gender', AA_GENDER::varchar from players_cohort_profile
    union all select personid, 'AA_Marital_Status', AA_MARITAL_STATUS::varchar from players_cohort_profile
    union all select personid, 'AA_Children_HH', AA_HH_CHILDREN::varchar from players_cohort_profile
    union all select personid, 'AA_Home_Owner', AA_HOME_OWNER::varchar from players_cohort_profile
    union all select personid, 'AA_Income_HH', AA_HH_INCOME::varchar from players_cohort_profile
    union all select personid, 'AA_Net_Worth_HH', AA_HH_NET_WORTH::varchar from players_cohort_profile
    union all select personid, 'AA_Credit_Range', AA_CREDIT_RANGE::varchar from players_cohort_profile
    union all select personid, 'AA_Occupation_Category', AA_OCCUPATION_CATEGORY::varchar from players_cohort_profile
),
valid as (
    select * from demographic_unpivot
    where nullif(trim(value), '') is not null
      and upper(trim(value)) <> 'UNKNOWN'   -- treat 'Unknown' as null
)
select
    attribute,
    value as field_value,
    count(*) as field_records,
    sum(count(*)) over (partition by attribute) as attribute_total,
    count(*) / sum(count(*)) over (partition by attribute) as field_distribution
from valid
group by attribute, value
order by attribute, field_records desc;

-- 3) First-party source overlap: % of cohort in each source
with sources as (
    select personid, 'Fan Council Members' as source_type, Fan_Council_Member as flag from players_cohort_profile
    union all select personid, 'PartnerOffers Subscribers', Partner_Offers_Subscriber from players_cohort_profile
    union all select personid, 'Wire2Wire Subscribers', Wire_to_Wire_Subscriber from players_cohort_profile
    union all select personid, 'VIP Volunteer Subscribers', VIP_Volunteer_Subscriber from players_cohort_profile
    union all select personid, 'The Early Card Subscribers', The_Early_Card_Subscriber from players_cohort_profile
    union all select personid, 'Champions Minute Monthly Subscribers', Champions_Monthly_Minute_Subscriber from players_cohort_profile
    union all select personid, 'Signature Scroll Subscribers', Signature_Scroll_Subscriber from players_cohort_profile
    union all select personid, 'Fanatics Buyers', PGA_TOUR_Fan_Shop_Buyer from players_cohort_profile
    union all select personid, 'Current Season Fantasy Players', Current_Season_Fantasy_Player from players_cohort_profile
    union all select personid, 'TOUR Pass Member', TOUR_Pass_Member from players_cohort_profile
    union all select personid, 'EA PGA TOUR Players', EA_PGA_TOUR_Player from players_cohort_profile
    union all select personid, 'PLAYERS Newsletter Subscribers', PLAYERS_Newsletter_Subscriber from players_cohort_profile
    union all select personid, 'Cognizant Newsletter Subscribers', Cognizant_Newsletter_Subscriber from players_cohort_profile
    union all select personid, 'Truist Newsletter Subscribers', Truist_Newsletter_Subscriber from players_cohort_profile
    union all select personid, 'Biltmore Championship Newsletter Subscribers', Biltmore_Championship_Newsletter_Subscriber from players_cohort_profile
    union all select personid, 'Cadillac Championship Newsletter Subscribers', Cadillac_Championship_Newsletter_Subscriber from players_cohort_profile
)
select
    source_type,
    count_if(flag = true) as fans_in_source,
    (select count(*) from players_cohort_profile) as cohort_fans,
    count_if(flag = true) / (select count(*) from players_cohort_profile)::float as pct_of_cohort
from sources
group by source_type
order by fans_in_source desc;

-- 4) Geography: by DMA
select
    dma_name,
    dma_code,
    count(distinct personid) as fans,
    count(distinct personid) / sum(count(distinct personid)) over () as pct_of_cohort
from players_cohort_geo
group by dma_name, dma_code
order by fans desc;

-- 5) Geography: by ZIP (with DMA)
select
    zip,
    city,
    state,
    dma_name,
    count(distinct personid) as fans,
    count(distinct personid) / sum(count(distinct personid)) over () as pct_of_cohort
from players_cohort_geo
group by zip, city, state, dma_name
order by fans desc;

-- 6) Geography: by state
select
    country,
    state,
    count(distinct personid) as fans,
    count(distinct personid) / sum(count(distinct personid)) over () as pct_of_cohort
from players_cohort_geo
group by country, state
order by fans desc;

-- 7) Which PLAYERS years the cohort attended (a fan can appear in several)
select
    t.tournament,
    count(distinct t.personid) as fans,
    sum(t.total_tickets) as tickets
from analytics.prod_archtics.archtics_tournament_summary t
join players_cohort c on t.personid = c.personid
where t.tournament in (
      '2025 THE PLAYERS', '2025 THE PLAYERS Parking',
      '2026 THE PLAYERS', '2026 THE PLAYERS Parking',
      '2027 THE PLAYERS', '2027 THE PLAYERS Parking')
group by t.tournament
order by t.tournament;
