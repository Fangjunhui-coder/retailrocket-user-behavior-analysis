-- Sensitivity to equal timestamps and to requiring the same item.
WITH first_views AS (
 SELECT visitor_id,item_id,min(ts_ms) AS view_ms FROM events WHERE event_name='view' GROUP BY ALL
), item_carts AS (
 SELECT e.visitor_id,e.item_id,min(e.ts_ms) AS cart_ms FROM events e JOIN first_views v USING(visitor_id,item_id)
 WHERE event_name='addtocart' AND ts_ms>view_ms GROUP BY ALL
), item_buys AS (
 SELECT DISTINCT e.visitor_id FROM events e JOIN item_carts c USING(visitor_id,item_id)
 WHERE event_name='transaction' AND ts_ms>cart_ms
), loose_carts AS (
 SELECT e.visitor_id,min(e.ts_ms) AS cart_ms FROM events e JOIN visitors v USING(visitor_id)
 WHERE event_name='addtocart' AND ts_ms>=first_view_ms GROUP BY e.visitor_id
), loose_buys AS (
 SELECT DISTINCT e.visitor_id FROM events e JOIN loose_carts c USING(visitor_id)
 WHERE event_name='transaction' AND ts_ms>=cart_ms
)
SELECT 'strict_cross_item' AS definition,count(*) FILTER(WHERE first_cart_ms IS NOT NULL) AS cart_visitors,
 count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL) AS buyer_visitors FROM visitor_funnel
UNION ALL SELECT 'nondecreasing_cross_item',(SELECT count(*) FROM loose_carts),(SELECT count(*) FROM loose_buys)
UNION ALL SELECT 'strict_same_item',(SELECT count(DISTINCT visitor_id) FROM item_carts),(SELECT count(*) FROM item_buys);
