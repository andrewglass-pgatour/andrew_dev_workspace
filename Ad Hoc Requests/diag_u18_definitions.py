import os, snowflake.connector, pandas as pd, warnings
warnings.filterwarnings('ignore')
con = snowflake.connector.connect(account='vza78146.us-east-1', user='andrewglass@pgatourhq.com',
    authenticator='externalbrowser', role='DBT_PRODUCTION', warehouse='DBT_WH_XSMALL')
q = """
with a as (
    select gigyaid, gigyacreated::date as d, age, try_to_date(dob::string) as dob_d
    from analytics.prod_gigya.gigya_summary
    qualify row_number() over (partition by gigyaid order by gigyalastupdated desc nulls last) = 1
)
select 'age field <18' as defn, count(*) n, count_if(d>='2026-03-01') n_mar26_on, count_if(d>='2026-01-01') n_2026 from a where age<18
union all select 'dob-derived <18', count(*), count_if(d>='2026-03-01'), count_if(d>='2026-01-01') from a where datediff('year',dob_d,current_date())<18
union all select 'age<18 and age>=13', count(*), count_if(d>='2026-03-01'), count_if(d>='2026-01-01') from a where age between 13 and 17
union all select 'age or dob <18 (current script)', count(*), count_if(d>='2026-03-01'), count_if(d>='2026-01-01') from a where coalesce(age, datediff('year',dob_d,current_date()))<18
"""
df = pd.read_sql(q, con); print(df.to_string(index=False))
df.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'u18_definition_check.csv'), index=False)
