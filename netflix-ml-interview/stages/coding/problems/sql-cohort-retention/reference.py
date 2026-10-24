def cohort_retention_query():
    return """
    WITH cohort AS (
        SELECT user_id, signup_date, strftime('%Y-%m', signup_date) AS cohort_month,
               CAST(strftime('%Y', signup_date) AS INTEGER) * 12 + CAST(strftime('%m', signup_date) AS INTEGER) AS m0
        FROM signups
    ), sizes AS (
        SELECT cohort_month, COUNT(*) AS cohort_size FROM cohort GROUP BY cohort_month
    ), act AS (
        SELECT DISTINCT c.cohort_month, c.user_id,
               CAST(strftime('%Y', a.activity_date) AS INTEGER) * 12
                 + CAST(strftime('%m', a.activity_date) AS INTEGER) - c.m0 AS month_offset
        FROM cohort c
        JOIN activity a ON a.user_id = c.user_id AND a.activity_date >= c.signup_date
    )
    SELECT act.cohort_month, act.month_offset,
           COUNT(*) AS active_users, sizes.cohort_size,
           ROUND(1.0 * COUNT(*) / sizes.cohort_size, 4) AS retention
    FROM act JOIN sizes USING (cohort_month)
    GROUP BY act.cohort_month, act.month_offset
    ORDER BY act.cohort_month, act.month_offset
    """
