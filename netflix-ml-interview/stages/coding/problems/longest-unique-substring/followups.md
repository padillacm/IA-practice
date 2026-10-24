# Follow-ups: longest substring without repeated characters

1. **Alphabet size.** Array of 26/128 counters vs dict vs a bitmask when the alphabet is small. What changes for
   Unicode code points versus grapheme clusters (emoji with modifiers)?
2. **Streaming.** The string is an unbounded stream of title ids (a playback session). Report the longest run so far
   in O(1) per item and O(distinct) memory. What bounds the memory?
3. **Scale and parallelism.** A 10 GB string split across 64 workers (parallel chunks): why can't chunks be processed
   independently, and what do you carry across chunk boundaries (a boundary window of at most alphabet-size characters)?
4. **Concurrency.** Many threads each calling the function on their own strings: any shared state? Is memoization with a
   dict safe, and how would you make a shared cache thread-safe?
5. **Variants.** At most k distinct characters; at most one repeated character; the longest substring where every
   character appears at least k times. Which invariant changes?
