-- Per-item strict view->cart->purchase; window-wide, item prices/categories unavailable in events.csv.
WITH views AS (
 SELECT visitor_id,item_id,min(ts_ms) AS view_ms FROM events WHERE event_name='view' GROUP BY ALL
), carts AS (
 SELECT e.visitor_id,e.item_id,min(e.ts_ms) AS cart_ms FROM events e JOIN views v USING(visitor_id,item_id)
 WHERE event_name='addtocart' AND ts_ms>view_ms GROUP BY ALL
), direct_buys AS (
 SELECT e.visitor_id,e.item_id,min(e.ts_ms) AS any_buy_ms FROM events e JOIN views v USING(visitor_id,item_id)
 WHERE event_name='transaction' AND ts_ms>view_ms GROUP BY ALL
), buys AS (
 SELECT e.visitor_id,e.item_id,min(e.ts_ms) AS buy_ms FROM events e JOIN carts c USING(visitor_id,item_id)
 WHERE event_name='transaction' AND ts_ms>cart_ms GROUP BY ALL
)
SELECT item_id,count(*) AS viewing_visitors,count(cart_ms) AS cart_visitors,count(buy_ms) AS buying_visitors,
 count(any_buy_ms) AS buyers_after_view,
 100.0*count(cart_ms)/count(*) AS view_to_cart_pct,100.0*count(buy_ms)/count(*) AS ordered_conversion_pct
FROM views LEFT JOIN carts USING(visitor_id,item_id) LEFT JOIN buys USING(visitor_id,item_id)
LEFT JOIN direct_buys USING(visitor_id,item_id)
GROUP BY item_id HAVING count(*)>=1000 ORDER BY viewing_visitors DESC;
