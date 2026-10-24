# Follow-ups: pairs of strings with no common characters

1. **Bound on the work.** At most 2^26 masks, but a list of n words has at most n distinct masks; with short words far
   fewer. When does the pairwise loop over distinct masks stop being acceptable?
2. **Subset-sum (SOS) DP.** Count disjoint pairs in O(2^26 * 26) by counting for each mask the words that are subsets
   of its complement. When is that better than the pairwise loop? What is the memory cost?
3. **Scale and parallelism.** 100M words (for example tags per title): compute masks in parallel with a map step,
   aggregate counts per mask in a reduce, then run the pair counting on the (small) histogram. Why is the histogram
   tiny relative to the input?
4. **Concurrency.** Building the mask histogram from several threads: per-thread Counters merged at the end vs a shared
   locked dict. Which scales better and why?
5. **Generalization.** Unicode tags (no 26-bit limit): hashing into a Bloom-like signature, false positives and an exact
   verification step. Relate it to candidate-pair generation for near-duplicate title detection.
