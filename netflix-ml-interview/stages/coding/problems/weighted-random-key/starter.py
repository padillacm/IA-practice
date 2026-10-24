class WeightedKeySampler:
    def __init__(self, weights):
        raise NotImplementedError

    def pick(self, u):
        raise NotImplementedError

    def update(self, key, weight):
        raise NotImplementedError
