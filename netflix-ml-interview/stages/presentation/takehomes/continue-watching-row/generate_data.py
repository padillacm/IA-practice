#!/usr/bin/env python3
"""Generate the synthetic 'continue watching row' experiment data (stdlib only, seeded, deterministic).

Usage: python3 generate_data.py <output_dir>
Writes users.csv, assignment.csv, outcomes.csv.
"""
import csv
import math
import os
import random
import sys

SEED = 20260611
N_USERS = 8000
DEVICES = ["tv", "mobile", "web"]
DEVICE_P = [0.50, 0.35, 0.15]
# True average effect of the new row on post-period viewing hours, by device.
EFFECT = {"tv": 0.55, "mobile": 0.05, "web": 0.20}
PLANS = ["basic", "standard", "premium"]


def main(out):
    rng = random.Random(SEED)
    os.makedirs(out, exist_ok=True)
    users, assign, outcomes = [], [], []
    for i in range(N_USERS):
        uid = f"u{i:05d}"
        device = rng.choices(DEVICES, DEVICE_P)[0]
        plan = rng.choices(PLANS, [0.25, 0.5, 0.25])[0]
        tenure = int(rng.expovariate(1 / 18)) + 1  # months
        # latent taste for viewing drives both pre and post (CUPED-able covariate)
        latent = rng.lognormvariate(0.9, 0.55)
        pre_hours = max(0.0, latent + rng.gauss(0, 0.8))
        variant = "treatment" if rng.random() < 0.5 else "control"
        base = 0.85 * latent + 0.4 + rng.gauss(0, 1.1)
        eff = EFFECT[device] if variant == "treatment" else 0.0
        post_hours = max(0.0, base + eff + rng.gauss(0, 0.3))
        sessions = max(0, int(round(post_hours * 0.9 + rng.gauss(0, 0.8))))
        # Row click-through only exists for treatment exposure
        saw_row = 1 if variant == "treatment" and rng.random() < 0.93 else 0
        clicked = 1 if saw_row and rng.random() < (0.30 if device == "tv" else 0.12) else 0
        # Guardrail: search usage drops slightly when the row is present
        searches = max(0, int(round(rng.gauss(2.0 - (0.25 if saw_row else 0.0), 1.3))))
        retained_28d = 1 if rng.random() < 1 / (1 + math.exp(-(0.9 + 0.35 * (post_hours - 3) + 0.01 * tenure))) else 0
        users.append([uid, device, plan, tenure, round(pre_hours, 3)])
        assign.append([uid, variant])
        outcomes.append([uid, round(post_hours, 3), sessions, saw_row, clicked, searches, retained_28d])
    for name, header, rows in [
        ("users.csv", ["user_id", "device", "plan", "tenure_months", "pre_hours"], users),
        ("assignment.csv", ["user_id", "variant"], assign),
        ("outcomes.csv", ["user_id", "post_hours", "post_sessions", "saw_row", "clicked_row", "post_searches", "retained_28d"], outcomes),
    ]:
        with open(os.path.join(out, name), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: generate_data.py <output_dir>")
    main(sys.argv[1])
