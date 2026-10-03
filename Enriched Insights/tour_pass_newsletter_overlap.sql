{{
    config(
        materialized = 'view'
    )
}}

with
    -- Mirror the Streamlit app logic: derive monthly subscription status from INT_FAN_SUBSCRIBER
    -- (PARTNEROFFERSSUBSCRIBERDATE / UNSUBSCRIBEDPARTNEROFFERSDATE), using month-level comparisons.
    partneroffers_subscriber_dates as (
        select distinct
            lower(email) as email,
            to_timestamp(partnerofferssubscriberdate) as subscribe_date,
            to_timestamp(unsubscribedpartneroffersdate) as unsubscribe_date
        from {{ ref('int_fan_subscriber') }}
        where email is not null
          and (partnerofferssubscriberdate is not null or unsubscribedpartneroffersdate is not null)
          and (
              partnerofferssubscriberdate is null
              or to_timestamp(partnerofferssubscriberdate) <= current_timestamp()
          )
          and (
              unsubscribedpartneroffersdate is null
              or to_timestamp(unsubscribedpartneroffersdate) <= current_timestamp()
          )
    ),

    gigya_users as (
        select distinct
            uid,
            lower(email) as email,
            to_timestamp(created) as created_ts
        from {{ ref('int_account_and_email_account') }}
        where uid is not null
          and email is not null
          and created is not null
          and to_timestamp(created) <= current_timestamp()
    ),

    date_bounds as (
        select
            least(
                coalesce((select min(to_date(subscribe_date)) from partneroffers_subscriber_dates), current_date()),
                coalesce((select min(to_date(created_ts)) from gigya_users), current_date())
            ) as min_date,
            current_date() as max_date
    ),

    -- Snowflake requires GENERATOR(ROWCOUNT=>...) to be a constant literal, so we use a recursive month spine.
    recursive_month_spine as (
        select date_trunc('month', min_date)::date as month_start
        from date_bounds

        union all

        select dateadd(month, 1, rms.month_start) as month_start
        from recursive_month_spine rms
        cross join date_bounds db
        where rms.month_start < date_trunc('month', db.max_date)::date
    ),

    months as (
        select
            month_start,
            last_day(month_start) as month_end
        from recursive_month_spine
    ),

    partneroffers_active_emails_by_month as (
        select distinct
            m.month_start,
            s.email
        from months m
        inner join partneroffers_subscriber_dates s
            on date_trunc('month', s.subscribe_date)::date <= m.month_start
           and (s.unsubscribe_date is null or date_trunc('month', s.unsubscribe_date)::date > m.month_start)
    ),

    partneroffers_active_counts as (
        select
            month_start,
            count(distinct email) as partneroffers_active_subscribers
        from partneroffers_active_emails_by_month
        group by month_start
    ),

    gigya_registered_counts as (
        select
            m.month_start,
            count(distinct g.uid) as gigya_registered_users
        from months m
        inner join gigya_users g
            on date_trunc('month', g.created_ts)::date <= m.month_start
        group by m.month_start
    ),

    overlap_active_counts as (
        select
            m.month_start,
            count(distinct g.uid) as overlap_active_partneroffers_and_gigya_registered
        from months m
        inner join partneroffers_active_emails_by_month p
            on p.month_start = m.month_start
        inner join gigya_users g
            on g.email = p.email
           and date_trunc('month', g.created_ts)::date <= m.month_start
        group by m.month_start
    ),

    gigya_monthly_registrations as (
        select
            date_trunc('month', created_ts)::date as month_start,
            count(distinct uid) as gigya_new_registrations
        from gigya_users
        group by date_trunc('month', created_ts)::date
    )

select
    m.month_start,
    m.month_end,

    coalesce(pac.partneroffers_active_subscribers, 0) as partneroffers_active_subscribers,
    coalesce(grc.gigya_registered_users, 0) as gigya_registered_users,
    coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0) as overlap_active_partneroffers_and_gigya_registered,
    case
        when lag(coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)) over (order by m.month_start) = 0
            then null
        else round(
            (
                coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)
                - lag(coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)) over (order by m.month_start)
            )::float
            / nullif(lag(coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)) over (order by m.month_start), 0)::float,
            4
        )
    end as overlap_mom_pct_change,

    case
        when coalesce(pac.partneroffers_active_subscribers, 0) = 0 then null
        else round(
            coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)::float
            / pac.partneroffers_active_subscribers::float,
            4
        )
    end as pct_partneroffers_with_gigya,

    case
        when coalesce(grc.gigya_registered_users, 0) = 0 then null
        else round(
            coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)::float
            / grc.gigya_registered_users::float,
            4
        )
    end as pct_gigya_with_partneroffers,

    coalesce(gmr.gigya_new_registrations, 0) as gigya_new_registrations,

    coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)
        - lag(coalesce(oac.overlap_active_partneroffers_and_gigya_registered, 0)) over (order by m.month_start)
        as overlap_mom_change
from months m
left join partneroffers_active_counts pac
    on pac.month_start = m.month_start
left join gigya_registered_counts grc
    on grc.month_start = m.month_start
left join overlap_active_counts oac
    on oac.month_start = m.month_start
left join gigya_monthly_registrations gmr
    on gmr.month_start = m.month_start
order by m.month_start desc