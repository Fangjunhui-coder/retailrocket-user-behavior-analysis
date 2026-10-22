-- Sensitivity only: high activity does not prove a bot or an invalid visitor.
WITH cutoff AS (SELECT quantile_cont(events,0.999) AS event_threshold FROM visitors),
filtered AS (SELECT v.* FROM visitor_funnel v,cutoff WHERE events<=event_threshold)
SELECT 'all_visitors' AS population,(SELECT event_threshold FROM cutoff) AS event_threshold,
 count(*) AS visitors,count(*) FILTER(WHERE first_view_ms IS NOT NULL) AS viewers,
 count(*) FILTER(WHERE first_cart_ms IS NOT NULL) AS ordered_carts,
 count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL) AS ordered_buyers,
 100.0*count(*) FILTER(WHERE first_cart_ms IS NOT NULL)/count(*) FILTER(WHERE first_view_ms IS NOT NULL) AS view_to_cart_pct,
 100.0*count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL)/count(*) FILTER(WHERE first_view_ms IS NOT NULL) AS ordered_conversion_pct
FROM visitor_funnel
UNION ALL SELECT 'exclude_above_p999',(SELECT event_threshold FROM cutoff),count(*),
 count(*) FILTER(WHERE first_view_ms IS NOT NULL),count(*) FILTER(WHERE first_cart_ms IS NOT NULL),
 count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL),
 100.0*count(*) FILTER(WHERE first_cart_ms IS NOT NULL)/count(*) FILTER(WHERE first_view_ms IS NOT NULL),
 100.0*count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL)/count(*) FILTER(WHERE first_view_ms IS NOT NULL)
FROM filtered;
