-- Exclusion counts are mutually exclusive: invalid rows first, then duplicate valid rows.
SELECT (SELECT count(*) FROM raw) AS raw_rows,
 (SELECT count(*) FROM parsed)-(SELECT count(*) FROM valid) AS invalid_rows,
 (SELECT count(*) FROM valid)-(SELECT count(*) FROM events) AS exact_duplicates,
 count(*) AS clean_rows,count(DISTINCT visitor_id) AS visitors,
 count(DISTINCT item_id) AS items,count(DISTINCT transaction_id) AS orders,
 min(event_ts) AS first_event_utc,max(event_ts) AS last_event_utc,
 count(*) FILTER(WHERE event_name='view') AS views,
 count(*) FILTER(WHERE event_name='addtocart') AS carts,
 count(*) FILTER(WHERE event_name='transaction') AS transaction_lines,
 count(*) FILTER(WHERE event_name<>'transaction' AND transaction_id IS NOT NULL) AS unexpected_transaction_ids,
 (SELECT count(*) FROM (SELECT visitor_id,ts_ms FROM events GROUP BY ALL HAVING count(*)>1)) AS visitor_timestamp_tie_groups
FROM events;
