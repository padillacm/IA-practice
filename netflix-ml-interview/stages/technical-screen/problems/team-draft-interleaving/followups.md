# Follow-ups: team-draft interleaving

1. **Why interleave.** Interleaving is a quick pruning step with far fewer members than an A/B for the same sensitivity,
   but it gives a relative preference, not retention. What decision does it support and what must still go to an A/B test?
2. **Position bias.** In each position an item must be equally likely to come from A or B. Show with the coin per round
   that this holds, and what breaks if the coin is global per impression.
3. **Scale.** 100M impressions per test. Credit assignment is a per-impression map and a global sum: partition impressions
   across parallel workers, aggregate sums of wins, and compute a sign test or bootstrap on the aggregated counts.
4. **Concurrency.** The coin sequence must be reproducible for logging. Seed per (member, request) so retried requests in
   concurrent services produce the same interleaving.
5. **Business logic.** Rows, artwork and filters make the two lists differ for reasons other than ranking. Which of
   those break the interleaving assumption?
