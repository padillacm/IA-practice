# Follow-ups: ROC AUC with ties

1. **Interpretation.** Why is AUC insensitive to calibration and to class prior, and why does that make it a poor
   headline metric for a ranker whose output feeds a probability-based decision? When would you use PR-AUC or NDCG?
2. **Scale.** Evaluate 5 billion (label, score) pairs. Bucket scores into a few thousand quantile bins on each parallel
   worker, sum positive and negative counts per bin, and compute AUC from the merged histogram; what error does ties
   inside a bin add? Why is averaging per-shard AUC wrong?
3. **Concurrency.** Streaming evaluation with multiple threads updating the histogram: lock-free atomic counters per bin
   vs per-thread histograms merged; what consistency do you need for a dashboard?
4. **Group AUC.** Per-member AUC averages are dominated by members with a few events. Weighting options and the effect of
   members with one class only being dropped (selection bias).
5. **Leakage check.** The AUC jumps from 0.72 to 0.98 after a feature change. List three causes to check before
   celebrating (time leakage, label proxy, duplicates across train and test).
