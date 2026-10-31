-- Global and UTC week-local paths use strictly increasing timestamps. A transaction ID
-- must belong to one visitor per scope; the runner rejects violations explicitly.
CREATE OR REPLACE TEMP TABLE metric_tree_base AS
WITH scoped AS (
 SELECT 'all' AS scope, NULL::DATE AS week_start, * FROM events
 UNION ALL
 SELECT 'week', event_week, * FROM events
), visitor AS (
 SELECT scope,week_start,visitor_id,
 min(ts_ms) FILTER (WHERE event_name='view') AS view_ms,
 count(DISTINCT transaction_id) FILTER (WHERE event_name='transaction') AS orders
 FROM scoped GROUP BY ALL
), carts AS (
 SELECT e.scope,e.week_start,e.visitor_id,min(e.ts_ms) AS cart_ms
 FROM scoped e JOIN visitor v ON e.scope=v.scope AND e.week_start IS NOT DISTINCT FROM v.week_start AND e.visitor_id=v.visitor_id
 WHERE e.event_name='addtocart' AND e.ts_ms>v.view_ms GROUP BY ALL
), buys AS (
 SELECT e.scope,e.week_start,e.visitor_id,min(e.ts_ms) AS buy_ms
 FROM scoped e JOIN carts c ON e.scope=c.scope AND e.week_start IS NOT DISTINCT FROM c.week_start AND e.visitor_id=c.visitor_id
 WHERE e.event_name='transaction' AND e.ts_ms>c.cart_ms GROUP BY ALL
), counts AS (
 SELECT v.scope,v.week_start,count(*) FILTER(WHERE v.view_ms IS NOT NULL) AS viewers,
 count(*) FILTER(WHERE c.cart_ms IS NOT NULL) AS cart_visitors,
 count(*) FILTER(WHERE b.buy_ms IS NOT NULL) AS strict_buyers,
 count(*) FILTER(WHERE v.orders>0) AS buyers,
 count(*) FILTER(WHERE v.orders=1) AS single_buyers,
 count(*) FILTER(WHERE v.orders>1) AS repeat_buyers,
 coalesce(sum(v.orders) FILTER(WHERE v.orders>1),0) AS repeat_orders,
 coalesce(sum(v.orders),0) AS orders
 FROM visitor v LEFT JOIN carts c ON v.scope=c.scope AND v.week_start IS NOT DISTINCT FROM c.week_start AND v.visitor_id=c.visitor_id
 LEFT JOIN buys b ON v.scope=b.scope AND v.week_start IS NOT DISTINCT FROM b.week_start AND v.visitor_id=b.visitor_id GROUP BY ALL
), rates AS (
 SELECT *,buyers-strict_buyers AS other_buyers,
 coalesce(cart_visitors::DOUBLE/nullif(viewers,0),0) AS cart_rate,
 coalesce(strict_buyers::DOUBLE/nullif(cart_visitors,0),0) AS purchase_rate,
 coalesce(orders::DOUBLE/nullif(buyers,0),0) AS orders_per_buyer,
 coalesce(repeat_buyers::DOUBLE/nullif(buyers,0),0) AS repeat_share,
 coalesce(repeat_orders::DOUBLE/nullif(repeat_buyers,0)-1,0) AS repeat_extra_orders
 FROM counts
)
SELECT *,buyers-(strict_buyers+other_buyers) AS buyer_reconciliation,
 orders-(single_buyers+repeat_orders) AS segment_reconciliation,
 orders-buyers*orders_per_buyer AS order_reconciliation,
 strict_buyers-viewers*cart_rate*purchase_rate AS funnel_reconciliation,
 CASE WHEN buyers>0 THEN orders_per_buyer-(1+repeat_share*repeat_extra_orders) ELSE 0 END AS frequency_reconciliation
FROM rates;

CREATE OR REPLACE TEMP TABLE metric_tree_weekly AS
WITH bounds AS (SELECT min(event_ts) AS first_ts,max(event_ts) AS last_ts FROM events),
 flags AS (
 SELECT m.*, (week_start >= first_ts AND week_start+INTERVAL 7 DAY <= last_ts) AS is_complete
 FROM metric_tree_base m CROSS JOIN bounds WHERE scope='week'
), prev AS (
 SELECT *,lag(week_start) OVER w AS previous_week,lag(is_complete) OVER w AS previous_complete,
 lag(viewers) OVER w AS pv,lag(cart_rate) OVER w AS pa,lag(purchase_rate) OVER w AS pb,
 lag(other_buyers) OVER w AS pn,lag(repeat_share) OVER w AS ps,lag(repeat_extra_orders) OVER w AS pf,
 lag(1+repeat_share*repeat_extra_orders) OVER w AS po,lag(orders) OVER w AS prior_orders
 FROM flags WINDOW w AS (ORDER BY week_start)
), eligible AS (
 SELECT *,is_complete AND previous_complete AND week_start=previous_week+INTERVAL 7 DAY AS comparable FROM prev
), effects AS (
 SELECT *, CASE WHEN comparable THEN orders-prior_orders END AS order_change,
 CASE WHEN comparable THEN (viewers-pv)*pa*pb*po END AS traffic_effect,
 CASE WHEN comparable THEN viewers*(cart_rate-pa)*pb*po END AS cart_rate_effect,
 CASE WHEN comparable THEN viewers*cart_rate*(purchase_rate-pb)*po END AS purchase_rate_effect,
 CASE WHEN comparable THEN (other_buyers-pn)*po END AS other_buyer_effect,
 CASE WHEN comparable THEN buyers*(repeat_share-ps)*pf END AS repeat_share_effect,
 CASE WHEN comparable THEN buyers*repeat_share*(repeat_extra_orders-pf) END AS repeat_frequency_effect
 FROM eligible
)
SELECT *,order_change-(traffic_effect+cart_rate_effect+purchase_rate_effect+other_buyer_effect+repeat_share_effect+repeat_frequency_effect) AS decomposition_reconciliation FROM effects;
SELECT * EXCLUDE(scope,week_start) FROM metric_tree_base WHERE scope='all';
