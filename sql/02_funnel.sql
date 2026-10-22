-- Visitor-level strict ordered funnel across the observation window, not one product or session.
WITH counts AS (
 SELECT 1 AS stage_order,'view' AS stage,count(*) FILTER(WHERE first_view_ms IS NOT NULL) AS visitors FROM visitor_funnel
 UNION ALL SELECT 2,'cart_after_view',count(*) FILTER(WHERE first_cart_ms IS NOT NULL) FROM visitor_funnel
 UNION ALL SELECT 3,'purchase_after_cart',count(*) FILTER(WHERE buy_after_cart_ms IS NOT NULL) FROM visitor_funnel
), comparison AS (
 SELECT *,lag(visitors) OVER(ORDER BY stage_order) AS prior_visitors,
 first_value(visitors) OVER(ORDER BY stage_order) AS viewing_visitors FROM counts
)
SELECT *,100.0*visitors/nullif(prior_visitors,0) AS prior_conversion_pct,
 100.0*visitors/viewing_visitors AS overall_conversion_pct,
 prior_visitors-visitors AS dropoff_visitors FROM comparison ORDER BY stage_order;
