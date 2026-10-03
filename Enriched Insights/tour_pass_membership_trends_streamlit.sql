{{
    config(
        materialized = 'view'
    )
}}

{#
  Streamlit-friendly 24-month trend series for TOUR Pass membership:
  - total_tour_pass_members: cumulative distinct registrations through each month
  - active_tour_pass_members_rolling_12m: distinct uids whose LASTLOGIN falls in trailing 12 months

  Note: "active rolling 12m" is derived from the current `lastlogin` field (latest-ever login timestamp),
  aggregated by month and rolled up over 12 months.
#}

with
    month_spine_24 as (
        select
            dateadd(
                month,
                -seq4(),
                date_trunc('month', current_date())
            )::date as month_start
        from table(generator(rowcount => 24))
    ),

    months as (
        select
            month_start,
            last_day(month_start)::date as month_end
        from month_spine_24
    ),

    bounds as (
        select
            min(month_start) as min_month_start,
            max(month_end) as max_month_end
        from months
    ),

    members as (
        select distinct
            uid,
            to_date(created) as created_date,
            to_date(lastlogin) as lastlogin_date
        from {{ ref('int_account_and_email_account') }}
        where uid is not null
    ),

    baseline_total_members as (
        select
            count(distinct uid) as members_before_spine
        from members
        where created_date is not null
          and created_date < (select min_month_start from bounds)
    ),

    registrations_by_month as (
        select
            date_trunc('month', created_date)::date as month_start,
            count(distinct uid) as new_registrations
        from members
        where created_date is not null
          and created_date >= (select min_month_start from bounds)
          and created_date <= (select max_month_end from bounds)
        group by 1
    ),

    lastlogins_by_month as (
        select
            date_trunc('month', lastlogin_date)::date as month_start,
            count(distinct uid) as lastlogin_uids
        from members
        where lastlogin_date is not null
          and lastlogin_date >= (select min_month_start from bounds)
          and lastlogin_date <= (select max_month_end from bounds)
        group by 1
    ),

    joined as (
        select
            m.month_start,
            m.month_end,
            coalesce(r.new_registrations, 0) as new_registrations,
            coalesce(l.lastlogin_uids, 0) as lastlogin_uids
        from months m
        left join registrations_by_month r
            on r.month_start = m.month_start
        left join lastlogins_by_month l
            on l.month_start = m.month_start
    ),

    calc as (
        select
            j.month_start,
            j.month_end,
            j.new_registrations,
            (select members_before_spine from baseline_total_members)
                + sum(j.new_registrations) over (
                    order by j.month_start
                    rows between unbounded preceding and current row
                ) as total_tour_pass_members,
            sum(j.lastlogin_uids) over (
                order by j.month_start
                rows between 11 preceding and current row
            ) as active_tour_pass_members_rolling_12m
        from joined j
    )

select
    month_start,
    month_end,
    new_registrations,
    total_tour_pass_members,
    active_tour_pass_members_rolling_12m
from calc
where month_start >= dateadd(month, -23, date_trunc('month', current_date()))::date
order by month_start asc

