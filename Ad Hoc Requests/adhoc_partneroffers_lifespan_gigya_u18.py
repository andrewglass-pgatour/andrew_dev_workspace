"""
Ad hoc: (1) PartnerOffers (Fan Connect) subscriber lifespan; (2) Gigya <18 accounts created after Pass launch.
Auth: externalbrowser SSO (same as dbt profile). Writes CSVs + results.md next to this script.
"""
import os, sys
import pandas as pd
import snowflake.connector

OUT = os.path.dirname(os.path.abspath(__file__))
PASS_LAUNCH = sys.argv[1] if len(sys.argv) > 1 else '2026-01-01'  # override: python script.py YYYY-MM-DD

Q_LIFESPAN = """
with ev as (
    select lower(emailaddress) as email, lower(eventtype) as eventtype, eventdate
    from pgat.golden.subscriptionevents
    where newsletter = 'PartnerOffers' and lower(eventtype) in ('optin','optout')
),
seq as (
    select email, eventtype, eventdate,
           lead(eventtype) over (partition by email order by eventdate) as next_type,
           lead(eventdate) over (partition by email order by eventdate) as next_date
    from ev
),
spells as (  -- every optin immediately followed by an optout
    select email, eventdate as optin_date, next_date as optout_date,
           datediff('day', eventdate, next_date) as days_subscribed
    from seq where eventtype = 'optin' and next_type = 'optout'
)
select count(*) as completed_spells, count(distinct email) as distinct_emails,
       round(avg(days_subscribed),1) as avg_days, round(median(days_subscribed),1) as median_days,
       round(avg(days_subscribed)/30.4375,2) as avg_months, round(median(days_subscribed)/30.4375,2) as median_months,
       round(percentile_cont(0.25) within group (order by days_subscribed),1) as p25_days,
       round(percentile_cont(0.75) within group (order by days_subscribed),1) as p75_days,
       round(percentile_cont(0.90) within group (order by days_subscribed),1) as p90_days,
       sum(iff(days_subscribed = 0, 1, 0)) as same_day_unsubs
from spells
"""
Q_LIFESPAN_EXCL0 = Q_LIFESPAN.replace("from spells", "from spells where days_subscribed > 0")
Q_LIFESPAN_BASE = """
select count(distinct lower(emailaddress)) as ever_opted_in,
       count(distinct iff(lower(eventtype)='optout', lower(emailaddress), null)) as ever_opted_out
from pgat.golden.subscriptionevents where newsletter='PartnerOffers'
"""
Q_U18 = f"""
with a as (
    select gigyaid, gigyacreated::date as created_date,
           coalesce(age, iff(dob is not null, datediff('year', try_to_date(dob::string), current_date()), null)) as age_calc
    from analytics.prod_gigya.gigya_summary
    qualify row_number() over (partition by gigyaid order by gigyalastupdated desc nulls last) = 1
)
select count(*) as u18_accounts,
       count_if(created_date >= '{PASS_LAUNCH}') as created_on_or_after_launch,
       round(100*count_if(created_date >= '{PASS_LAUNCH}')/nullif(count(*),0),2) as pct_after_launch,
       count_if(created_date >= '2026-01-01') as created_2026,
       round(100*count_if(created_date >= '2026-01-01')/nullif(count(*),0),2) as pct_2026,
       min(created_date) as earliest_created, max(created_date) as latest_created
from a where age_calc is not null and age_calc < 18
"""
Q_U18_MONTH = """
with a as (
    select gigyaid, gigyacreated::date as created_date,
           coalesce(age, iff(dob is not null, datediff('year', try_to_date(dob::string), current_date()), null)) as age_calc
    from analytics.prod_gigya.gigya_summary
    qualify row_number() over (partition by gigyaid order by gigyalastupdated desc nulls last) = 1
)
select date_trunc('month', created_date) as created_month, count(*) as u18_accounts
from a where age_calc < 18 and created_date >= '2025-07-01' group by 1 order by 1
"""

con = snowflake.connector.connect(account='vza78146.us-east-1', user='andrewglass@pgatourhq.com',
    authenticator='externalbrowser', role='DBT_PRODUCTION', warehouse='DBT_WH_XSMALL')
res = {}
for name, q in [('lifespan_all', Q_LIFESPAN), ('lifespan_excl_same_day', Q_LIFESPAN_EXCL0),
                ('lifespan_base', Q_LIFESPAN_BASE), ('u18_summary', Q_U18), ('u18_by_month', Q_U18_MONTH)]:
    df = pd.read_sql(q, con); res[name] = df
    df.to_csv(os.path.join(OUT, f'{name}.csv'), index=False)
    print(f'\n== {name} ==\n{df.to_string(index=False)}')
with open(os.path.join(OUT, 'results.md'), 'w') as f:
    f.write(f'# Ad hoc results (Pass launch cutoff used: {PASS_LAUNCH})\n\n')
    for k, v in res.items():
        f.write(f'## {k}\n\n{v.to_markdown(index=False)}\n\n')
con.close()
