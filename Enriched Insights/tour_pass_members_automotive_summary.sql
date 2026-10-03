{#
  SIG financial (Audience Acuity) attribute distributions for TOUR Pass members.
  Explicit column list (AA_SIG_FINANCIAL) — no macro.
#}

with 
gigya_automotive_summary as (
    select
        m.personid,
        m.uid as gigyaid,
        m.email,
        UPPER(a.make) as make,
        a.model,
        a.manufacturer, 
        a.manufacturerbased,
        a.year,
        a.fuel,
        case when a.msrp < 10000 then 'Under $10,000'
            when a.msrp between 10000 and 20000 then '$10,000 - $20,000'
            when a.msrp between 20000 and 30000 then '$20,000 - $30,000'
            when a.msrp between 30000 and 40000 then '$30,000 - $40,000'
            when a.msrp between 40000 and 50000 then '$40,000 - $50,000'
            when a.msrp between 50000 and 60000 then '$50,000 - $60,000'
            when a.msrp between 60000 and 70000 then '$60,000 - $70,000'
            when a.msrp between 70000 and 80000 then '$70,000 - $80,000'
            when a.msrp between 80000 and 90000 then '$80,000 - $90,000'
            when a.msrp between 90000 and 100000 then '$90,000 - $100,000'
            when a.msrp > 100000 then '$100,000+'
        end as msrp_range,
        year(a.purchasedate) as purchase_year,
        case when a.purchasenew = 1 then TRUE else FALSE end as purchasenew, 
        a.bodytype, 
        a.bodysubtype,
        a.class, 
        a.doors,
        a.drivetype,
        a.vechicletype as vehicletype,
        a.size,
        a.weight,
        case when a.maxpayload < 1000 then 'Under 1,000 lbs'
            when a.maxpayload between 1000 and 2000 then '1,000 - 2,000 lbs'
            when a.maxpayload between 2000 and 3000 then '2,000 - 3,000 lbs'
            when a.maxpayload between 3000 and 4000 then '3,000 - 4,000 lbs'
            when a.maxpayload between 4000 and 5000 then '4,000 - 5,000 lbs'
            when a.maxpayload between 5000 and 6000 then '5,000 - 6,000 lbs'
            when a.maxpayload between 6000 and 7000 then '6,000 - 7,000 lbs'
            when a.maxpayload between 7000 and 8000 then '7,000 - 8,000 lbs'
            when a.maxpayload between 8000 and 9000 then '8,000 - 9,000 lbs'
            when a.maxpayload between 9000 and 10000 then '9,000 - 10,000 lbs'
            when a.maxpayload > 10000 then '10,000+ lbs'
        end as maxpayload_range,
        a.trim, 
        a.enginecylinders,
        a.transmissiontype, 
        a.transmissiongears,
        a.gvwrange,
        a.number_of_vehicles_in_hh
    from {{ ref('int_account_and_email_account') }} m
    join {{ ref('us_full_golden_record_sig_auto') }} a
        on m.personid = a.personid
    where m.uid is not null
),

demographic_unpivot as (
    select
        personid,
        'AA_Make' as attribute,
        make::varchar as value
    from gigya_automotive_summary
    union all
    select personid, 'AA_Model', to_varchar(model) from gigya_automotive_summary
    union all
    select personid, 'AA_Manufacturer', to_varchar(manufacturer) from gigya_automotive_summary
    union all
    select personid, 'AA_Manufacturer_Based', to_varchar(manufacturerbased) from gigya_automotive_summary
    union all
    select personid, 'AA_Year', to_varchar(year) from gigya_automotive_summary
    union all
    select personid, 'AA_Fuel', to_varchar(fuel) from gigya_automotive_summary
    union all
    select personid, 'AA_MSRP_Range', to_varchar(msrp_range) from gigya_automotive_summary
    union all
    select personid, 'AA_Purchase_Year', to_varchar(purchase_year) from gigya_automotive_summary
    union all
    select personid, 'AA_Purchased_New', to_varchar(purchasenew) from gigya_automotive_summary
    union all
    select personid, 'AA_Body_Type', to_varchar(bodytype) from gigya_automotive_summary
    union all
    select personid, 'AA_Body_Subtype', to_varchar(bodysubtype) from gigya_automotive_summary
    union all
    select personid, 'AA_Class', to_varchar(class) from gigya_automotive_summary
    union all
    select personid, 'AA_Doors', to_varchar(doors) from gigya_automotive_summary
    union all
    select personid, 'AA_Drive_Type', to_varchar(drivetype) from gigya_automotive_summary
    union all
    select personid, 'AA_Vehicle_Type', to_varchar(vehicletype) from gigya_automotive_summary
    union all
    select personid, 'AA_Size', to_varchar(size) from gigya_automotive_summary
    union all
    select personid, 'AA_Weight', to_varchar(weight) from gigya_automotive_summary
    union all
    select personid, 'AA_Max_Payload_Range', to_varchar(maxpayload_range) from gigya_automotive_summary
    union all
    select personid, 'AA_Trim', to_varchar(trim) from gigya_automotive_summary
    union all
    select personid, 'AA_Engine_Cylinders', to_varchar(enginecylinders) from gigya_automotive_summary
    union all
    select personid, 'AA_Transmission_Type', to_varchar(transmissiontype) from gigya_automotive_summary
    union all
    select personid, 'AA_Transmission_Gears', to_varchar(transmissiongears) from gigya_automotive_summary
    union all
    select personid, 'AA_GVW_Range', to_varchar(gvwrange) from gigya_automotive_summary
    union all
    select personid, 'AA_Number_of_Vehicles_in_HH', to_varchar(number_of_vehicles_in_hh) from gigya_automotive_summary
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