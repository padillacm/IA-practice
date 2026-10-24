#!/usr/bin/env python3
"""Generate the synthetic 'kids profile feature' data (stdlib only, seeded, deterministic).

Usage: python3 generate_data.py <output_dir>
Writes households.csv, daily_activity.csv, survey.csv.
"""
import csv
import math
import os
import random
import sys

SEED = 20260612
N_HH = 3000
DAYS = 28
REGIONS = ["na", "emea", "latam", "apac"]
# Novelty: the lift decays; a smaller durable component remains.
NOVELTY_AMP = 0.60
NOVELTY_TAU = 5.0
DURABLE = 0.06


def main(out):
    rng = random.Random(SEED)
    os.makedirs(out, exist_ok=True)
    hh_rows, act_rows, survey_rows = [], [], []
    for i in range(N_HH):
        hid = f"h{i:05d}"
        region = rng.choices(REGIONS, [0.4, 0.3, 0.2, 0.1])[0]
        n_kids = rng.choices([0, 1, 2, 3], [0.15, 0.4, 0.33, 0.12])[0]
        arm = "feature" if rng.random() < 0.5 else "holdout"
        # households with kids use the feature more
        affinity = 0.3 + 0.35 * n_kids
        base = max(0.2, rng.lognormvariate(0.2, 0.5))
        kids_base = 0.15 * n_kids * rng.random()
        hh_rows.append([hid, region, n_kids, arm])
        total_kids = 0.0
        for d in range(1, DAYS + 1):
            lift = 0.0
            if arm == "feature":
                lift = affinity * (NOVELTY_AMP * math.exp(-(d - 1) / NOVELTY_TAU) + DURABLE)
            weekend = 0.25 if d % 7 in (6, 0) else 0.0
            total = max(0.0, base + weekend + lift + rng.gauss(0, 0.35))
            kids = max(0.0, kids_base + (lift * 0.8 if arm == "feature" else 0.0) + rng.gauss(0, 0.1))
            kids = min(kids, total)
            total_kids += kids
            act_rows.append([hid, d, round(total, 3), round(kids, 3), 1 if total > 0.05 else 0])
        # Survey only for a self-selected subset (more likely if exposed and engaged): selection bias.
        p_resp = 0.10 + (0.20 if arm == "feature" else 0.0) + 0.1 * min(total_kids / 10, 1)
        if rng.random() < p_resp:
            score = 3.2 + (0.5 if arm == "feature" else 0.0) + rng.gauss(0, 0.9)
            survey_rows.append([hid, max(1, min(5, int(round(score))))])
    for name, header, rows in [
        ("households.csv", ["household_id", "region", "n_kids_profiles_prior", "arm"], hh_rows),
        ("daily_activity.csv", ["household_id", "day", "hours_total", "hours_kids_content", "active"], act_rows),
        ("survey.csv", ["household_id", "parent_satisfaction_1to5"], survey_rows),
    ]:
        with open(os.path.join(out, name), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: generate_data.py <output_dir>")
    main(sys.argv[1])
