import heapq


class Billboard:
    """Pending heap with lazy deletion; `served` movies wait for the next cycle."""

    def __init__(self):
        self.score = {}
        self.pending = set()
        self.heap = []

    def add(self, movie, score):
        self.score[movie] = score
        self.pending.add(movie)
        heapq.heappush(self.heap, (-score, movie))

    def update(self, movie, score):
        if movie not in self.score:
            raise KeyError(movie)
        self.score[movie] = score
        if movie in self.pending:
            heapq.heappush(self.heap, (-score, movie))

    def remove(self, movie):
        if movie not in self.score:
            raise KeyError(movie)
        del self.score[movie]
        self.pending.discard(movie)

    def get(self):
        if not self.score:
            return None
        if not self.pending:
            self.pending = set(self.score)
            self.heap = [(-s, m) for m, s in self.score.items()]
            heapq.heapify(self.heap)
        while True:
            neg, movie = heapq.heappop(self.heap)
            if movie in self.pending and self.score[movie] == -neg:
                self.pending.discard(movie)
                return movie
