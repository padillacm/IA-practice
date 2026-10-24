"""Group catalog records that describe the same title.

Two records are duplicates when they have the same content type, the same release year and the same
normalized title. Records with a missing year only match records with a missing year.
The canonical record of a group is the one with the most non-empty metadata fields;
ties go to the lowest id.
"""
from collections import namedtuple

from .normalize import normalize_title

Record = namedtuple("Record", "id title year kind metadata")
# kind: "movie" | "series"; metadata: dict of optional fields (may contain empty values)


def canonical_key(record):
    return (record.kind, record.year, normalize_title(record.title))


def _richness(record):
    return sum(1 for v in record.metadata.values() if v not in (None, "", [], {}))


def dedupe(records):
    """Return a list of groups; each group is {"canonical": id, "duplicates": [ids...]}.

    Groups are ordered by the canonical id; duplicates are sorted ascending. Groups of size 1 are included.
    """
    buckets = {}
    for r in records:
        buckets.setdefault(canonical_key(r), []).append(r)
    groups = []
    for members in buckets.values():
        best = sorted(members, key=lambda r: (-_richness(r), r.id))[0]
        groups.append({"canonical": best.id,
                       "duplicates": sorted(r.id for r in members if r.id != best.id)})
    return sorted(groups, key=lambda g: g["canonical"])
