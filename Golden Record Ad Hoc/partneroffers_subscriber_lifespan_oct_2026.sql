/* =====================================================================
   PartnerOffers (Fan Connect) subscriber lifespan
   Run in Snowsight; each query can be run on its own.
   Lifespan = days from an opt-in to the next opt-out for the same email.
   Only completed spells (people who unsubscribed) are included, so this
   understates lifespan for people still subscribed.
   ===================================================================== */

use warehouse ANALYTICS_WH;  -- <-- change to a warehouse you have access to (or delete this line)

create or replace temporary table partneroffers_spells as
with ev as (
    select lower(emailaddress) as email, lower(eventtype) as eventtype, eventdate
    from pgat.golden.subscriptionevents
    where newsletter = 'PartnerOffers'
      and lower(eventtype) in ('optin', 'optout')
),
seq as (
    select email, eventtype, eventdate,
           lead(eventtype) over (partition by email order by eventdate) as next_type,
           lead(eventdate) over (partition by email order by eventdate) as next_date
    from ev
)
select email,
       eventdate as optin_date,
       next_date as optout_date,
       datediff('day', eventdate, next_date) as days_subscribed
from seq
where eventtype = 'optin' and next_type = 'optout';

/* 1) Lifespan summary: all completed spells */
select count(*)                                                         as completed_spells,
       count(distinct email)                                            as distinct_emails,
       round(avg(days_subscribed), 1)                                   as avg_days,
       round(median(days_subscribed), 1)                                as median_days,
       round(avg(days_subscribed) / 30.4375, 2)                         as avg_months,
       round(median(days_subscribed) / 30.4375, 2)                      as median_months,
       round(percentile_cont(0.25) within group (order by days_subscribed), 1) as p25_days,
       round(percentile_cont(0.75) within group (order by days_subscribed), 1) as p75_days,
       round(percentile_cont(0.90) within group (order by days_subscribed), 1) as p90_days,
       count_if(days_subscribed = 0)                                    as same_day_unsubs
from partneroffers_spells;

/* 2) Same summary excluding same-day unsubscribes */
select count(*)                                    as completed_spells,
       round(avg(days_subscribed), 1)              as avg_days,
       round(median(days_subscribed), 1)           as median_days,
       round(avg(days_subscribed) / 30.4375, 2)    as avg_months,
       round(median(days_subscribed) / 30.4375, 2) as median_months
from partneroffers_spells
where days_subscribed > 0;

/* 3) Context: how many ever opted in vs. ever opted out */
select count(distinct lower(emailaddress))                                           as ever_opted_in,
       count(distinct iff(lower(eventtype) = 'optout', lower(emailaddress), null))   as ever_opted_out
from pgat.golden.subscriptionevents
where newsletter = 'PartnerOffers';

/* 4) Optional: lifespan by opt-in year (shows legacy-list skew) */
select year(optin_date)                        as optin_year,
       count(*)                                as completed_spells,
       round(avg(days_subscribed), 1)          as avg_days,
       round(median(days_subscribed), 1)       as median_days
from partneroffers_spells
group by 1
order by 1;
