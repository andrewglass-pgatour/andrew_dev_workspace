{#
  SIG financial (Audience Acuity) attribute distributions for TOUR Pass members.
  Explicit column list (AA_SIG_FINANCIAL) — no macro.
#}

with 
gigya_financial_summary as (
    select
        m.personid,
        m.uid as gigyaid,
        m.email,
        m.lastlogin as gigya_last_login,
        m.created as gigya_created,
        f.discretionary_income,
        f.mortgage_open1st_intent,
        f.mortgage_new_intent,
        f.mortgage_open2nd_intent,
        f.mortgage_refinance_intent,
        f.automotive_loan_intent,
        f.bank_card_intent,
        f.personal_loan_intent,
        f.retail_card_intent,
        f.student_loan_cons_intent,
        f.student_loan_intent,
        f.automotive_offer_response,
        f.personal_loan_response,
        f.card_offer_response,
        f.mortgage_offer_response
    from {{ ref('int_account_and_email_account') }} m
    join {{ ref('us_full_golden_record_sig_financial') }} f
        on m.personid = f.personid
    where m.uid is not null
),

demographic_unpivot as (
    select
        personid,
        'AA_Discretionary_Income' as attribute,
        discretionary_income::varchar as value
    from gigya_financial_summary
    union all
    select personid, 'AA_Mortgage_Open_1st_Intent', to_varchar(mortgage_open1st_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Mortgage_New_Intent', to_varchar(mortgage_new_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Mortgage_Open_2nd_Intent', to_varchar(mortgage_open2nd_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Mortgage_Refinance_Intent', to_varchar(mortgage_refinance_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Automotive_Loan_Intent', to_varchar(automotive_loan_intent) from gigya_financial_summary
    union all   
    select personid, 'AA_Bank_Card_Intent', to_varchar(bank_card_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Personal_Loan_Intent', to_varchar(personal_loan_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Retail_Card_Intent', to_varchar(retail_card_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Student_Loan_Cons_Intent', to_varchar(student_loan_cons_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Student_Loan_Intent', to_varchar(student_loan_intent) from gigya_financial_summary
    union all
    select personid, 'AA_Automotive_Loan_Offer_Response', to_varchar(automotive_offer_response) from gigya_financial_summary
    union all
    select personid, 'AA_Personal_Loan_Response', to_varchar(personal_loan_response) from gigya_financial_summary
    union all
    select personid, 'AA_Card_Offer_Response', to_varchar(card_offer_response) from gigya_financial_summary
    union all
    select personid, 'AA_Mortgage_Offer_Response', to_varchar(mortgage_offer_response) from gigya_financial_summary
),

demographic_totals as (
    select
        attribute,
        count(*) as attribute_total
    from demographic_unpivot
    where value is not null and value <> ''
    group by attribute
),

demographic_counts as (
    select
        'DEMOGRAPHIC' as metric_type,
        d.attribute as attribute,
        d.value as field_value,
        count(*) as field_records,
        t.attribute_total,
        count(*) / nullif(t.attribute_total, 0)::float as field_distribution
    from demographic_unpivot d
    join demographic_totals t
        on d.attribute = t.attribute
    where d.value is not null and d.value <> ''
    group by 1, 2, 3, 5
)

select
    metric_type,
    attribute,
    field_value,
    field_records,
    attribute_total,
    field_distribution
from demographic_counts
order by
    attribute,
    field_records desc