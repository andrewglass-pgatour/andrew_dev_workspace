/* =====================================================================
   Gigya under-18 accounts: share created after TOUR Pass launch
   Run in Snowsight; each query can be run on its own.
   Under 18 = age field < 18 on analytics.prod_gigya.gigya_summary,
   deduplicated to one row per Gigya ID. (DOB is rarely populated; only
   ~11 accounts are under 18 by DOB.)
   Set the launch date below. Monthly counts show a jump in March 2026.
   ===================================================================== */

use warehouse ANALYST_ADHOC_XS;
use pgat.gigya;

set pass_launch = '2026-03-12';  -- <-- start date of PLAYERS 2026

create or replace temporary table gigya_u18 as
select gigyaid,
       gigyacreated::date as created_date,
       age
from analytics.prod_gigya.gigya_summary
qualify row_number() over (partition by gigyaid order by gigyalastupdated desc nulls last) = 1;

/* 1) Share of under-18 accounts created on/after Pass launch */
select count(*)                                                                as u18_accounts,
       count_if(created_date >= $pass_launch::date)                            as created_on_or_after_tour_pass_launch,
       round(100 * count_if(created_date >= $pass_launch::date) / nullif(count(*), 0), 2) as pct_after_launch,
       count_if(created_date >= '2026-01-01')                                  as created_2026,
       round(100 * count_if(created_date >= '2026-01-01') / nullif(count(*), 0), 2)       as pct_2026,
       min(created_date)                                                       as earliest_created,
       max(created_date)                                                       as latest_created
from gigya_u18
where age < 18;

/* 2) Under-18 accounts created by month (find the launch inflection) */
select date_trunc('month', created_date) as created_month,
       count(*)                          as u18_accounts
from gigya_u18
where age < 18 and created_date >= '2025-07-01'
group by 1
order by 1;

/* 3) Under-18 accounts created by year */
select date_trunc('year', created_date) as created_month,
       count(*)                          as u18_accounts
from gigya_u18
where age < 18
group by 1
order by 1;

/* 4) Definition check: how the count changes with the age definition */
select 'age < 18'        as definition, count(*) as accounts, count_if(created_date >= $pass_launch::date) as after_launch from gigya_u18 where age < 18
union all
select 'age 13 to 17',   count(*), count_if(created_date >= $pass_launch::date) from gigya_u18 where age between 13 and 17;


SELECT DATE, COUNT(*) FROM DRAFTKINGS_PGA_TOUR.PGA.OSB_PGA_AGE 
GROUP BY 1 ORDER BY 1 DESC;

SELECT DKWEEKSTARTDATE, COUNT(*) FROM DRAFTKINGS_PGA_TOUR.PGA.DFS_PGA_CONTESTTYPE 
GROUP BY 1 ORDER BY 1 DESC;