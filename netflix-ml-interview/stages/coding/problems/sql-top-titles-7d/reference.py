def top_titles_query():
    return """
    WITH win AS (
        SELECT country, title_id, COUNT(*) AS completions
        FROM plays
        WHERE completed = 1
          AND play_date BETWEEN date(:as_of, '-6 days') AND date(:as_of)
        GROUP BY country, title_id
    ), ranked AS (
        SELECT country, title_id, completions,
               ROW_NUMBER() OVER (PARTITION BY country ORDER BY completions DESC, title_id ASC) AS rnk
        FROM win
    )
    SELECT country, title_id, completions, rnk
    FROM ranked
    WHERE rnk <= :n
    ORDER BY country, rnk
    """
