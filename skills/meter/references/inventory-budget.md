# Inventory quality and budget estimates

Read this for program selection, contradictory surface metadata or a requested campaign budget. METER supplies inventory and projected audience metrics, not operator prices or booking availability. Keep one sourced inventory dataset, the final ID roster and the declared budget model together. Do not reinterpret a budget estimate as a confirmed tariff or an instruction to buy advertising.

## Normalize before selecting

- Preserve the inventory `cntry` ISO alpha-2 country code and original `country` display name. Keep the submitted `countryCode` in campaign parameters; localized names do not override ISO identity. Conflicting duplicate or malformed codes require review.
- Preserve source records and their warnings. Deduplicate by stable METER ID, not by address, coordinates or a physical-construction group: distinct sides/cards can share a location and still be separate API surfaces. Report the counting unit. Complete pagination or label the eligible pool partial/screened.
- Normalize `isDigital` / `is_digital` deliberately: integer `0` and string `"false"` mean false, not truthy. Missing or invalid flags are unknown. A general type such as Billboard or Bus stop alone does not establish static inventory. Explicit LED/digital labels can establish digital evidence; contradictions with a structured flag require review. `Mediafacade` with a false digital flag also requires review, rather than silently selecting a static tariff.
- Preserve dismantled/inactive source markers and exclude affected cards from a proposed buy. A positive active/verified flag or a returned record does not confirm available placement. Retain availability as unconfirmed unless a separate authorized source explicitly confirms it. Negated text such as “не демонтирован” is not a dismantled marker.
- Put unresolved classification or conflicting pricing metadata into a review list; keep it in the source dataset but outside a proposed buying pool. Resolve classification only with a cited source and reason; retain the original contradictory values and warnings. A classification resolution cannot erase dismantled status or unrelated format/address conflicts.
- Parse physical dimensions only when their units are known. The helper supports dimensions in metres; leave units unknown instead of treating a pixel resolution as square metres. Preserve width/height order when matching a format. Missing or inconsistent coordinates produce an unmapped ID and a partial map, not a silently reduced program. Missing dimensions may prevent area-based costing without preventing a valid count-based scenario.

If a new exclusion changes an already calculated program, retain its old result as historical and rerun campaign Reach for the revised exact IDs. Never copy that old Reach onto a cleaned roster. The helper does not decide that an existing deliverable is wrong merely because its source data requires review.

## Choose and disclose the cost model

When the user authorizes an independent budget estimate, proceed with explicit assumptions instead of requesting a fixed budget again. Prefer applicable supplied quotes or authorized local rate data. If neither exists, declare planning assumptions and low/base/high scenarios for the relevant class, format and period; do not call them observed market rates. Keep the model's source/reference, date and basis. There are no built-in tariffs, tax rates, exchange rates or universal size-scaling coefficients in this package.

Match a quoted price to the exact surface ID, OOH/DOOH class, type, physical format and covered dates. Match a DOOH price to the actual purchased schedule/SOV controls; capacity Reach cannot substantiate a one-slot budget. Do not reuse an LED quote for a static card, substitute a static fallback for an unpriced screen, or silently ignore a contradictory exact-ID quote. Estimated category rules may cover several matching cards; a matching explicit-ID rule takes precedence. Multiple equally specific rules require correction.

Specify whether a rate is for the exact campaign, a day or a calendar month. Prorate a monthly rate by covered days in each calendar month only when that billing assumption is supplied; do not divide every month by 30. Currency conversion, if needed, must already be sourced and explained in the input rates. Do not mix currencies or let a reserve stand in for an asserted tax rate.

Separate media, production, installation, creative, fees, tax and reserve. Declare the required/included components and explain omissions. A missing price is unavailable, not zero. A zero charge requires an explicit supported assumption or quote. A total combining estimated and confirmed costs remains estimated. Low/high values are model scenarios, not statistical confidence intervals. A spending cap evaluated against an estimate remains provisional; compare the upper scenario when the user requires protection against that uncertainty.

## Optional local helper

Use the bundled [inventory-budget.py](../scripts/inventory-budget.py) when local Python/file execution is available. It normalizes sourced cards, checks pricing matches, calculates costs with decimal arithmetic and returns a structured JSON dataset. It uses no network, credentials or price feed and does not authenticate quoted sources. Otherwise perform the same checks with available client tools; do not claim the helper ran.

```bash
python3 /path/to/meter/scripts/inventory-budget.py /absolute/artifacts/budget-model.json
```

The example below is a **synthetic executable fixture**, not a suggested price or default budget. Replace the records, amounts, references and assumptions with the task's actual inputs. Copy `campaign.parameters` from the campaign brief: the complete submitted body except `surfaces`. Leave `selected_ids` empty to inspect inventory before selection, retaining fractional extras. Declared required/priced per-surface components are valid dependencies at this stage, but their fractions remain unavailable until there are known amounts; no empty-selection total is bound. `dimension_unit` is `m` only for sourced physical dimensions, otherwise `unknown`. An unknown unit prevents area calculations.

```json
{
  "schema_version": 1,
  "inventory_source_reference": "/absolute/artifacts/inventory.json",
  "model_source_reference": "/absolute/artifacts/budget-model.json",
  "dimension_unit": "m",
  "campaign": {
    "currency": "UZS", "money_decimals": 2,
    "parameters": {
      "city": "Ташкент", "countryCode": "UZ", "periodFrom": "2026-08-01", "periodTo": "2026-08-31",
      "audience": {"age_from": 18, "age_to": 55, "gender": "all", "income": "bc"},
      "blockSize": 0, "chrono": 10, "outputsInBlock": 1, "byDays": false,
      "impressions": [-1], "normalizeCoeff": 0.3, "reachModel": "nbd-dirichlet"
    }
  },
  "records": [{"id": 101, "cntry": "UZ", "country": "Узбекистан", "isDigital": 0, "type": "Billboard", "dimension": "3x6"}],
  "selected_ids": [101], "required_components": ["media"],
  "price_rules": [{
    "match": {"media_class": "static", "type": "Billboard", "dimension": "3x6"},
    "component": "media", "unit": "surface_month", "proration": "calendar_days",
    "amounts": {"low": "100", "base": "120", "high": "150"},
    "status": "estimate", "currency": "UZS", "as_of": "2026-07-01",
    "valid_from": "2026-08-01", "valid_to": "2026-08-31",
    "source_reference": "/absolute/artifacts/synthetic-model.json",
    "basis": "Illustrative test values; not market rates"
  }],
  "extras": []
}
```

`classification_overrides`, when needed, is a list of `{id, media_class, source_reference, reason}`. All original records remain in the output. Every normalized row has classification, status, planning eligibility, unconfirmed availability, dimensions/area when known, map coordinates, review reasons and source warnings. A record's explicit `dimension_unit` takes precedence over the declared dataset unit; pixel/unsupported/conflicting units remain unknown and never become square metres. Use `eligible_ids` for the planning pool only after enforcing the other brief constraints. Use normalized `coordinates` for the map; do not fall back to a conflicting raw coordinate.

Per-surface price rules have a `match`, `component` (`media`, `production`, `installation`), `unit`, `amounts`, `status`, `currency`, validity dates, `as_of`, source and basis. `match` requires `media_class`, `type`, `dimension`; optional `id` makes it specific. A confirmed quote requires the exact ID/type/format and equal low/base/high amounts. `*` is allowed for an estimated dimension or an estimated production/installation type; it is not a confirmed match. Every supplied rule must cover the requested period. Media units are `campaign`, `surface_day`, `surface_month`, `m2_month`; production/installation also support `surface` and `m2`. Monthly units require `proration: "calendar_days"`. An exact-campaign media price requires its validity dates to equal the campaign dates.

For digital media, `priced_controls` must equal the submitted controls among `chrono`, `blockSize`, `outputsInBlock`, `impressions`, `broadcast`, `creatives`, `broadcastRequest`. The first three must be explicit; when `broadcastRequest` is present, use campaign mode `1`. The client must establish that the quote actually covers that slot/schedule, not merely copy the API fields into a price record.

`extras` contain `component` (`creative`, `fees`, `tax`, `reserve`), `unit` (`campaign` or `fraction`), low/base/high `amounts`, status, currency, source and basis. A fraction names unique previously calculated components in `applies_to`; it never implicitly applies to all costs or to itself. Declare tax explicitly if applicable; the helper does not establish legal tax treatment. For required per-surface components, every selected card needs a rate; global required components need a declared extra. Set requirements to the actual budget scope, not merely to hide missing costs.

Output includes line items, component totals, omissions and missing costs. Displayed rounded line amounts reconcile to totals. `total` and `ledger_cost` are absent/null for an empty selection or incomplete required costs; `known_subtotal` is explicitly partial. Fraction extras in that subtotal apply only to the known amounts of already processed components, including components with missing required rates; the missing rates remain listed and prevent a complete total. An undefined, later or self-referential component is invalid. For a complete budget, copy `ledger_cost` into the corresponding [campaign ledger](campaign-planning.md) scenario. It carries the exact ordered IDs, campaign parameters, decimal amount and model reference; the ledger rejects attaching it to a different roster or calculation setup. Preserve its low/high range and estimated status in comparisons and [Excel exports](excel-export.md). Rate changes require recalculating cost; roster/period/audience/schedule changes also require the appropriate campaign calculation.
