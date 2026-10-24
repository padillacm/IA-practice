def longest_unique_span(s):
    last = {}
    start = best_start = best_len = 0
    for i, ch in enumerate(s):
        if ch in last and last[ch] >= start:
            start = last[ch] + 1
        last[ch] = i
        if i - start + 1 > best_len:
            best_start, best_len = start, i - start + 1
    return (best_start, best_len)


def longest_unique_substring(s):
    return longest_unique_span(s)[1]
