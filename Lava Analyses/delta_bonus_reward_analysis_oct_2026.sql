/* ============================================================================
   DELTA SKYMILES CASH — $5 BONUS CREDIT (REWARD_ID 43)
   TOUR Championship 2026 (East Lake)
   v5 — rebuilt around the Lava reward summary; adds spend, ROI and benchmarks
   ----------------------------------------------------------------------------
   AUDIENCE: Marketing. The question is "how well did the Delta perk granted
   through TOUR Pass perform?" Read in this order:
     §1  Scorecard       reach, activation, value redeemed, fan spend
     §2  Benchmark       Delta against every other stored-value reward
     §3  Spend & ROI     what fans spent alongside the $5, vs. baskets with no perk
     §4  Who             Pass-signup timing, ticketing, adoption
     §5+ Detail          day curve, locations, leakage, data quality

   WHAT CHANGED FROM v4

   1. HEADLINE NUMBERS COME FROM LAVA_REWARD_SUMMARY (new model). v4 rebuilt
      grants, redemptions and activation by hand from the int_ layer. The reward
      summary is the one governed definition (test rewards / test members /
      voids excluded, grants net of cancellations, tournament windows from
      lookups.tournament_schedule), so §1 reads it directly and §1b reconciles
      it to the event-level working set. Any gap in §1b is worth chasing before
      a number is quoted.

   2. SPEND IS NOW MEASURED (§3). v4 stopped at "$X redeemed". The question
      Marketing actually asks is whether the credit brought fans in to spend
      their own money.
      HOW SPEND IS READ (checked against the data, worth knowing):
        Lava does not record the credit on Delta transactions — the
        transaction's redeemed amount is 0 and TOTAL_SPENT is what the fan
        paid AFTER the credit (267 of 1,327 Delta baskets are smaller than the
        credit applied, 113 are $0, which a gross figure could not be). So:
          cash spend               = TOTAL_SPENT as recorded (fan's own money)
          gross basket value       = cash + stored-value credit drawn in the basket
          spend per credit dollar  = gross basket value / Delta credit applied
          fan cash per credit $    = cash / Delta credit applied
        Where a transaction does carry the credit (redeemed amount > 0, ~7% of
        redemption transactions overall, none for Delta) nothing is added back.
        This is an inference from the transaction pattern, not a documented
        field: confirm with Lava before quoting gross figures externally. Cash
        spend needs no inference.
      §3d compares Delta baskets with baskets at the same tournament that used
      no reward, which is the closest thing to a lift read the data supports.
      It is NOT a controlled lift test: fans who redeem a perk differ from fans
      who do not.

   3. BENCHMARK (§2). An 84% activation rate means little in isolation. §2 lines
      Delta up against every stored-value reward on the same measures, including
      reward 16 (PLAYERS - Delta Stored Value, a different activation).

   4. OFFER-TO-REDEMPTION BY PASS STATUS (§4e) uses
      tour_pass_lava_reward_redemption_streamlit, which already splits offered
      vs. redeemed for Pass members.

   5. GRANT TIMING (§7) — was the credit delivered before the event or at it,
      and how does activation differ.

   6. TEST MEMBERS ARE EXCLUDED FROM GRANTS TOO. v4 filtered them from the gold
      model but not from delta_grants.

   7. UNCHANGED FROM v4: reward pinned to REWARD_ID 43, Pass signup attribution
      on Gigya (TOUR_PASS_SIGNUP_DATE), Archtics ticketing linkage.

   DEPENDS ON (all in ANALYTICS / INTERMEDIATE, schema PROD_LAVA unless noted)
     LAVA_REWARD_SUMMARY            NEW — build first: dbt run -s lava_reward_summary
     LAVA_TOURNAMENT_REDEMPTIONS    existing
     LAVA_USER_SUMMARY              existing
     INT_LAVA_* (rewards, members, grants, redemptions, transactions)
     PROD_TOUR_PASS.TOUR_PASS_LAVA_REWARD_REDEMPTION_STREAMLIT   existing view

   GRAIN REMINDERS
     LAVA_TOURNAMENT_REDEMPTIONS: one row = one member x one reward x one
       tournament, carrying REDEMPTION_COUNT. Never COUNT(*) it and call the
       result redemptions — SUM(redemption_count).
     LAVA_REWARD_SUMMARY: one row per reward, all time. Delta was only live at
       this tournament, so reward-level = event-level (§1b proves it).
     delta_baskets (below): one row per POS transaction that used the credit.
       Spend is summed over transactions, never over redemptions, because one
       basket can contain several redemptions.
   ============================================================================ */


/* =================================== §0a =================================
   CONSTANTS
   ========================================================================= */
create or replace temporary table delta_params as (
    select
        'tour-championship-2026'::varchar   as tournament_id,
        43                                  as delta_reward_id
);

/* Confirm the reward is what we think it is before anything else runs. */
select r.reward_id, r.reward_name, r.reward_slug, r.reward_type, r.amount_type,
       r.is_hidden, r.is_deleted, r.is_test_reward
from INTERMEDIATE.PROD_LAVA.INT_LAVA_REWARDS r
join delta_params p on p.delta_reward_id = r.reward_id;
-- expect: 43, "Delta SkyMiles Cash", Stored Value, currency, not deleted, not test


/* =================================== §0b =================================
   EVENT WINDOW
   ========================================================================= */
create or replace temporary table delta_event as (
    select l.*
    from PGAT.LAVA.LAVA_TOURNAMENT_LOOKUP l
    join delta_params p on p.tournament_id = l.tournament_id
);

select tournament_id, tournament_name, official_start_date, official_end_date,
       window_start_date, window_end_date, timezone
from delta_event;
-- expect: 2026-08-27 .. 2026-08-30 official, 2026-08-24 .. 2026-08-30 window, America/New_York


/* =================================== §0c =================================
   WORKING SETS
   ========================================================================= */
/* Delta rows of the gold model — reach, cohort, timing, match keys */
create or replace temporary table delta_gold as (
    select g.*
    from ANALYTICS.PROD_LAVA.LAVA_TOURNAMENT_REDEMPTIONS g
    join delta_params p
      on p.tournament_id   = g.tournament_id
     and p.delta_reward_id = g.reward_id
);

/* Event-level Delta redemptions — day curve, location, ticket size.
   Test members excluded to match the gold model and the reward summary. */
create or replace temporary table delta_redemptions as (
    select
        r.redemption_id,
        r.member_id,
        r.amount                                            as redeemed_amount,
        r.is_stored_value_usd,
        r.txn_id,
        t.location                                          as pos_location,
        t.integration_name,
        r.redeemed_at,
        convert_timezone('UTC', e.timezone, r.redeemed_at)  as redeemed_at_local
    from INTERMEDIATE.PROD_LAVA.INT_LAVA_REDEMPTIONS r
    cross join delta_event e
    join delta_params p on p.delta_reward_id = r.reward_id
    join INTERMEDIATE.PROD_LAVA.INT_LAVA_MEMBERS m
      on m.member_id = r.member_id and not m.is_test_member
    left join INTERMEDIATE.PROD_LAVA.INT_LAVA_TRANSACTIONS t on t.txn_id = r.txn_id
    where r.member_id is not null
      and not r.is_test_reward
      and convert_timezone('UTC', e.timezone, r.redeemed_at)::date
          between e.window_start_date and e.window_end_date
);

/* Delta baskets — one row per non-void POS transaction that used the credit.
   cash_spend_usd     = TOTAL_SPENT as recorded: the fan's own money. For these
                        transactions the credit is NOT in it (TXN.REDEEMED_AMOUNT is 0
                        and 267 of 1,327 baskets are smaller than the credit applied).
   basket_credit_usd  = stored-value $ drawn down in the whole basket (any reward)
   gross_spend_usd    = cash + basket credit: what the fan actually bought
   credit_applied_usd = Delta $ only (the denominator for ROI) */
create or replace temporary table delta_baskets as (
    with basket_credit as (
        select txn_id, sum(amount) as credit_usd
        from INTERMEDIATE.PROD_LAVA.INT_LAVA_REDEMPTIONS
        where is_stored_value_usd and txn_id is not null
        group by 1
    )
    select
        t.txn_id,
        t.member_id,
        t.integration_name,
        t.location                                          as pos_location,
        convert_timezone('UTC', e.timezone, t.txn_at)       as txn_at_local,
        t.total_spent_usd                                   as cash_spend_usd,
        case when coalesce(t.redeemed_usd, 0) > 0 then 0
             else coalesce(bc.credit_usd, 0) end            as basket_credit_usd,
        t.total_spent_usd
          + case when coalesce(t.redeemed_usd, 0) > 0 then 0
                 else coalesce(bc.credit_usd, 0) end        as gross_spend_usd,
        sum(case when r.is_stored_value_usd then r.redeemed_amount end) as credit_applied_usd,
        count(distinct r.redemption_id)                     as redemptions
    from delta_redemptions r
    cross join delta_event e
    join INTERMEDIATE.PROD_LAVA.INT_LAVA_TRANSACTIONS t on t.txn_id = r.txn_id
    left join basket_credit bc on bc.txn_id = t.txn_id
    where not t.is_void
      and not t.is_test_integration
    group by all
);

/* Delta grants — distribution side. Cancelled, test and test-member rows out. */
create or replace temporary table delta_grants as (
    select
        g.member_id,
        g.amount                                            as granted_amount,
        g.is_manual_grant,
        g.is_stored_value_usd,
        g.granted_at,
        convert_timezone('UTC', e.timezone, g.granted_at)   as granted_at_local
    from INTERMEDIATE.PROD_LAVA.INT_LAVA_GRANTS g
    cross join delta_event e
    join delta_params p on p.delta_reward_id = g.reward_id
    join INTERMEDIATE.PROD_LAVA.INT_LAVA_MEMBERS m
      on m.member_id = g.member_id and not m.is_test_member
    where not g.is_cancelled
      and not g.is_test_reward
);


/* =================================== §1 ==================================
   SCORECARD — the one-row answer
   ========================================================================= */
-- 1a. Straight from the governed reward summary.
select
    s.reward_name,
    s.unique_members_granted                                        as fans_granted,
    s.unique_redeemers                                              as fans_redeemed,
    round(100 * s.redeemer_rate_of_granted, 1)                      as activation_pct,
    s.total_redemptions                                             as redemptions,
    s.redemptions_per_redeemer,
    round(s.granted_usd, 2)                                         as credit_granted_usd,
    round(s.redeemed_usd, 2)                                        as credit_redeemed_usd,
    round(100 * div0(s.redeemed_usd, s.granted_usd), 1)             as pct_of_credit_used,
    round(s.total_spend_usd, 2)                                     as gross_basket_value_usd,
    round(s.total_cash_spend_usd, 2)                                as fan_cash_spend_usd,
    s.spend_txn_count                                               as baskets,
    round(s.avg_txn_spend_usd, 2)                                   as avg_gross_basket_usd,
    round(div0(s.total_spend_usd, s.redeemed_usd), 2)               as gross_spend_per_credit_dollar,
    round(div0(s.total_cash_spend_usd, s.redeemed_usd), 2)          as fan_cash_per_credit_dollar,
    round(100 * s.pct_redemptions_in_tournament_window, 1)          as pct_redemptions_in_event_week,
    s.tournament_windows_with_redemptions                           as event_windows_used,
    s.first_redeemed_at,
    s.last_redeemed_at
from ANALYTICS.PROD_LAVA.LAVA_REWARD_SUMMARY s
join delta_params p on p.delta_reward_id = s.reward_id;

-- 1b. Reconciliation: reward summary (all time) vs the event working sets.
--     Redemptions, fans and credit should match; fans_granted can differ slightly
--     where a member was granted outside the lookup window. event_windows_used = 1
--     above means the reward only ever ran at this tournament.
select
    s.total_redemptions                                             as summary_redemptions,
    (select sum(redemption_count) from delta_gold)                  as event_redemptions,
    s.unique_redeemers                                              as summary_fans_redeemed,
    (select count(distinct member_id) from delta_gold)              as event_fans_redeemed,
    round(s.redeemed_usd, 2)                                        as summary_credit_usd,
    (select round(sum(redeemed_usd), 2) from delta_gold)            as event_credit_usd,
    s.unique_members_granted                                        as summary_fans_granted,
    (select count(distinct member_id) from delta_grants)            as event_fans_granted,
    s.spend_txn_count                                               as summary_baskets,
    (select count(*) from delta_baskets)                            as event_baskets
from ANALYTICS.PROD_LAVA.LAVA_REWARD_SUMMARY s
join delta_params p on p.delta_reward_id = s.reward_id;


/* =================================== §2 ==================================
   BENCHMARK — Delta vs. every stored-value reward
   Read like-for-like: fan-facing rewards only. Rewards with a handful of
   grants but thousands of redeemers (e.g. Fan Cash) are issued through a shared
   or preset balance, so their activation rate is not meaningful — compare them
   on spend and redemptions per fan instead.
   ========================================================================= */
select
    s.reward_id,
    s.reward_name,
    case when s.reward_name ilike any ('%volunteer%', '%staff%', '%leadership%')
              or s.reward_slug ilike any ('%volunteer%', '%staff%')
         then 'staff / volunteer' else 'fan-facing' end             as audience,
    (s.reward_id = p.delta_reward_id)                               as is_delta,
    s.unique_members_granted                                        as fans_granted,
    s.unique_redeemers                                              as fans_redeemed,
    round(100 * s.redeemer_rate_of_granted, 1)                      as activation_pct,
    s.total_redemptions                                             as redemptions,
    s.redemptions_per_redeemer,
    round(s.granted_usd, 0)                                         as credit_granted_usd,
    round(s.redeemed_usd, 0)                                        as credit_redeemed_usd,
    round(100 * div0(s.redeemed_usd, nullif(s.granted_usd, 0)), 1)  as pct_of_credit_used,
    round(s.total_spend_usd, 0)                                     as gross_basket_value_usd,
    round(s.total_cash_spend_usd, 0)                                as fan_cash_spend_usd,
    round(s.avg_txn_spend_usd, 2)                                   as avg_gross_basket_usd,
    round(div0(s.total_spend_usd, nullif(s.redeemed_usd, 0)), 2)    as gross_spend_per_credit_dollar,
    round(div0(s.total_cash_spend_usd, nullif(s.redeemed_usd, 0)), 2) as fan_cash_per_credit_dollar,
    s.tournament_windows_with_redemptions                           as event_windows_used
from ANALYTICS.PROD_LAVA.LAVA_REWARD_SUMMARY s
cross join delta_params p
where s.reward_type = 'Stored Value'
  and s.amount_type = 'currency'
  and s.total_redemptions > 0
order by is_delta desc, audience, fans_redeemed desc;


/* =================================== §3 ==================================
   SPEND & ROI — did the $5 bring spend with it?
   ========================================================================= */
-- 3a. Headline spend on Delta baskets.
select
    count(*)                                                        as baskets,
    count(distinct member_id)                                       as fans,
    round(sum(credit_applied_usd), 2)                               as delta_credit_applied_usd,
    round(sum(gross_spend_usd), 2)                                  as gross_basket_value_usd,
    round(sum(cash_spend_usd), 2)                                   as fan_cash_spend_usd,
    round(avg(gross_spend_usd), 2)                                  as avg_gross_basket_usd,
    round(median(gross_spend_usd), 2)                               as median_gross_basket_usd,
    round(avg(cash_spend_usd), 2)                                   as avg_cash_spend_usd,
    round(sum(gross_spend_usd) / nullif(sum(credit_applied_usd), 0), 2) as gross_spend_per_credit_dollar,
    round(sum(cash_spend_usd) / nullif(sum(credit_applied_usd), 0), 2) as fan_cash_per_credit_dollar,
    round(100.0 * count_if(cash_spend_usd > 0) / nullif(count(*), 0), 1) as pct_baskets_with_own_money,
    round(100.0 * count_if(cash_spend_usd = 0) / nullif(count(*), 0), 1) as pct_baskets_fully_covered
from delta_baskets;

-- 3b. Fan cash per basket. $0 = the credit covered the whole basket; everything
--     above it is the fan choosing to spend their own money on top of the $5.
select
    case
        when cash_spend_usd = 0     then '1. $0 (credit covered it)'
        when cash_spend_usd <= 5    then '2. up to $5'
        when cash_spend_usd <= 10   then '3. $5 - $10'
        when cash_spend_usd <= 20   then '4. $10 - $20'
        when cash_spend_usd <= 50   then '5. $20 - $50'
        else                             '6. over $50'
    end                                                             as fan_cash_band,
    count(*)                                                        as baskets,
    count(distinct member_id)                                       as fans,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as pct_of_baskets,
    round(sum(cash_spend_usd), 2)                                   as fan_cash_spend_usd,
    round(100.0 * sum(cash_spend_usd) / nullif(sum(sum(cash_spend_usd)) over (), 0), 1) as pct_of_fan_cash,
    round(avg(credit_applied_usd), 2)                               as avg_delta_credit_applied_usd
from delta_baskets
group by 1
order by 1;

-- 3c. Spend by Pass-signup cohort.
select
    g.pass_signup_timing,
    count(distinct b.member_id)                                     as fans,
    count(*)                                                        as baskets,
    round(sum(b.gross_spend_usd), 2)                                as gross_basket_value_usd,
    round(avg(b.gross_spend_usd), 2)                                as avg_gross_basket_usd,
    round(sum(b.cash_spend_usd), 2)                                 as fan_cash_spend_usd,
    round(sum(b.cash_spend_usd) / nullif(sum(b.credit_applied_usd), 0), 2) as fan_cash_per_credit_dollar
from delta_baskets b
join delta_gold g on g.member_id = b.member_id
group by 1
order by fans desc;

-- 3d. Same tournament, same Lava POS: Delta baskets vs. other fan-facing
--     rewards vs. staff / volunteer rewards (mostly $0 meal vouchers) vs. no
--     reward at all. Directional only — perk users self-select, and the
--     no-reward group is small. Gross = cash + credit, same rule as delta_baskets.
with basket_credit as (
    select txn_id, sum(amount) as credit_usd
    from INTERMEDIATE.PROD_LAVA.INT_LAVA_REDEMPTIONS
    where is_stored_value_usd and txn_id is not null
    group by 1
),
window_txns as (
    select
        t.txn_id,
        t.member_id,
        t.total_spent_usd                                           as cash_spend_usd,
        t.total_spent_usd
          + case when coalesce(t.redeemed_usd, 0) > 0 then 0
                 else coalesce(bc.credit_usd, 0) end                as gross_spend_usd
    from INTERMEDIATE.PROD_LAVA.INT_LAVA_TRANSACTIONS t
    cross join delta_event e
    left join basket_credit bc on bc.txn_id = t.txn_id
    where not t.is_void
      and not t.is_test_integration
      and convert_timezone('UTC', e.timezone, t.txn_at)::date
          between e.window_start_date and e.window_end_date
),
other_reward_txns as (
    select
        r.txn_id,
        max(case when rw.reward_name ilike any ('%volunteer%', '%staff%', '%leadership%')
                 then 0 else 1 end)                                 as has_fan_facing_reward
    from INTERMEDIATE.PROD_LAVA.INT_LAVA_REDEMPTIONS r
    join INTERMEDIATE.PROD_LAVA.INT_LAVA_REWARDS rw on rw.reward_id = r.reward_id
    where not r.is_test_reward
      and r.reward_id <> (select delta_reward_id from delta_params)
      and r.txn_id is not null
    group by 1
)
select
    case
        when b.txn_id is not null               then '1. Delta credit used'
        when o.has_fan_facing_reward = 1        then '2. Other fan-facing reward used'
        when o.txn_id is not null               then '3. Staff / volunteer reward'
        else                                         '4. No reward'
    end                                                             as basket_type,
    count(*)                                                        as baskets,
    count(distinct w.member_id)                                     as fans,
    round(avg(w.gross_spend_usd), 2)                                as avg_gross_basket_usd,
    round(median(w.gross_spend_usd), 2)                             as median_gross_basket_usd,
    round(avg(w.cash_spend_usd), 2)                                 as avg_cash_spend_usd,
    round(median(w.cash_spend_usd), 2)                              as median_cash_spend_usd,
    round(sum(w.gross_spend_usd), 0)                                as gross_basket_value_usd,
    round(sum(w.cash_spend_usd), 0)                                 as fan_cash_spend_usd
from window_txns w
left join delta_baskets b on b.txn_id = w.txn_id
left join other_reward_txns o on o.txn_id = w.txn_id
group by 1
order by 1;
-- A basket holding Delta and another reward is labelled Delta (first match wins).


/* =================================== §4 ==================================
   WHO — Pass signup timing, ticketing, adoption
   ========================================================================= */
-- 4a. Headline split by how the fan relates to TOUR Pass.
select '1. Fans granted the $5 Delta credit'                     as metric,
       count(*)                                                   as events,
       count(distinct member_id)                                  as fans
from delta_grants
union all
select '2. Fans who redeemed it at TOUR Championship',
       sum(redemption_count), count(distinct member_id)
from delta_gold
union all
select '3. ...who registered for TOUR Pass during this event',
       sum(redemption_count), count(distinct member_id)
from delta_gold
where pass_signup_timing in ('in the moment (competition days)', 'event week, before first round')
union all
select '4. ...who registered in the 30 days leading up to it',
       sum(redemption_count), count(distinct member_id)
from delta_gold
where pass_signup_timing = 'lead-up (30 days prior)'
union all
select '5. ...who were already Pass members',
       sum(redemption_count), count(distinct member_id)
from delta_gold
where pass_signup_timing = 'pre-existing member'
union all
select '6. ...with no Gigya / Pass record at all',
       sum(redemption_count), count(distinct member_id)
from delta_gold
where pass_signup_timing = 'no pass record'
order by metric;

-- 4b. Signup timing — did Pass registration happen before they arrived, or
--     standing at the tent?
select
    g.pass_signup_timing,
    count(distinct g.member_id)                                     as fans,
    round(100.0 * count(distinct g.member_id)
                / sum(count(distinct g.member_id)) over (), 1)      as pct_of_fans,
    sum(g.redemption_count)                                         as redemptions,
    round(sum(g.redeemed_usd), 2)                                   as value_redeemed_usd
from delta_gold g
group by 1
order by fans desc;

-- 4c. Fans who registered during event week: which day, and did they redeem the
--     same day? Same-day is the strongest evidence of an onsite signup driven
--     by the offer itself.
select
    g.tour_pass_signup_date                                         as pass_signup_day,
    dayname(g.tour_pass_signup_date)                                as dow,
    count(distinct g.member_id)                                     as fans,
    count(distinct case when g.first_redeemed_local_date = g.tour_pass_signup_date
                        then g.member_id end)                       as redeemed_same_day,
    round(100.0 * count(distinct case when g.first_redeemed_local_date = g.tour_pass_signup_date
                                      then g.member_id end)
                / nullif(count(distinct g.member_id), 0), 1)        as pct_same_day
from delta_gold g
where g.tour_pass_signup_date between g.official_start_date - 6 and g.official_end_date
group by 1, 2
order by 1;

-- 4d. Lag between Pass signup and first Delta redemption.
select
    case
        when g.tour_pass_signup_date is null then 'no pass record'
        when datediff('day', g.tour_pass_signup_date, g.first_redeemed_local_date) = 0 then 'same day'
        when datediff('day', g.tour_pass_signup_date, g.first_redeemed_local_date) <= 7 then 'within a week'
        when datediff('day', g.tour_pass_signup_date, g.first_redeemed_local_date) <= 90 then 'within 90 days'
        when datediff('day', g.tour_pass_signup_date, g.first_redeemed_local_date) <= 365 then 'within a year'
        else 'over a year'
    end                                                             as signup_to_redemption_lag,
    count(distinct g.member_id)                                     as fans
from delta_gold g
group by 1
order by fans desc;

-- 4e. Offered vs. redeemed, Pass members vs. everyone. Uses the existing Pass
--     view; "offered" = held a live grant during the event week.
select
    v.reward_name,
    v.members_offered,
    v.members_redeemed,
    round(100 * v.redemption_rate, 1)                               as redemption_rate_pct,
    v.tour_pass_offered,
    v.tour_pass_redeemed,
    round(100 * v.tour_pass_redemption_rate, 1)                     as tour_pass_redemption_rate_pct
from ANALYTICS.PROD_TOUR_PASS.TOUR_PASS_LAVA_REWARD_REDEMPTION_STREAMLIT v
join delta_params p
  on p.tournament_id   = v.tournament_id
 and p.delta_reward_id = v.reward_id;

-- 4f. Are ticket holders adopting Pass and using it onsite?
select
    g.is_ticketholder,
    g.has_tm_account_resolved,
    g.best_match_key,
    count(distinct g.member_id)                                     as fans,
    sum(g.redemption_count)                                         as redemptions
from delta_gold g
group by 1, 2, 3
order by fans desc;

-- 4g. Same cut for every TOUR Championship redeemer — the baseline for 4f.
select
    g.is_ticketholder,
    g.has_tm_account_resolved,
    g.best_match_key,
    count(distinct g.member_id)                                     as fans
from ANALYTICS.PROD_LAVA.LAVA_TOURNAMENT_REDEMPTIONS g
join delta_params p on p.tournament_id = g.tournament_id
group by 1, 2, 3
order by fans desc;

-- 4h. Does Pass create known records that ticketing alone would not have?
select
    case
        when g.is_tour_pass_member and not g.has_tm_account_resolved
            then 'pass only — incremental 1P record'
        when g.is_tour_pass_member and g.has_tm_account_resolved
            then 'pass + ticketing account'
        when not g.is_tour_pass_member and g.has_tm_account_resolved
            then 'ticketing only — no pass'
        else 'neither — unmatchable'
    end                                                             as record_type,
    count(distinct g.member_id)                                     as fans,
    round(100.0 * count(distinct g.member_id)
                / sum(count(distinct g.member_id)) over (), 1)      as pct_of_fans
from delta_gold g
group by 1
order by fans desc;

-- 4i. Where the cohort stands today. 'rewarded_only' = the $5 was the whole
--     relationship; 'transacted' = they spent their own money, at any time.
select
    u.lifecycle_stage,
    u.is_known_record,
    count(distinct g.member_id)                                     as fans,
    round(avg(u.pass_tenure_days), 0)                               as avg_pass_tenure_days,
    round(avg(u.total_spend_usd), 2)                                as avg_lifetime_spend_usd
from delta_gold g
join ANALYTICS.PROD_LAVA.LAVA_USER_SUMMARY u on u.member_id = g.member_id
group by 1, 2
order by fans desc;


/* =================================== §5 ==================================
   DAY CURVE — redemptions and spend by tournament day
   ========================================================================= */
with redeem as (
    select
        r.redeemed_at_local::date                                   as tournament_day,
        count(*)                                                    as redemptions,
        count(distinct r.member_id)                                 as unique_fans,
        round(sum(case when r.is_stored_value_usd then r.redeemed_amount end), 2) as credit_redeemed_usd
    from delta_redemptions r
    group by 1
),
spend as (
    select
        b.txn_at_local::date                                        as tournament_day,
        count(*)                                                    as baskets,
        round(sum(b.gross_spend_usd), 2)                            as gross_basket_value_usd,
        round(sum(b.cash_spend_usd), 2)                             as fan_cash_spend_usd
    from delta_baskets b
    group by 1
)
select
    r.tournament_day,
    dayname(r.tournament_day)                                       as dow,
    r.redemptions,
    r.unique_fans,
    r.credit_redeemed_usd,
    s.baskets,
    s.gross_basket_value_usd,
    s.fan_cash_spend_usd,
    round(s.gross_basket_value_usd / nullif(s.baskets, 0), 2)       as avg_gross_basket_usd
from redeem r
left join spend s on s.tournament_day = r.tournament_day
order by 1;


/* =================================== §6 ==================================
   LOCATIONS — Square location IDs; VENUE_ABBR is blank on every
   INTEGRATION_DEFINITIONS row, so map these from the venue build sheet.
   ========================================================================= */
select
    r.pos_location,
    r.integration_name,
    count(*)                                                        as redemptions,
    count(distinct r.member_id)                                     as unique_fans,
    round(sum(case when r.is_stored_value_usd then r.redeemed_amount end), 2) as credit_redeemed_usd,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as pct_of_redemptions,
    max(b.gross_spend_usd)                                          as max_gross_basket_usd
from delta_redemptions r
left join delta_baskets b on b.txn_id = r.txn_id
group by 1, 2
order by redemptions desc;


/* =================================== §7 ==================================
   GRANT TIMING — was the credit delivered before the event or at it?
   Each fan is bucketed on their FIRST Delta grant.
   ========================================================================= */
with first_grant as (
    select
        g.member_id,
        min(g.granted_at_local)::date                               as first_grant_date
    from delta_grants g
    where g.granted_amount > 0
    group by 1
)
select
    case
        when f.first_grant_date < e.window_start_date              then '1. before event week'
        when f.first_grant_date < e.official_start_date            then '2. event week, before first round'
        when f.first_grant_date <= e.official_end_date             then '3. during competition days'
        else                                                            '4. after the event'
    end                                                             as grant_timing,
    count(*)                                                        as fans_granted,
    count(d.member_id)                                              as fans_redeemed,
    round(100.0 * count(d.member_id) / nullif(count(*), 0), 1)      as activation_pct
from first_grant f
cross join delta_event e
left join (select distinct member_id from delta_gold) d on d.member_id = f.member_id
group by 1
order by 1;


/* =================================== §8 ==================================
   TICKET SIZE — confirms the $5 face value, surfaces partial spends
   ========================================================================= */
select
    r.redeemed_amount,
    count(*)                                                        as redemptions,
    count(distinct r.member_id)                                     as unique_fans,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as pct_of_redemptions
from delta_redemptions r
where r.is_stored_value_usd
group by 1
order by redemptions desc;


/* =================================== §9 ==================================
   BASKET OF REWARDS — what else the Delta cohort used at this tournament
   ========================================================================= */
-- 9a. Every reward the Delta cohort touched
with delta_fans as (
    select distinct member_id from delta_gold
)
select
    g.reward_id,
    g.reward_name,
    g.reward_type,
    count(distinct g.member_id)                                     as unique_fans,
    sum(g.redemption_count)                                         as redemptions,
    round(sum(g.redeemed_usd), 2)                                   as value_redeemed_usd
from ANALYTICS.PROD_LAVA.LAVA_TOURNAMENT_REDEMPTIONS g
join delta_params p on p.tournament_id = g.tournament_id
join delta_fans f   on f.member_id     = g.member_id
group by 1, 2, 3
order by unique_fans desc;

-- 9b. How many rewards deep did they go?
select
    g.rewards_used_in_tournament,
    count(distinct g.member_id)                                     as fans
from delta_gold g
group by 1
order by 1;


/* =================================== §10 =================================
   LEAKAGE — granted the credit, never used it here
   The remarketing list, and the denominator behind the activation rate.
   ========================================================================= */
select
    case when m.is_tour_pass_member then 'pass member' else 'no pass record' end as pass_status,
    m.member_source,
    m.is_ticketholder,
    count(distinct g.member_id)                                     as granted_but_unspent,
    round(sum(case when g.is_stored_value_usd then g.granted_amount end), 2) as unspent_face_value_usd
from delta_grants g
join INTERMEDIATE.PROD_LAVA.INT_LAVA_MEMBERS m on m.member_id = g.member_id
where g.member_id not in (select distinct member_id from delta_gold)
group by 1, 2, 3
order by granted_but_unspent desc;


/* =================================== §11 =================================
   DATA QUALITY
   ========================================================================= */
-- 11a. Grant amounts. Reward 43 is a $5 credit, but manual grants carry other
--      values and ISSUED_GRANTS holds negative rows warehouse-wide.
select
    g.granted_amount,
    g.is_manual_grant,
    count(*)                                                        as grants,
    count(distinct g.member_id)                                     as unique_fans,
    case when g.granted_amount = 5  then 'standard $5 grant'
         when g.granted_amount < 0  then 'correction / clawback'
         else 'manual or off-value grant' end                       as grant_class
from delta_grants g
group by 1, 2
order by grants desc;

-- 11b. Match quality. Duplicate Gigya accounts or Archtics rows on one email mean
--      int_lava_tour_pass_identity picked one. Non-zero is worth a look before
--      any Pass-attribution number is quoted externally.
select
    count(distinct case when m.has_ambiguous_gigya_match then g.member_id end) as fans_ambiguous_gigya,
    count(distinct case when m.has_ambiguous_tm_match    then g.member_id end) as fans_ambiguous_tm,
    count(distinct g.member_id)                                                as fans_total
from delta_gold g
join INTERMEDIATE.PROD_LAVA.INT_LAVA_MEMBERS m on m.member_id = g.member_id;

-- 11c. Pass coverage of this cohort. A high 'no pass record' count would mean the
--      email join is failing rather than that fans lack a Pass.
select
    g.has_email,
    (g.av_id is not null)                                           as has_av_id,
    g.is_tour_pass_member,
    count(distinct g.member_id)                                     as fans
from delta_gold g
group by 1, 2, 3
order by fans desc;

-- 11d. Baskets we could not price: redemptions whose transaction is missing,
--      void, or from a test integration. They count as redemptions but carry no
--      spend, so a large number here understates §3.
select
    count(*)                                                        as redemptions,
    count_if(b.txn_id is null)                                      as redemptions_without_priced_basket,
    round(100.0 * count_if(b.txn_id is null) / nullif(count(*), 0), 1) as pct_unpriced
from delta_redemptions r
left join (select distinct txn_id from delta_baskets) b on b.txn_id = r.txn_id;
