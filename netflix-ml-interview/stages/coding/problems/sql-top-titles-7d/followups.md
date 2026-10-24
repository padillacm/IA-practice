# Follow-ups: top titles by 7-day completions per country

1. **ROW_NUMBER vs RANK vs DENSE_RANK.** What does each return for tied titles, and which does the product want
   (a fixed-size row of exactly n titles)? Change the query to return all titles tied for the last slot.
2. **Rate vs count.** Rank by completion rate (completed / started) with a minimum number of starts. Why does a raw
   rate with 1 play over-rank tiny titles? Add shrinkage or a minimum-support filter.
3. **Scale.** The plays table has 50 billion rows. Which indexes or partitions make the filter cheap (partition by
   date, cluster by country)? Precompute daily aggregates and sum 7 of them instead of rescanning; the daily rollup is
   also trivially parallel across date partitions. What does this do to late-arriving plays?
4. **Concurrency.** Ingestion keeps appending plays while the query runs. What isolation level / snapshot semantics do you
   want so that the ranking is consistent, and what would happen with two concurrent refresh jobs writing the same
   output table (idempotent overwrite by partition)?
5. **Time zones.** `play_date` is UTC but the product day is local. How many countries cross a date boundary and how do
   you fix it?
6. **Pandas.** Write the same logic with `groupby(...).size()` and `rank(method="first")` after sorting. What is
   the equivalent of the tie-breaker?
