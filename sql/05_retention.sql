-- Calendar week cohorts (UTC). Discard partial entry cohorts and immature follow-up weeks.
WITH bounds AS (SELECT min(event_ts) AS min_ts,max(event_ts) AS max_ts FROM events),
 cohorts AS (
 SELECT cohort_week,count(*) AS cohort_size FROM visitors,bounds
 WHERE cohort_week>=CAST(min_ts AS DATE)
 AND CAST(cohort_week AS TIMESTAMP)+INTERVAL '7 days'<=max_ts GROUP BY cohort_week
), grid AS (
 SELECT c.*,age.week_age FROM cohorts c CROSS JOIN range(0,13) age(week_age),bounds
 WHERE CAST(c.cohort_week AS TIMESTAMP)+(age.week_age+1)*INTERVAL '7 days'<=max_ts
), activities AS (
 SELECT DISTINCT v.cohort_week,e.visitor_id,date_diff('week',v.cohort_week,e.event_week) AS week_age
 FROM events e JOIN visitors v USING(visitor_id)
)
SELECT g.cohort_week,g.week_age,g.cohort_size,count(a.visitor_id) AS active_visitors,
 100.0*count(a.visitor_id)/g.cohort_size AS retention_pct FROM grid g
LEFT JOIN activities a ON g.cohort_week=a.cohort_week AND g.week_age=a.week_age
GROUP BY g.cohort_week,g.week_age,g.cohort_size ORDER BY 1,2;
