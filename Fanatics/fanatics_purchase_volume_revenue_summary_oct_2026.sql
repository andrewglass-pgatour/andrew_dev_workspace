/* ============================================================================
   FANATICS — PURCHASE VOLUME & REVENUE SUMMARY
   Breakouts: by year, month_year, US vs. INTL, and INTL country.
   ----------------------------------------------------------------------------
   SOURCE: PGAT.FANATICS.PURCHASE_DATA (raw; one row = one order LINE).
   Same client_email-not-null filter as INT_PURCHASE_DATA.

   GRAIN / REVENUE DEFINITIONS
     Order-level amounts (ORDER_NET_TOTAL, ORDER_SHIP_TOTAL, ORDER_TAX_TOTAL,
     ORDER_DISCOUNT_TOTAL) repeat on every line of an order, so they are
     collapsed to one row per order BEFORE summing. Summing them off the line
     table would overcount multi-item orders.
       order_net_revenue  = ORDER_NET_TOTAL (same measure the dbt models use
                            for total spend)
       line_revenue       = QTY_SOLD * UNIT_PRICE, summed over lines (item
                            merchandise value, before order-level discount/
                            shipping/tax) — the same definition as
                            ORDER_LINE_SPEND in INT_PURCHASE_DATA
     The two will not match: net total includes shipping/tax/discounts. Check
     the reconciliation in §1d before quoting either.
   ============================================================================ */


/* =================================== §0 ==================================
   WORKING SETS
   ========================================================================= */
/* One row per order line, with a parsed order date */
create or replace temporary table fanatics_lines as (
    select
        r.order_id,
        r.client_email,
        r.order_date::date                                  as order_dt, -- ORDER_DATE is already TIMESTAMP_NTZ
        r.qty_sold,
        r.qty_sold * r.unit_price                           as line_revenue,
        r.order_net_total,
        r.order_ship_total,
        r.order_tax_total,
        r.order_discount_total,
        r.ship_address_country,
        r.ship_address_state,
        r.ship_address_zip
    from PGAT.FANATICS.PURCHASE_DATA r
    where r.client_email is not null
);

/* One row per order. Order-level fields are constant within an order; max()
   just picks the repeated value. */
create or replace temporary table fanatics_orders as (
    select
        order_id,
        max(order_dt)                                       as order_dt,
        max(client_email)                                   as client_email,
        count(*)                                            as line_items,
        sum(qty_sold)                                       as units,
        sum(line_revenue)                                   as line_revenue,
        max(order_net_total)                                as order_net_total,
        max(order_ship_total)                               as order_ship_total,
        max(order_tax_total)                                as order_tax_total,
        max(order_discount_total)                           as order_discount_total,
        max(ship_address_country)                           as ship_address_country,
        max(ship_address_state)                             as ship_address_state,
        max(ship_address_zip)                                as ship_address_zip
    from fanatics_lines
    group by order_id
);


/* =================================== §1 ==================================
   CHECKS
   ========================================================================= */
-- 1a. Dates that failed to parse would silently drop out of the breakouts.
select
    count(*)                                                as orders,
    count_if(order_dt is null)                              as orders_without_valid_date,
    min(order_dt)                                           as first_order_date,
    max(order_dt)                                           as last_order_date
from fanatics_orders;

-- 1b. Order-level fields should be constant within an order. Non-zero means
--     the max() in fanatics_orders is hiding conflicting values.
select
    count(*)                                                as orders_with_conflicting_net_total
from (
    select order_id
    from fanatics_lines
    group by order_id
    having count(distinct order_net_total) > 1
);

-- 1c. Shipping geography should be constant within each order.
select
    count(*)                                                as orders_with_conflicting_shipping_geography
from (
    select order_id
    from fanatics_lines
    group by order_id
    having count(distinct nullif(upper(trim(ship_address_country)), '')) > 1
        or count(distinct nullif(upper(trim(ship_address_state)), '')) > 1
        or count(distinct nullif(trim(ship_address_zip), '')) > 1
);

-- 1d. All-time totals — the reconciliation row for the breakouts below.
select
    count(*)                                                as orders,
    count(distinct client_email)                            as customers,
    sum(line_items)                                         as line_items,
    sum(units)                                              as units,
    round(sum(line_revenue), 2)                             as line_revenue_usd,
    round(sum(order_net_total), 2)                          as order_net_revenue_usd
from fanatics_orders;


/* =================================== §2 ==================================
   BY YEAR
   ========================================================================= */
select
    year(order_dt)                                          as order_year,
    count(*)                                                as orders,
    count(distinct client_email)                            as customers,
    sum(line_items)                                         as line_items,
    sum(units)                                              as units,
    round(sum(line_revenue), 2)                             as line_revenue_usd,
    round(sum(order_net_total), 2)                          as order_net_revenue_usd,
    round(sum(order_ship_total), 2)                         as shipping_usd,
    round(sum(order_tax_total), 2)                          as tax_usd,
    round(sum(order_discount_total), 2)                     as discounts_usd,
    round(sum(order_net_total) / nullif(count(*), 0), 2)    as avg_order_value_usd,
    round(sum(units) / nullif(count(*), 0), 2)              as units_per_order,
    round(sum(order_net_total) / nullif(count(distinct client_email), 0), 2) as revenue_per_customer_usd,
    round(100.0 * (sum(order_net_total) / nullif(lag(sum(order_net_total)) over (order by year(order_dt)), 0) - 1), 1) as net_revenue_yoy_pct
from fanatics_orders
where order_dt is not null
group by 1
order by 1;


/* =================================== §3 ==================================
   BY MONTH_YEAR
   ========================================================================= */
select
    to_char(date_trunc('month', order_dt), 'YYYY-MM')       as month_year,
    year(order_dt)                                          as order_year,
    monthname(order_dt)                                     as order_month,
    count(*)                                                as orders,
    count(distinct client_email)                            as customers,
    sum(line_items)                                         as line_items,
    sum(units)                                              as units,
    round(sum(line_revenue), 2)                             as line_revenue_usd,
    round(sum(order_net_total), 2)                          as order_net_revenue_usd,
    round(sum(order_ship_total), 2)                         as shipping_usd,
    round(sum(order_tax_total), 2)                          as tax_usd,
    round(sum(order_discount_total), 2)                     as discounts_usd,
    round(sum(order_net_total) / nullif(count(*), 0), 2)    as avg_order_value_usd,
    round(sum(units) / nullif(count(*), 0), 2)              as units_per_order
from fanatics_orders
where order_dt is not null
group by 1, 2, 3, date_trunc('month', order_dt)
order by date_trunc('month', order_dt);


/* =================================== §4 ==================================
   VALIDATION vs. ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY
   That model is one row per personid x email with TOTAL_ORDERS and
   TOTAL_SPEND (= sum of ORDER_NET_TOTAL over distinct orders). It should
   tie to fanatics_orders above. Adjust the schema name if the view lives
   elsewhere (dbt_project.yml puts it in database ANALYTICS, schema fanatics).
   Differences worth knowing before reading them as errors:
     - The model joins FANSOURCE on email; an email with two personids yields
       two rows, each counting the same order. §4b rolls up to email first so
       that shows as a difference in row count, not in the totals.
     - Orders whose lines carry different ORDER_NET_TOTAL values count twice
       in the model (see check 1b).
   ========================================================================= */
create or replace temporary table fanatics_summary_by_email as (
    select
        email                                               as client_email,
        count(*)                                            as model_rows,
        sum(total_orders)                                   as model_orders,
        sum(total_spend)                                    as model_spend
    from ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY
    group by email
);

-- 4a. Totals: this script vs. the model. All diffs should be 0.
select
    (select count(*) from fanatics_orders)                              as script_orders,
    (select sum(total_orders) from ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY) as model_orders,
    script_orders - model_orders                                        as orders_diff,
    (select round(sum(order_net_total), 2) from fanatics_orders)        as script_net_revenue,
    (select round(sum(total_spend), 2) from ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY) as model_net_revenue,
    round(script_net_revenue - model_net_revenue, 2)                    as revenue_diff,
    (select count(distinct client_email) from fanatics_orders)          as script_customers,
    (select count(distinct email) from ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY) as model_customers,
    (select count(*) from ANALYTICS.PROD_FANATICS.FANATICS_SUMMARY)     as model_rows;

-- 4b. Per-email comparison: counts of matches and each kind of mismatch.
with script_by_email as (
    select client_email,
           count(*)             as orders,
           sum(order_net_total) as spend
    from fanatics_orders
    group by client_email
)
select
    count_if(s.client_email is not null and m.client_email is not null
             and s.orders = m.model_orders
             and abs(s.spend - m.model_spend) < 0.01)                   as emails_matching,
    count_if(s.client_email is not null and m.client_email is not null
             and s.orders <> m.model_orders)                            as emails_order_count_differs,
    count_if(s.client_email is not null and m.client_email is not null
             and abs(s.spend - m.model_spend) >= 0.01)                  as emails_spend_differs,
    count_if(m.client_email is null)                                    as emails_missing_from_model,
    count_if(s.client_email is null)                                    as emails_only_in_model,
    count_if(m.model_rows > 1)                                          as emails_with_multiple_model_rows
from script_by_email s
full outer join fanatics_summary_by_email m on m.client_email = s.client_email;

-- 4c. The largest per-email differences, for investigation (empty = clean).
with script_by_email as (
    select client_email,
           count(*)             as orders,
           sum(order_net_total) as spend
    from fanatics_orders
    group by client_email
)
select
    coalesce(s.client_email, m.client_email)                            as client_email,
    s.orders                                                            as script_orders,
    m.model_orders,
    round(s.spend, 2)                                                   as script_spend,
    round(m.model_spend, 2)                                             as model_spend,
    round(coalesce(s.spend, 0) - coalesce(m.model_spend, 0), 2)         as spend_diff,
    m.model_rows
from script_by_email s
full outer join fanatics_summary_by_email m on m.client_email = s.client_email
where s.client_email is null
   or m.client_email is null
   or s.orders <> m.model_orders
   or abs(s.spend - m.model_spend) >= 0.01
order by abs(coalesce(s.spend, 0) - coalesce(m.model_spend, 0)) desc
limit 100;


/* =================================== §5 ==================================
   YEARLY REVENUE BY SHIPPING GEOGRAPHY
   All breakouts use orders with a valid order date. US is classified from the
   order's shipping country. Blank country values remain UNKNOWN rather than
   being counted as INTL. International country values are shown as supplied
   (uppercased/trimmed).
   ========================================================================= */
-- 5a. Annual US vs. INTL revenue; blank shipping country is UNKNOWN.
with classified_orders as (
    select
        year(order_dt) as order_year,
        case
            when upper(trim(ship_address_country)) in
                 ('US', 'USA', 'UNITED STATES', 'UNITED STATES OF AMERICA') then 'US'
            when nullif(trim(ship_address_country), '') is null then 'UNKNOWN'
            else 'INTL'
        end as geography,
        client_email,
        line_items,
        units,
        line_revenue,
        order_net_total
    from fanatics_orders
    where order_dt is not null
),
geography_rollup as (
    select
        order_year,
        geography,
        count(*) as orders,
        count(distinct client_email) as customers,
        sum(line_items) as line_items,
        sum(units) as units,
        sum(line_revenue) as line_revenue,
        sum(order_net_total) as order_net_revenue
    from classified_orders
    group by order_year, geography
),
all_revenue as (
    select
        order_year,
        sum(line_revenue) as total_line_revenue,
        sum(order_net_total) as total_order_net_revenue
    from classified_orders
    group by order_year
)
select
    g.order_year,
    g.geography,
    g.orders,
    g.customers,
    g.line_items,
    g.units,
    round(g.line_revenue, 2) as line_revenue_usd,
    round(g.order_net_revenue, 2) as order_net_revenue_usd,
    round(100.0 * g.line_revenue / nullif(a.total_line_revenue, 0), 1) as line_revenue_pct,
    round(100.0 * g.order_net_revenue / nullif(a.total_order_net_revenue, 0), 1) as order_net_revenue_pct
from geography_rollup g
join all_revenue a on a.order_year = g.order_year
order by g.order_year,
         case g.geography when 'US' then 1 when 'INTL' then 2 else 3 end;

-- 5b. Annual INTL revenue by shipping country. Country values are normalized
--     for display only; no country-code/name mapping is applied.
with intl_orders as (
    select
        year(order_dt) as order_year,
        coalesce(nullif(upper(trim(ship_address_country)), ''), 'UNKNOWN') as country,
        client_email,
        line_items,
        units,
        line_revenue,
        order_net_total
    from fanatics_orders
    where order_dt is not null
      and upper(trim(ship_address_country)) not in
          ('US', 'USA', 'UNITED STATES', 'UNITED STATES OF AMERICA')
      and nullif(trim(ship_address_country), '') is not null
),
country_rollup as (
    select
        order_year,
        country,
        count(*) as orders,
        count(distinct client_email) as customers,
        sum(line_items) as line_items,
        sum(units) as units,
        sum(line_revenue) as line_revenue,
        sum(order_net_total) as order_net_revenue
    from intl_orders
    group by order_year, country
),
intl_revenue as (
    select
        order_year,
        sum(line_revenue) as total_line_revenue,
        sum(order_net_total) as total_order_net_revenue
    from intl_orders
    group by order_year
)
select
    c.order_year,
    c.country,
    c.orders,
    c.customers,
    c.line_items,
    c.units,
    round(c.line_revenue, 2) as line_revenue_usd,
    round(c.order_net_revenue, 2) as order_net_revenue_usd,
    round(100.0 * c.line_revenue / nullif(i.total_line_revenue, 0), 1) as intl_line_revenue_pct,
    round(100.0 * c.order_net_revenue / nullif(i.total_order_net_revenue, 0), 1) as intl_order_net_revenue_pct
from country_rollup c
join intl_revenue i on i.order_year = c.order_year
order by c.order_year, c.order_net_revenue desc;
