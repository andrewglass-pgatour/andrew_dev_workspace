{#
  Two header KPIs for the TOUR Pass User Overview Streamlit app (fixed regardless of ENR/Financial):
  1) All-time members (row count of distinct Gigya account rows, uid not null)
  2) Rolling-12m actives: distinct uids with lastlogin in the trailing 12 months
  One scan: aggregate from the same distinct-member grain as the prior two-CTE design.
#}

with m as (
    select distinct
        acct.personid,
        acct.uid,
        acct.email,
        acct.lastlogin,
        acct.created
    from {{ ref('int_account_and_email_account') }} acct
    where acct.uid is not null
),

agg as (
    select
        count(*) as n_all_time,
        count(distinct case when m.lastlogin >= dateadd(month, -12, current_date()) then m.uid end) as n_rolling_12m, -- Rolling 12m active users 
        count(distinct case when m.created >= '2026-01-01' then m.uid end) as n_ytd -- YTD new users
    from m
)

select
    'KEY_COUNT' as metric_type,
    'TOTAL_TOUR_PASS_MEMBERS_ALL_TIME' as attribute,
    null::varchar as field_value,
    a.n_all_time::number as field_records,
    null::number as attribute_total,
    null::float as field_distribution
from agg a

union all

select
    'KEY_COUNT' as metric_type,
    'TOTAL_TOUR_PASS_MEMBERS_LOGGED_IN_ROLLING_12M' as attribute,
    null::varchar as field_value,
    a.n_rolling_12m::number as field_records,
    null::number as attribute_total,
    null::float as field_distribution
from agg a

union all

select
    'KEY_COUNT' as metric_type,
    'TOTAL_TOUR_PASS_REGISTRATIONS_IN_2026' as attribute,
    null::varchar as field_value,
    a.n_ytd::number as field_records,
    null::number as attribute_total,
    null::float as field_distribution
from agg a
