# Wordnik API Call Optimization Plan

> Status: **PROPOSED — review before implementation.**
> Scope: reduce Wordnik quota consumption, prevent request bursts, and keep the
> existing daily word, tier, definition, example, audio, and pronunciation
> experience intact.

## 1. Executive Summary

The integration does not contain a timer or recursive retry loop, but one forced
fetch can currently be very expensive. The selection algorithm requests up to
20 candidate words, checks up to 10 of them, and then fetches audio, examples,
and pronunciations for every candidate that has a definition before deciding
which word to use. The corpus fallback can add another candidate request.

The target after this work is:

| Operation | Current possible cost | Target cost |
|-----------|------------------------|-------------|
| Normal daily fetch | 1 picker + up to 10 definition calls + up to 10 x 3 enrichment calls + audio download | 1 picker + 1-3 definition calls + enrichment for one selected word |
| New Word | Same as normal fetch, multiplied by every targeted tier | Same as normal fetch, with debounce and rate-limit protection |
| Empty filtered result | 2 picker calls | 1 bounded fallback, only when permitted by rate-limit state |
| Restart with current stored word | 0 API calls | 0 API calls |

The plan deliberately separates **quota reduction** from **content quality**. A
word without audio should not cause the integration to inspect and enrich nine
more words. Audio is an optional field in the current UI, not a requirement for
a word to be valid.

## 2. Evidence From the Wordnik API

Reviewed endpoint: [Wordnik `getRandomWords` documentation](https://developer.wordnik.com/docs#!/words/getRandomWords).

### 2.1 `randomWords`

`GET /words.json/randomWords` returns an array of `WordObject` values containing
fields such as `word`, `canonicalForm`, and `originalWord`. It does not return
the definition, examples, audio metadata, or pronunciations needed by the
card.

Useful documented filters include:

- `hasDictionaryDef`
- `minLength` / `maxLength`
- `minCorpusCount` / `maxCorpusCount`
- `includePartOfSpeech` / `excludePartOfSpeech`
- `limit`

`hasDictionaryDef=true` is useful for candidate selection but must not be
assumed to make a later definitions request unnecessary. The integration should
still validate the returned definition payload.

### 2.2 `wordOfTheDay`

`GET /words.json/wordOfTheDay?date=YYYY-MM-DD` returns a curated Wordnik word
with definitions and examples in the response. It is a good low-call-count
source for a non-tiered mode, but it cannot implement the current Sprout,
Explorer, Everyday, Scholar, and Luminary corpus/length profiles. It should
not silently replace tiered selection.

Potential future use:

- Add an explicit **Official Wordnik Word of the Day** mode.
- Use it only as a documented fallback when tier filtering is unavailable, if
  that product decision is approved.

### 2.3 Detail endpoints

The current detail endpoints each serve a distinct UI field:

- `/word/{word}/definitions`: definition text and attribution.
- `/word/{word}/topExample`: one example and should be evaluated as a cheaper,
  smaller alternative to `/examples` for the card's primary example.
- `/word/{word}/examples`: multiple examples and the current `examples` sensor
  attribute.
- `/word/{word}/audio`: audio metadata with an expiring `fileUrl`.
- `/word/{word}/pronunciations`: pronunciation data.

There is no documented combined endpoint that returns all of these fields for a
random tiered word. Parallel requests may reduce latency, but they do **not**
reduce quota usage. The implementation should optimize request count first.

## 3. Current Request Hotspots

### 3.1 Candidate loop enriches too early

`coordinator.py` currently does this for each candidate with a usable
 definition:

1. Fetch definitions.
2. Fetch audio.
3. Fetch examples.
4. Fetch pronunciations.
5. Prefer that candidate if it has audio; otherwise keep it as fallback.

Because audio is preferred, the code can fully enrich many candidates before
returning. This is the main request-volume bug.

### 3.2 Corpus fallback adds a burst

The current empty-result fallback repeats `randomWords` without corpus bounds.
This can be useful when Wordnik's corpus index has sparse coverage, but it adds a
request and can weaken the tier guarantee. It must be bounded and observable,
not treated as a free retry.

### 3.3 One API key is shared by all tiers

Each config entry creates its own coordinator, but all coordinators use the
same API key. A service call without a target intentionally refreshes every
configured tier. Any rate-limit accounting must therefore live in the shared
API client or shared Home Assistant domain state, not only in an individual
coordinator.

## 4. Proposed Design

### Phase 0: Instrument Before Tuning

Add request telemetry at the API boundary without logging the API key or full
URLs containing secrets:

- Endpoint family, such as `randomWords`, `definitions`, or `audio`.
- HTTP status.
- Duration.
- Whether the request was a normal fetch, fallback, startup, rollover, or
  `new_word` request.
- Candidate count and number of definition attempts per assembly.
- Rate-limit headers when present:
  - `x-ratelimit-remaining-minute`
  - `x-ratelimit-remaining-hour`
  - matching reset or retry headers if supplied by Wordnik.

Add a debug summary for each assembled word, for example:

```text
Wordnik fetch tier=everyday requests=5 candidates=3 definition_attempts=1 fallback=false
```

This lets us verify actual quota behavior rather than infer it from one 429.

### Phase 1: Make Candidate Selection Cheap

Refactor `_assemble` into explicit selection and enrichment stages.

1. Request a small candidate batch, initially `limit=3` or `limit=5` instead of
   `20`. Make the limit a named constant so it can be tuned.
2. Apply the blocklist locally.
3. For candidates in order, request definitions only.
4. Select the first candidate with a non-empty definition.
5. Stop selection immediately. Do not request audio, examples, or
   pronunciations for rejected candidates.
6. Enrich only the selected candidate.

The first target budget is:

- One `randomWords` call.
- One definition call in the common case, with a small bounded maximum for
  invalid candidates.
- One audio call.
- One example call, or one `topExample` call if the response is sufficient.
- One pronunciation call when the pronunciation sensor is enabled.
- One audio file download only when audio metadata exists.

A successful normal fetch should therefore be approximately 4-5 API calls,
not 40+.

### Phase 2: Remove Unnecessary Payload and Work

Evaluate these changes independently with tests:

- Change definitions from `limit=10` to the smallest value that still supports
  the primary definition and the `definitions` attribute. Start with `1` or
  `3`; retain only the returned data.
- Change audio metadata from `limit=5` to `limit=1` because the card uses one
  playable clip. Select the first valid `fileUrl`.
- Replace `examples?limit=5` with `topExample` for the primary card example if
  it returns equivalent usable text. Keep the full examples endpoint only if
  the `examples` sensor attribute is a supported requirement.
- Fetch pronunciations only when `CONF_SHOW_PRONUNCIATION` is enabled. This
  option currently controls entity creation, so the coordinator should receive
  or derive that setting before making the call.
- Do not download audio until the selected word is otherwise valid. Continue
  treating audio download failure as non-fatal.

Reducing response size is useful for latency and memory, but endpoint count is
the quota priority.

### Phase 3: Rate-Limit Awareness and Burst Control

Update `_get` to capture response headers and preserve rate-limit context in a
small shared state associated with the API client/key.

On HTTP 429:

1. Read `Retry-After` or the documented reset header when available.
2. Store a cooldown timestamp for the shared API client.
3. Raise a typed rate-limit error carrying the retry time and endpoint family.
4. Do not immediately retry the failed request.
5. While cooling down, fail fast before opening another HTTP request.

At the coordinator/service layer:

- Add an in-flight lock so two `new_word` calls for the same tier cannot fetch
  concurrently.
- Debounce `new_word` per tier, for example one successful or attempted forced
  fetch per configurable short interval. The exact interval should be chosen
  after observing the real quota headers.
- Preserve the last good word on 429 and clear the forced state only after a
  successful replacement is stored.
- Avoid automatic retry loops after a rate-limit failure. A later daily
  rollover may retry once the shared cooldown has expired.
- When several tiers are targeted, process them through a shared coordinator
  gate rather than launching a burst of concurrent requests.

The service description should explicitly warn that an untargeted call affects
all configured tiers. The card already targets a device/entity, which should
remain the preferred path.

### Phase 4: Handle Empty Candidate Results Without Making Quota Worse

The current corpus relaxation should be revised as follows:

- Keep the first request fully tier-filtered.
- If it returns no candidates, check the shared rate-limit state before trying
  a fallback.
- Allow at most one fallback request.
- Preserve length and part-of-speech filters.
- Mark the assembled result and logs as `corpus_fallback=true`.
- Do not use the fallback when the key is near its minute/hour limit.
- Consider removing the fallback entirely for tiers where it undermines the
  tier promise, especially Luminary and Scholar.

An alternative is to broaden the tier thresholds in configuration based on
observed empty-result rates. That is preferable to silently discarding corpus
semantics on every failure.

### Phase 5: Evaluate `wordOfTheDay` as a Separate Mode

Do not use `wordOfTheDay` as an implicit fallback for a tier. Instead, consider
an explicit configuration option:

- **Tiered random word:** current differentiated experience; approximately
  4-5 calls after optimization.
- **Official Wordnik word of the day:** one call returns the word, definitions,
  and examples; optional audio and pronunciation remain separate calls.

This gives users a genuinely low-call mode while keeping the meaning of the
existing tier controls honest.

## 5. Caching and Terms Check

The integration already persists the assembled daily display payload and avoids
API calls when the stored logical date is current. That is the most valuable
cache and should remain the default behavior.

Do not add a raw Wordnik response cache without checking the user's API plan and
Wordnik terms. The Wordnik FAQ states that Basic-plan users may not cache API
data for offline use, while paid plans have limited display-text caching
rights. The existing storage behavior should be reviewed against those terms
before expanding it to candidate lists or raw responses.

Safe implementation direction:

- Cache the assembled daily display state needed by Home Assistant.
- Do not persist unused candidate batches.
- Do not refetch detail endpoints when the stored word is current.
- Keep expiring audio URLs out of long-lived remote-use assumptions; the current
  local download is useful but should remain failure-tolerant.

## 6. Testing Plan

Add focused tests before changing request behavior:

### API client tests

- `randomWords` sends the intended reduced limit and all tier filters.
- Definitions, audio, and examples use reduced limits or `topExample` parsing.
- Rate-limit headers are captured on 429.
- `Retry-After` produces the expected cooldown.
- Requests fail fast during cooldown without calling the session.

### Coordinator tests

- Candidate 1 with a definition is selected and only candidate 1 is enriched.
- Candidate 1 without a definition causes one bounded definition-only retry.
- A candidate without audio is still selected and does not trigger selection of
  more candidates.
- Pronunciation is not requested when disabled.
- Empty corpus results cause at most one fallback request.
- A 429 returns the stored word and does not immediately retry.
- Concurrent `new_word` calls produce one fetch per tier.
- Targeted service calls affect only the requested entry.

### Regression and observability checks

- Assert request call counts for normal, fallback, and rate-limited paths.
- Verify no API calls occur when the current daily payload is stored.
- Verify multiple tiers do not issue concurrent bursts when one service call is
  targeted globally.
- Run the real test suite with the project's Home Assistant test dependencies.

## 7. Delivery Order

1. Add API status/header instrumentation and request-count tests.
2. Refactor selection so only definitions are fetched during candidate testing.
3. Enrich one selected candidate and reduce endpoint limits.
4. Add shared cooldown, in-flight locking, and forced-fetch debounce.
5. Rework or remove the corpus fallback based on observed empty-result data.
6. Add or document an explicit official Wordnik mode only if desired.
7. Update README and service descriptions with request behavior and targeting
   guidance.
8. Bump the integration version and release only after the focused and full
   test suites pass.

## 8. Acceptance Criteria

The optimization is complete when:

- A successful tiered daily fetch normally uses no more than 5 Wordnik API
  requests before the optional audio file download.
- Rejected candidates receive definition calls only; they never receive audio,
  examples, or pronunciation calls.
- A single `new_word` failure cannot immediately create an unbounded retry
  burst.
- HTTP 429 responses expose useful cooldown information and preserve the last
  good word.
- An untargeted multi-tier service call is serialized or explicitly documented
  as consuming one fetch budget per tier.
- Stored same-day data still results in zero Wordnik API requests.
- Tests assert request counts and rate-limit behavior rather than only checking
  the final word payload.
