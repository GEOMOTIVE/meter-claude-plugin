# Campaign Reach planning

Use this workflow when selecting an effective address program, maximizing Reach N+, or answering whether an existing program is the most effective. The connected tools calculate campaigns and rank inventory; they do not expose a global campaign optimizer. Use campaign calculations to search and compare feasible programs. Never describe the highest individual-surface Reach ranking as the optimal campaign.

## Persist the brief before searching

Keep a local JSON brief and scenario ledger in the client's artifact directory, outside a source checkout. Carry them across turns and reuse valid calculations within this task. Record city/country, inclusive dates, complete audience, requested campaign Reach frequency, methodology/tool, every submitted campaign control, maximum surface count, required/excluded IDs, and budget policy. Preserve other supplied constraints, such as formats or districts, in the brief and enforce them when building the eligible pool. Do not store credentials or account selectors.

Interpret “Reach 5+” as the projected unique audience with at least five contacts across the **complete program**. “At most 80 surfaces” is an upper bound, not a requirement to fill 80 rows. “Estimate the budget yourself” authorizes a disclosed cost estimate; it does not supply a hard spending cap or change a maximum-Reach objective into lowest cost. Do not ask again for those already supplied decisions. If both a spending cap and a count limit are missing and materially affect the search, ask for one while preparing inventory and a labeled baseline. Keep missing availability and estimated prices visible.

Store the exact model-facing tool arguments that were submitted, even when the API echo is empty. Use [api-routing.md](api-routing.md) for methodology, schema differences and assumptions. Campaign mode and the priced schedule must match: for New OTS broadcast-aware campaign planning, explicitly use `broadcastRequest: 1`. A full-capacity result cannot substantiate Reach for a purchased DOOH slot. Compare only requests with the same audience, period, methodology and schedule; disclose separate schedule alternatives as separate comparisons. Preserve the order of IDs when arguments contain aligned arrays.

## Search complete programs

1. Finish inventory pagination or explicitly label the pool partial/screened. Normalize status/classification and any requested costs using [inventory-budget.md](inventory-budget.md). Deduplicate stable surface IDs, preserve warnings, exclude known dismantled/inactive records from a proposed buy, and record each exclusion. Apply the brief's eligibility constraints before searching. A returned record still does not confirm booking availability. Per-surface OTS/Reach and geographic spread may help generate candidates; neither proves the campaign objective.
2. Calculate several feasible starting programs from different selection rules, such as contact ranking and geographic spread. Include smaller programs when the brief sets only a maximum count. Use price-based seeds only when a defensible cost source or disclosed estimation model exists. Evaluate the requested campaign Reach N+ for each **whole ID list**; do not sum individual Reach, average it, or optimize Reach 1+ as a proxy for Reach 5+.
3. Improve promising starts with additions, removals and replacements within the constraints. Test some group replacements as well as single swaps: Reach 5+ can depend on accumulating contacts across several surfaces, so a one-swap plateau is not proof of optimality. Do not invent an overlap matrix, use map distance as measured audience overlap, or assume the objective has a greedy optimality guarantee.
4. Before a new call, check its request identity against the ledger. Reuse a successful identical task calculation instead of repeating it during selection. Save each actual attempt, result reference, timestamp, units, warnings and any cost/status; count failures in the workload. Keep `no_data` and errors distinct from zero Reach. Follow [performance.md](performance.md) for timeouts. Set and disclose a bounded evaluation budget, retain the best feasible result, and record whether the search ended because of that budget, tested-neighborhood exhaustion, failure or user interruption. Do not estimate total runtime from lookup timings alone.
5. If permitted coverage fallback changes the methodology, create a new brief/comparison ledger and rerun the shortlisted alternatives under that methodology. Do not rank legacy and New OTS rows together. A changed audience, period, objective, eligibility pool or controls also creates a new comparison; never relabel old results.
6. Once selection is settled, make one fresh campaign calculation for the exact final IDs and unchanged brief. Record it as final validation. If it fails or changes the winner, retain the prior checkpoint, explain the limitation and resolve the discrepancy before claiming a verified final recommendation. Use its own Universe for any derived people count. Export that same final roster and result using [excel-export.md](excel-export.md).

Report “best among the tested feasible programs,” the requested campaign Reach N+, count, budget status, methodology/controls, pool size/coverage, number of unique programs and actual calculation attempts, and stopping reason. A global-optimum claim requires an actual proof or exhaustive search of the stated feasible space; none is provided by this workflow. An economy alternative is useful when requested or when it explains a material Reach/cost tradeoff, but estimated price differences cannot establish proven cost efficiency.

## Local ledger check

When local Python/file execution is available, use the bundled [campaign-ledger.py](../scripts/campaign-ledger.py). It validates the brief against the exact submitted arguments, rejects invalid/noncomparable results and selects the best of the recorded successful feasible programs. It does not call METER, generate candidates, verify backend accuracy, confirm availability or prove optimality. Otherwise apply the same checks with available client tools and retain the ledger; do not present the missing helper as a connection failure.

Run with the actual installed script path and an absolute artifact path:

```bash
python3 /path/to/meter/scripts/campaign-ledger.py /absolute/artifacts/campaign.json
```

The JSON structure is below. Values illustrate an assumed legacy setup; copy the user's actual brief and current tool schema instead of treating this as API defaults. `parameters` is the full submitted body except `surfaces`. Include all additional supplied filters/controls. A scenario's `request` is the full submitted body. The helper compares it exactly, including optional fields and array order. Append every actual attempt; use `planned` to validate a candidate before calling. `evaluation_limit` bounds search calls; account for final validation calls separately and reserve time for one. In a completed ledger set `stop_reason` and `final_scenario` to the successful final attempt's unique name.

```json
{
  "schema_version": 1,
  "brief": {
    "country": "Uzbekistan",
    "tool": "meter_ots_reach",
    "parameters": {
      "city": "Ташкент",
      "periodFrom": "2026-08-01",
      "periodTo": "2026-08-31",
      "audience": {"age_from": 18, "age_to": 55, "gender": "all", "income": "bc"},
      "blockSize": 0, "chrono": 10, "outputsInBlock": 1,
      "byDays": false, "impressions": [-1], "normalizeCoeff": 0.3,
      "reachModel": "nbd-dirichlet"
    },
    "objective": {"metric": "campaign_reach_n_plus", "frequency": 5},
    "constraints": {"max_surfaces": 80, "budget_limit": null, "currency": "UZS", "required_ids": [], "excluded_ids": []},
    "budget_mode": "estimate"
  },
  "inventory": {"eligible_ids": [101, 102], "coverage": "screened", "source_reference": "/absolute/artifacts/inventory.json"},
  "search": {"evaluation_limit": 40, "stop_reason": null},
  "scenarios": [],
  "final_scenario": null
}
```

For each scenario store `name`, `tool`, `request`, `status` (`planned`, `ok`, `no_data`, `error`), and `purpose` (`search` or `final_validation`). For `ok`, `result` requires `scope: "campaign"`, `frequency` matching the objective, `reach_fraction` in [0,1], positive `universe`, an ISO timestamp with timezone in `calculated_at`, and `source_reference` for the retained response. Convert an API percentage to a fraction once; identify the requested **cumulative N+** value using the response contract, not an assumed array position. A zero Reach with valid positive Universe remains a valid result; zero/absent Universe cannot support this comparison. Retain source warnings and exclusions beside the referenced data.

For `no_data` or `error`, retain a `failure` object with a timezone-aware ISO `recorded_at` timestamp and `source_reference` to the retained response/error log; do not add a numeric media `result`. References identify client artifacts; the helper does not independently authenticate their content or the source calculation.

An optional `cost` has nonnegative `amount`, matching `currency`, and `status` (`estimate` or `confirmed`). Prefer the bound `ledger_cost` from the inventory/budget helper: its `surface_ids` and `campaign_parameters` must match the exact request, and `source_reference` identifies the model. Its optional `amount_decimal` must equal the numeric amount without precision loss. Earlier unbound cost records remain readable but are labeled as lacking that request binding. A hard budget limit requires a cost for each planned or successful candidate; mark feasibility under estimates as provisional. Costs never override the Reach objective. Do not label a mixed estimate/confirmed total as confirmed.

The helper emits hashes for the brief/comparison and each request, counts of attempts, distinct requests and distinct ID rosters, the best scenario and its verified percent/people conversion, cost/coverage limitations, and whether its exact final attempt is confirmed. Object-key order is irrelevant; surface and schedule array order remains significant. After a repeated attempt, the latest outcome for that request governs recommendation eligibility; earlier responses remain in the ledger for investigation. A final calculation is a deliberate validation call, separate from avoiding duplicate calls during search.
