# Task: batch lookups and per-feature-set TTLs

You are on the team that owns `feature_service`, the online feature lookup layer in front of a slow
backend store. It is called on the request path of a ranking service, so extra backend round trips
matter. The code is in `workspace/`; run the tests with `python -m unittest` from that directory.

You may use the AI pair (`::ai <prompt>`) as much as you like. It proposes changes as a diff; nothing is
applied until you run `::apply`. You are responsible for what you apply.

## Part 1 - batch lookup

Add `FeatureService.get_many(entity_ids, feature_set)`:
- returns a dict `{entity_id: features}` for the entities that exist (unknown ids are omitted);
- cache hits are served from the cache, and all misses go to the backend in ONE `backend.fetch_many(feature_set, ids)` call;
- duplicate ids in the input trigger at most one backend lookup;
- hit/miss counters keep working (one per requested unique id).

## Part 2 - per-feature-set TTL

Some feature sets (e.g. `title`) change slowly and can be cached for an hour; others (`user`) should
expire in a minute. Add an optional `ttl_overrides` mapping (`{feature_set: seconds}`) to `FeatureService`
that is applied when entries are cached, falling back to the cache default.

## Expectations

- Add tests for what you build.
- Be ready to explain how you know the change is correct.
