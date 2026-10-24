def sessionize_query():
    return """
    WITH flagged AS (
        SELECT user_id, ts,
               CASE WHEN LAG(ts) OVER (PARTITION BY user_id ORDER BY ts) IS NULL
                         OR ts - LAG(ts) OVER (PARTITION BY user_id ORDER BY ts) > 1800
                    THEN 1 ELSE 0 END AS is_new
        FROM events
    ), numbered AS (
        SELECT user_id, ts,
               SUM(is_new) OVER (PARTITION BY user_id ORDER BY ts
                                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_num
        FROM flagged
    )
    SELECT user_id, session_num, MIN(ts) AS start_ts, MAX(ts) AS end_ts, COUNT(*) AS n_events
    FROM numbered
    GROUP BY user_id, session_num
    ORDER BY user_id, session_num
    """
