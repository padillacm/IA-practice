def dedup_rows(rows, n):
    visible = set()  # titles occupying a visible position in any processed row
    out = []
    for row in rows:
        seen = set()
        kept = []
        for title in row:
            if title in seen:
                continue
            if len(kept) < n:
                if title in visible:
                    continue
                visible.add(title)
            seen.add(title)
            kept.append(title)
        out.append(kept)
    return out
