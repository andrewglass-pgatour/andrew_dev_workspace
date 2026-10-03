{{
    config(
        materialized = 'view'
    )
}}

{#
  Geographic breakdown of TOUR Pass members:
  - Aggregates members by Country, State, DMA, City, and Zip Code.
  - Includes latitude and longitude for mapping.
  - Details both total all-time member counts and rolling 12-month active member counts.
#}

with m as (
    select distinct
        acct.uid,
        left(trim(acct.zip), 5) as clean_zip,
        acct.stateusingip,
        acct.countryusingip,
        acct.lastlogincountry,
        acct.lastlogin
    from {{ ref('int_account_and_email_account') }} acct
    where acct.uid is not null
),

joined as (
    select
        m.uid,
        m.lastlogin,
        coalesce(nullif(trim(zp.country), ''), nullif(trim(m.countryusingip), ''), nullif(trim(m.lastlogincountry), ''), 'Unknown') as country,
        coalesce(nullif(trim(zp.state), ''), nullif(trim(m.stateusingip), ''), 'Unknown') as state,
        coalesce(nullif(trim(zp.dma_name), ''), 'Unknown') as dma_name,
        zp.dma_code,
        zp.latitude,
        zp.longitude,
        coalesce(nullif(trim(zp.primary_city), ''), 'Unknown') as city,
        m.clean_zip as zip
    from m
    left join {{ ref('usa_zipcodes') }} zp on m.clean_zip = zp.zip
)

select
    upper(country) as country,
    upper(state) as state,
    dma_code,
    upper(dma_name) as dma_name,
    upper(city) as city,
    zip,
    latitude,
    longitude,
    count(distinct uid) as member_count,
    count(distinct case when lastlogin >= dateadd(month, -12, current_date()) then uid end) as active_member_count
from joined
group by 1, 2, 3, 4, 5, 6, 7, 8