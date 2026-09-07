# Measured response times

Measurements from 6 September 2026, using the METER API directly: Tashkent, three surfaces, 1–31 August 2026, audience ages 6–100. These are API response times including reading/parsing the response, not Claude task completion times or an SLA. OAuth, authorization and remote MCP transport were outside this benchmark. No customer identifiers or calculation payloads are included here.

| Метод | Замеров | Первый, с | Медиана всех, с | Последующие: медиана / диапазон, с |
| --- | ---: | ---: | ---: | ---: |
| `meter_status` | 3 | 1.066 | 0.326 | 0.314 / 0.301–0.326 |
| `meter_calc_2media` | 3 | 0.168 | 0.119 | 0.118 / 0.118–0.119 |
| `meter_collect_surfaces` | 3 | 2.034 | 2.222 | 2.337 / 2.222–2.451 |
| `meter_mock_campaign` | 3 | 0.817 | 0.238 | 0.233 / 0.229–0.238 |
| `meter_new_ots` | 3 | 7.707 | 6.350 | 6.325 / 6.300–6.350 |
| `meter_new_ots_reach` | 3 | 6.014 | 6.177 | 6.181 / 6.177–6.186 |
| `meter_new_ots_reach_by_surface` | 3 | 14.618 | 12.506 | 12.197 / 11.889–12.506 |
| `meter_new_ots_reach_with_broadcast` | 3 | 6.033 | 6.033 | 6.101 / 5.823–6.378 |
| `meter_new_ots_profile_rate` | 3 | 12.931 | 12.931 | 13.032 / 12.465–13.598 |
| `meter_ots_reach` † | 3 | 1.361 | 1.164 | 1.160 / 1.157–1.164 |
| `meter_ots_reach_by_surface` † | 3 | 1.206 | 1.206 | 1.461 / 1.153–1.768 |
| `meter_ots_reach_with_broadcast` | 3 | 1.890 | 1.650 | 1.615 / 1.581–1.650 |
| `meter_ots_report` † | 3 | 2.306 | 2.317 | 2.328 / 2.317–2.339 |
| `meter_query_surfaces` | 3 | 0.155 | 0.155 | 0.157 / 0.155–0.159 |
| `meter_statistic_profile_rate` | 3 | 3.014 | 2.866 | 2.686 / 2.505–2.866 |
| `meter_universe` | 3 | 0.393 | 0.143 | 0.141 / 0.138–0.143 |

† Для `meter_ots_reach`, `meter_ots_reach_by_surface` и `meter_ots_report`
указан контрольный прогон с `Connection: close`: новое HTTP-соединение на каждый
вызов.
The initial benchmark had three connection errors, excluded from the successful-response timings. Nine of nine follow-up legacy calls succeeded with a new HTTP connection per call. The cause of the original failures was not established. Nonzero metrics were checked for the follow-up legacy cases; most other media metric values were not independently audited. A non-error API response alone is not proof of a correct calculation.

## Setting expectations

For a comparable small scenario, simple lookups and calculations were usually under one second; selection and legacy calculations around 1–3 seconds; New OTS around 6–8 seconds; surface/profile breakdowns around 12–15 seconds. Other countries, periods, inventory sizes and load can behave differently. Three samples do not establish a reliable p95 or SLA.

The API's default per-call timeout is 300 seconds, but clients/proxies may stop earlier. Several calls plus file creation take longer than a single API response. Do not describe fast errors, empty results or `no_data` as successful calculation timings. Do not automatically repeat an unchanged timed-out request. A first measurement does not necessarily mean a cold server cache.

These historical measurements are distinct from the release checks documented in [verification](../../../docs/verification.md).
