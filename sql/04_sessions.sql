-- Segmentation is known at session start. This is observational, not an effect of returning.
SELECT segment,count(*) AS sessions,count(DISTINCT visitor_id) AS distinct_visitors,
 count(*) FILTER(WHERE view_ms IS NOT NULL) AS viewing_sessions,
 count(*) FILTER(WHERE cart_ms IS NOT NULL) AS ordered_cart_sessions,
 count(*) FILTER(WHERE ordered_buy_ms IS NOT NULL) AS ordered_buy_sessions,
 count(*) FILTER(WHERE purchased) AS purchasing_sessions,
 100.0*count(*) FILTER(WHERE ordered_buy_ms IS NOT NULL)/nullif(count(*) FILTER(WHERE view_ms IS NOT NULL),0) AS ordered_conversion_pct,
 100.0*count(*) FILTER(WHERE purchased)/count(*) AS any_purchase_pct,
 avg(viewed_items) AS mean_viewed_items FROM sessions GROUP BY segment ORDER BY segment;
