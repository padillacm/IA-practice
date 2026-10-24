class WeightedKeySampler:
    """Fenwick tree over weights: O(log n) update and O(log n) descent to find the key."""

    def __init__(self, weights):
        if any(w < 0 for w in weights.values()):
            raise ValueError("negative weight")
        if not weights or sum(weights.values()) <= 0:
            raise ValueError("total weight must be positive")
        self.keys = list(weights)
        self.index = {k: i for i, k in enumerate(self.keys)}
        self.n = len(self.keys)
        self.w = [weights[k] for k in self.keys]
        self.tree = [0] * (self.n + 1)
        for i, w in enumerate(self.w):
            self._add(i, w)
        self.total = sum(self.w)
        self.top = 1
        while self.top * 2 <= self.n:
            self.top *= 2

    def _add(self, i, delta):
        i += 1
        while i <= self.n:
            self.tree[i] += delta
            i += i & -i

    def update(self, key, weight):
        i = self.index[key]  # KeyError if unknown
        if weight < 0:
            raise ValueError("negative weight")
        if self.total - self.w[i] + weight <= 0:
            raise ValueError("total weight must be positive")
        self._add(i, weight - self.w[i])
        self.total += weight - self.w[i]
        self.w[i] = weight

    def pick(self, u):
        target = u * self.total
        pos, step = 0, self.top
        while step:
            nxt = pos + step
            if nxt <= self.n and self.tree[nxt] <= target:
                pos = nxt
                target -= self.tree[nxt]
            step //= 2
        if pos >= self.n:  # float rounding at the upper edge
            pos = self.n - 1
            while self.w[pos] == 0:
                pos -= 1
        return self.keys[pos]
