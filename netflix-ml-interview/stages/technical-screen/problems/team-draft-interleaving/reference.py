def team_draft(ranking_a, ranking_b, coins, k):
    rankings = {"A": ranking_a, "B": ranking_b}
    pos = {"A": 0, "B": 0}
    out, attribution = [], {}
    rnd = 0
    while len(out) < k and (pos["A"] < len(ranking_a) or pos["B"] < len(ranking_b)):
        if rnd >= len(coins):
            raise ValueError("not enough coins")
        order = ("A", "B") if coins[rnd] == 0 else ("B", "A")
        rnd += 1
        for team in order:
            if len(out) >= k:
                break
            r = rankings[team]
            while pos[team] < len(r) and r[pos[team]] in attribution:
                pos[team] += 1
            if pos[team] < len(r):
                item = r[pos[team]]
                out.append(item)
                attribution[item] = team
                pos[team] += 1
    return out, attribution


def score_clicks(clicked, attribution):
    score = {"A": 0, "B": 0}
    for item in clicked:
        if item in attribution:
            score[attribution[item]] += 1
    return score


def winner(clicks_by_impression):
    a = sum(1 for c in clicks_by_impression if c["A"] > c["B"])
    b = sum(1 for c in clicks_by_impression if c["B"] > c["A"])
    return "A" if a > b else "B" if b > a else "tie"
