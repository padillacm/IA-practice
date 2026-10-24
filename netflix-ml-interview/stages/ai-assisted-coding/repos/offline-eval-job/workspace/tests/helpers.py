from offline_eval import Impression


def imp(iid, req, user, item, pos, ts, clicked=0):
    return Impression(iid, req, user, item, pos, ts, clicked)
