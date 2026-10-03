with
    fan as (
        select * from {{ ref('mops_golden_fan_master') }}
    ),

    unified_fan_profile as (
        select fan.personid, 
            fan.email1, 
            fan.email2,
            case when tournament_summary.personid is not null then true else false end as Archtics_Attendee,
            sum(tournament_summary.total_spend) as Total_Ticket_Spend,
            sum(tournament_summary.total_tickets) as Total_Tickets,
            listagg(distinct tournament_summary.tournament, ', ') WITHIN GROUP (ORDER BY tournament_summary.tournament DESC) as Tournaments_Attended,
            case when gigya.personid is not null then true else false end as TOUR_Pass_Member,
            case when gigya.lastlogin >= '2025-01-01' then true else false end as TOUR_Pass_Login_Since_2005,
            case when fanatics.personid is not null then true else false end as PGA_TOUR_Fan_Shop_Buyer,
            count(distinct fanatics.order_id) as PGA_TOUR_Fan_Shop_Purchases, 
            max(fanatics.total_customer_spend) as PGA_TOUR_Fan_Shop_Total_Spend,
            case when fantasy.personid is not null then true else false end as Current_Season_Fantasy_Player,
            case when ea.personid is not null then true else false end as EA_PGA_TOUR_Player,            
            iff(
                (case when ea.personid is not null then true else false end)
                or (case when fantasy.personid is not null then true else false end),
                true, false
            ) as EA_or_Current_Season_Fantasy_Player,
            case when wit.personid is not null then true else false end as Wit_Participant,
            fantasy.total_tournaments_played as Fantasy_Tournaments_Played,
            iff(subs.CHAMPIONS_MONTHLY_MINUTE_SUBSCRIBER = TRUE, TRUE, FALSE) as Champions_Monthly_Minute_Subscriber,
            iff(subs.WIRE_TO_WIRE_SUBSCRIBER = TRUE, TRUE, FALSE) as Wire_to_Wire_Subscriber,
            iff(subs.PARTNER_OFFERS_SUBSCRIBER ilike 'true', true, false) as Partner_Offers_Subscriber,
            iff(subs.THE_EARLY_CARD_SUBSCRIBER ilike 'true', true, false) as The_Early_Card_Subscriber,
            iff(subs.VIP_VOLUNTEER_SUBSCRIBER_DATE ilike 'true', true, false) as VIP_Volunteer_Subscriber,
            iff(subs.SIGNATURE_SCROLL_SUBSCRIBER = TRUE, TRUE, FALSE) as Signature_Scroll_Subscriber,
            case when fan_council.personid is not null then true else false end as Fan_Council_Member,
            aa_enr.age as AA_Age,
            aa_enr.gender as AA_Gender,
            aa_enr.marital_status as AA_Marital_Status,
            aa_enr.children_hh as AA_HH_Children,
            aa_enr.home_owner as AA_Home_Owner,
            aa_enr.income_hh as AA_HH_Income,
            aa_enr.net_worth_hh as AA_HH_Net_Worth,
            aa_enr.credit_range as AA_Credit_Range,
            aa_enr.occupation_category as AA_Occupation_Category,
            --listagg(distinct aa_auto.MANUFACTURER, ', ') WITHIN GROUP (ORDER BY aa_auto.MANUFACTURER) as AA_Car_Make_Owned
        from fan
        left join {{ ref('fanatics_purchase_summary') }} as fanatics on fan.personid = fanatics.personid 
        left join {{ ref('int_account_and_email_account') }} as gigya on fan.personid = gigya.personid
        left join {{ ref('fantasy_summary_current_season') }} as fantasy on fan.personid = fantasy.personid
        left join {{ ref('newsletter_subscription_summary') }} as subs on fan.personid = subs.personid
        left join {{ ref('archtics_tournament_summary') }} as tournament_summary on fan.personid = tournament_summary.personid 
        left join {{ ref('ea_sports_summary') }} as ea on fan.personid = ea.personid 
        left join {{ ref('fan_council_directory') }} as fan_council on fan.personid = fan_council.personid
        left join {{ source('audience_acuity', 'us_full_golden_record_enriched_enr') }} as aa_enr on fan.personid = aa_enr.cid
        left join {{ ref('wit_user_summary')}} as wit on fan.personid = wit.personid
        --join {{ source('aa_sig_auto', 'aa_sig_auto') }} as aa_auto on aa_enr.aa_id = aa_auto.id 
        group by all
    )

    select * from unified_fan_profile