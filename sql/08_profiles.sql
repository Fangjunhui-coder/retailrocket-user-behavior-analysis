-- Post-hoc descriptive profiles; no causal comparison between future-defined groups.
SELECT CASE WHEN orders>1 THEN 'repeat_buyer' WHEN orders=1 THEN 'one_order_buyer'
 WHEN first_cart_ms IS NOT NULL THEN 'cart_no_purchase' ELSE 'other_no_purchase' END AS profile,
 count(*) AS visitors,avg(active_days) AS mean_active_days,avg(viewed_items) AS mean_viewed_items,
 median(viewed_items) AS median_viewed_items,sum(orders) AS visitor_orders
FROM visitor_funnel GROUP BY profile ORDER BY visitors DESC;
