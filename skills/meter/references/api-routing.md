# METER API v4 routing

## Inventory and setup

- `meter_query_surfaces`: look up known inventory by id, city, description, or address.
- `meter_collect_surfaces`: select and rank surfaces under audience, geography, and campaign constraints.
- `meter_universe`: calculate the projected audience Universe for filters before interpreting ratings or reach.

Preserve source warnings such as `демонтирован` (dismantled), unavailable or inactive in every selection and result table that includes the surface, including later campaign and per-surface answers. A returned record is not confirmation that placement is available. When a request selects up to three records, label it as a limited sample and disclose pagination/coverage limits; do not present it as complete city inventory.

## Campaign inputs and assumptions

Use the current tool schema and the user's actual city, period, audience and discovered surface IDs. Preserve user-supplied controls. When controls are omitted, either ask for inputs that materially affect the requested decision or explicitly disclose the reference assumptions before reporting the calculation: `blockSize: 0`, `byDays: false`, `chrono: 10`, `outputsInBlock: 1`, `impressions: [-1]`, normalization `0.3`, and legacy `reachModel: nbd-dirichlet` where supported. These are a reference campaign setup, not verified API defaults. Use the sentinel only where the selected tool supports it.

Keep the same complete surface set, audience, dates and campaign controls for campaign totals, per-surface breakdowns and methodology comparisons. Carry the agreed setup across turns. If inputs differ, disclose that difference before comparing results. Do not attribute a difference to one control without an isolated comparison.

## New OTS calculations

- New OTS is a newer methodology with limited geographic coverage. Do not assume inventory availability implies New OTS coverage.
- `meter_new_ots`: low-level broad New OTS calculation returning OTS/LTS/Rating/Universe and related metrics. It is not the default campaign reach route.
- `meter_new_ots_reach`: campaign OTS, reach, and impressions using the new methodology.
- `meter_new_ots_reach_by_surface`: reach and impressions split by surface.
- `meter_new_ots_profile_rate`: media metrics split by surface and audience profile.
- `meter_new_ots_reach_with_broadcast`: broadcast-aware calculation with two modes:
  - `broadcastRequest=0` (default): capacity mode; construction metric with SOV fixed to 1.0.
  - `broadcastRequest=1`: campaign mode; client SOV is active and `chrono`, `outputsInBlock`, and `blockSize` affect the result.

Do not infer campaign mode only because broadcast fields are populated; the `broadcastRequest` flag selects it. `impressionsRequest` is currently diagnostic/reserved and should not be described as affecting the returned media metrics.

## Legacy OTS calculations

Legacy OTS provides broad geographic coverage and is the default when New OTS support is unknown or unavailable.

- `meter_ots_reach`: campaign OTS and reach using the legacy methodology.
- `meter_ots_reach_by_surface`: legacy reach and impressions split by surface.
- `meter_ots_reach_with_broadcast`: legacy broadcast-aware calculation.
- `meter_statistic_profile_rate`: legacy audience profile calculation.
- `meter_ots_report`: legacy OTS-only reporting workflow.

The five legacy tools `meter_ots_reach`, `meter_ots_reach_by_surface`, `meter_ots_reach_with_broadcast`, `meter_ots_report`, and `meter_statistic_profile_rate` require an explicit, nonblank `audience.gender`. Use `all` only when the requested audience is all genders. Preserve any requested targeted value; do not infer an undocumented enum or silently inject `all`. If a targeted value is uncertain, resolve it from the current contract or ask for clarification. Keep the requested age and income filters; for all income groups use `abc`.

An invalid-parameter error requires correcting the same legacy tool request while retaining its methodology, audience, dates, surfaces and campaign controls. Do not recover with New OTS or `meter_mock_campaign`. New OTS statistics passed to mock-campaign with an NBD-Dirichlet reach model remain derived from New OTS; that step does not turn them into legacy OTS. If the corrected legacy request still fails, report the failure rather than inventing a legacy result. A zero result or empty response echo alone does not justify switching methodology.

Important field differences:

| New OTS | Legacy OTS |
| --- | --- |
| top-level `ageFrom`, `ageTo`, `gender`, `income` | nested `audience.age_from`, `audience.age_to`, `audience.gender`, `audience.income` |
| `normalize_coeff` | `normalizeCoeff` |
| methodology selected by `/new-ots/ots-reach` | `reachModel: nbd-dirichlet` on `/ots-reach` |

When New OTS returns `status: no_data` for an otherwise valid request, retry the equivalent legacy request once unless the user explicitly requires New OTS. Do not describe the New OTS endpoint as broken if legacy succeeds; report that the new methodology is unavailable for that geography or inventory. Do not silently mix results from the two methodologies.

The normalized HTTP `400`, `ok: false`, `data.status: no_data` response is also an explicit missing-coverage signal. Preserve audience, surfaces, dates and campaign controls in any permitted fallback. Other HTTP errors, invalid parameters and zero metrics are not evidence of missing coverage and must not trigger this fallback.

The API's echoed `request` object can be empty even when a calculation succeeds, so it is not a reliable record of submitted parameters. A `date` inside `statistic` can reflect response/calculation timing rather than the requested reporting period; retain the submitted period when labeling results.

## Other calculations

- `meter_mock_campaign`: modeled cumulative media metrics for a hypothetical campaign.
- `meter_calc_2media`: combine two reach spectra.
- `meter_collect_surfaces` can return inventory-ranking OTS from a different data path. A nonzero value there does not prove that New OTS supports the same geography or surface IDs.

## Capability boundaries

METER supports inventory planning and aggregate projected audience calculations. It does not buy or book advertising, take payments, or track identifiable private people. Explain these as unsupported METER capabilities, not problems caused by a missing card, expired campaign dates or missing inventory. Do not offer operator-site searches or another client mode as a METER booking workflow.

The plugin has no methods for exporting phone numbers, individual device or movement histories, footfall, device-level data, dwell time, visits or movement flows. Do not offer those exports as an aggregate alternative. Modeling factors such as dwell time do not establish an export capability. A supported alternative is an OTS/Reach, Universe or audience-profile calculation under the account's existing access.
