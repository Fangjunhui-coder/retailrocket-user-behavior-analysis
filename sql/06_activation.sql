-- Fixed 7-day follow-up from each visitor's first observed event; late arrivals excluded.
WITH bounds AS (SELECT max(ts_ms) AS end_ms FROM events)
SELECT count(*) AS observed_visitors,count(*) FILTER(WHERE first_buy_ms IS NOT NULL) AS observed_buyers,
 count(*) FILTER(WHERE first_ms+604800000<=end_ms) AS eligible_7d_visitors,
 count(*) FILTER(WHERE first_ms+604800000<=end_ms AND first_buy_ms<first_ms+604800000) AS buyers_7d,
 100.0*count(*) FILTER(WHERE first_ms+604800000<=end_ms AND first_buy_ms<first_ms+604800000)
 /count(*) FILTER(WHERE first_ms+604800000<=end_ms) AS activation_7d_pct,
 quantile_cont((first_buy_ms-first_view_ms)/3600000.0,0.5)
 FILTER(WHERE first_buy_ms>=first_view_ms) AS median_view_to_first_buy_hours,
 count(*) FILTER(WHERE first_buy_ms IS NOT NULL AND (first_view_ms IS NULL OR first_buy_ms<first_view_ms)) AS buyers_without_prior_view
FROM visitors,bounds;
