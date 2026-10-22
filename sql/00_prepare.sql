-- Parse once; retain raw input for quality checks. Exact-row duplicates are removed.
CREATE OR REPLACE TABLE parsed AS
SELECT row_number() OVER () AS source_row,
 try_cast(timestamp AS BIGINT) AS ts_ms, try_cast(visitorid AS BIGINT) AS visitor_id,
 lower(trim(event)) AS event_name, try_cast(itemid AS BIGINT) AS item_id,
 try_cast(transactionid AS BIGINT) AS transaction_id
FROM raw;
CREATE OR REPLACE TABLE valid AS
SELECT * FROM parsed WHERE ts_ms > 0 AND visitor_id >= 0 AND item_id >= 0
 AND event_name IN ('view','addtocart','transaction')
 AND (event_name <> 'transaction' OR transaction_id IS NOT NULL);
CREATE OR REPLACE TABLE events AS
SELECT *, epoch_ms(ts_ms) AS event_ts,
 CAST(epoch_ms(ts_ms) AS DATE) AS event_date,
 CAST(date_trunc('week',epoch_ms(ts_ms)) AS DATE) AS event_week
FROM valid QUALIFY row_number() OVER (
 PARTITION BY ts_ms,visitor_id,event_name,item_id,transaction_id ORDER BY source_row)=1;
CREATE OR REPLACE TABLE visitors AS
SELECT visitor_id,min(ts_ms) AS first_ms,max(ts_ms) AS last_ms,
 min(ts_ms) FILTER(WHERE event_name='view') AS first_view_ms,
 min(ts_ms) FILTER(WHERE event_name='transaction') AS first_buy_ms,
 count(*) AS events,count(DISTINCT event_date) AS active_days,
 count(DISTINCT item_id) FILTER(WHERE event_name='view') AS viewed_items,
 count(DISTINCT transaction_id) AS orders,
 min(event_week) AS cohort_week
FROM events GROUP BY visitor_id;
-- Strict time order prevents inventing an order for same-millisecond events.
CREATE OR REPLACE TABLE visitor_funnel AS
WITH carts AS (
 SELECT e.visitor_id,min(e.ts_ms) AS first_cart_ms FROM events e
 JOIN visitors v USING(visitor_id)
 WHERE event_name='addtocart' AND ts_ms>first_view_ms GROUP BY e.visitor_id
), purchases AS (
 SELECT e.visitor_id,min(e.ts_ms) AS buy_after_cart_ms FROM events e JOIN carts c USING(visitor_id)
 WHERE event_name='transaction' AND ts_ms>first_cart_ms GROUP BY e.visitor_id
)
SELECT v.*,c.first_cart_ms,p.buy_after_cart_ms FROM visitors v
LEFT JOIN carts c USING(visitor_id) LEFT JOIN purchases p USING(visitor_id);
-- Session IDs use all events. Exact ties share a session; source row breaks sorting ties only.
CREATE OR REPLACE TABLE session_events AS
WITH lagged AS (
 SELECT *,lag(ts_ms) OVER(PARTITION BY visitor_id ORDER BY ts_ms,source_row) AS prev_ms FROM events
), numbered AS (
 SELECT *,sum(CASE WHEN prev_ms IS NULL OR ts_ms-prev_ms>1800000 THEN 1 ELSE 0 END)
 OVER(PARTITION BY visitor_id ORDER BY ts_ms,source_row ROWS UNBOUNDED PRECEDING) AS session_num
 FROM lagged
)
SELECT * FROM numbered;
CREATE OR REPLACE TABLE sessions AS
WITH starts AS (
 SELECT visitor_id,session_num,min(ts_ms) AS start_ms,min(ts_ms) FILTER(WHERE event_name='view') AS view_ms,
 bool_or(event_name='transaction') AS purchased,count(*) AS events,
 count(DISTINCT item_id) FILTER(WHERE event_name='view') AS viewed_items
 FROM session_events GROUP BY visitor_id,session_num
), carts AS (
 SELECT e.visitor_id,e.session_num,min(e.ts_ms) AS cart_ms FROM session_events e JOIN starts s USING(visitor_id,session_num)
 WHERE event_name='addtocart' AND ts_ms>view_ms GROUP BY e.visitor_id,e.session_num
), buys AS (
 SELECT e.visitor_id,e.session_num,min(e.ts_ms) AS ordered_buy_ms FROM session_events e JOIN carts c USING(visitor_id,session_num)
 WHERE event_name='transaction' AND ts_ms>cart_ms GROUP BY e.visitor_id,e.session_num
)
SELECT s.*,c.cart_ms,b.ordered_buy_ms,
 CASE WHEN session_num=1 THEN 'first_observed' ELSE 'returning_observed' END AS segment
FROM starts s LEFT JOIN carts c USING(visitor_id,session_num) LEFT JOIN buys b USING(visitor_id,session_num);
