import math


def precision_at_k(ranked, relevant, k):
    raise NotImplementedError


def recall_at_k(ranked, relevant, k):
    raise NotImplementedError


def ndcg_at_k(ranked, gains, k):
    raise NotImplementedError


def mean_metric(metric, requests, **kwargs):
    raise NotImplementedError
