# METER API v4 routing

## Inventory and setup

- `meter_query_surfaces`: look up known inventory by id, city, description, or address.
- `meter_collect_surfaces`: select and rank surfaces under audience, geography, and campaign constraints.
- `meter_universe`: calculate the projected audience Universe for filters before interpreting ratings or reach.

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

Use the tool's current input schema and the user's actual city, period, audience and discovered surface IDs. Never reuse example IDs from another campaign. Preserve explicit campaign controls and use `impressions: [-1]` only where the schema and selected calculation support that sentinel.

## Legacy OTS calculations

Legacy OTS provides broad geographic coverage and is the default when New OTS support is unknown or unavailable.

- `meter_ots_reach`: campaign OTS and reach using the legacy methodology.
- `meter_ots_reach_by_surface`: legacy reach and impressions split by surface.
- `meter_ots_reach_with_broadcast`: legacy broadcast-aware calculation.
- `meter_statistic_profile_rate`: legacy audience profile calculation.

Important field differences:

| New OTS | Legacy OTS |
| --- | --- |
| top-level `ageFrom`, `ageTo`, `gender`, `income` | nested `audience.age_from`, `audience.age_to`, `audience.gender`, `audience.income` |
| `normalize_coeff` | `normalizeCoeff` |
| methodology selected by `/new-ots/ots-reach` | `reachModel: nbd-dirichlet` on `/ots-reach` |

When New OTS returns `status: no_data` for an otherwise valid request, retry the equivalent legacy request once unless the user explicitly requires New OTS. Do not describe the New OTS endpoint as broken if legacy succeeds; report that the new methodology is unavailable for that geography or inventory. Do not silently mix results from the two methodologies.

The API's echoed `request` object can be empty even when a calculation succeeds, so it is not a reliable record of submitted parameters. A `date` inside `statistic` can reflect response/calculation timing rather than the requested reporting period; retain the submitted period when labeling results.

## Other calculations

- `meter_mock_campaign`: modeled cumulative media metrics for a hypothetical campaign.
- `meter_calc_2media`: combine two reach spectra.
- `meter_ots_report`: OTS-only reporting workflow.
- `meter_collect_surfaces` can return inventory-ranking OTS from a different data path. A nonzero value there does not prove that New OTS supports the same geography or surface IDs.
