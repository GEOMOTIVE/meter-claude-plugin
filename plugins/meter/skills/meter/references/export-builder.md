# Local address-program builder

The maintained builder currently uses Russian worksheet labels. If the user requests another language or a custom template, use the prepared dataset with the client's normal authoring workflow and the export contract. Budget editing supports rate changes in the existing schedule; re-export after adding, removing or reordering cost lines. The project source includes the runtime integration test; it is not installed as part of the user-facing skill.

Use after [campaign planning](campaign-planning.md) and [inventory/budget checks](inventory-budget.md). This helper creates a **new** workbook from an exact final campaign; it does not refresh Reach, resolve inventory conflicts or edit existing workbooks. Preserve unrelated content when using the client's existing-workbook editing workflow.

## Inputs and runtime

Supply the original schema-version-1 campaign ledger with a successful latest `final_validation`, `final_scenario` and stop reason, and the original [inventory/budget model](inventory-budget.md). Preparation invokes [campaign-ledger.py](../scripts/campaign-ledger.py) and [inventory-budget.py](../scripts/inventory-budget.py). Selected IDs must equal the final request's IDs **in order**; parameters and currency must match. For a complete requested budget, record the model's `ledger_cost` on that exact final scenario before exporting. A recorded final cost must match this model and be bound to that request. New prices require an updated bound cost, not a new media calculation when the media request is unchanged. Retain the preceding checkpoint. Partial prices remain partial; `budget_mode: none` omits the budget sheet.

Preparation/verification need Python 3.10+. Maps additionally need Pillow 10.1+ and a local Unicode font for non-ASCII labels. XLSX authoring needs Node.js and the client's available `@oai/artifact-tool`. In Codex follow the spreadsheet skill and dependency loader: copy `address-program.mjs` into a writable task directory and make the host runtime resolvable there. Do not modify the installed plugin or hardcode a user's runtime path. The plugin installs no dependencies. If this runtime is unavailable in another client, use its spreadsheet tools with the prepared data and [export contract](excel-export.md); disclose unsupported file/map features.

Helpers read local JSON and write only new explicitly named local outputs. Existing bundle directories/workbooks are rejected. They never fetch tiles, make network requests, install packages, call METER or send coordinates elsewhere. Retain raw source files separately; workbooks contain selected metadata and references rather than account/session dumps. Source provenance and attribution are client-reported, not authenticated by the helpers.

## Basemap

Supply cached **real**, attributed Web Mercator PNG tiles, 256×256 pixels, named `ZOOM_X_Y.png`. Do not substitute a blank grid, invented roads or a map carrying another program's markers. Example configuration, replacing paths with existing local resources:

```json
{
  "projection": "web_mercator_tiles",
  "zoom": 12,
  "tile_directory": "./cached-tiles",
  "attribution": "© OpenStreetMap contributors",
  "source_reference": "cached-basemap-metadata.json",
  "font_path": "./unicode-font.ttf"
}
```

Paths resolve relative to the configuration. Use the cache's actual zoom/attribution. Bounds include padding and road context, limited to 256 tiles per panel. The overview shows exact points; colliding numbers get detail panels. Shared coordinates retain every ID's number in shared labels or detail panels. Leader lines are at most 48 pixels and identified as label connectors. Each panel retains attribution and table numbering. Enlarging cached tiles adds no street-level detail; use a more detailed local cache when needed.

Missing tiles, renderer/font or coordinates produce partial-map bundles with mapped/selected counts and unmapped IDs. They never remove a surface or invent its location. No basemap argument means an explicitly mapless bundle. Describe either as partial when a complete map was requested.

## Run and verify

Use the scripts' absolute paths from `skills/meter/scripts/` or copied helpers. Keep scratch inputs, previews and output files in the task artifact directory outside the source repository:

```sh
python3 prepare-export.py campaign-ledger.json inventory-model.json export-bundle --basemap basemap.json
node address-program.mjs export-bundle/export.json address-program.xlsx previews
python3 verify-export.py export-bundle/export.json address-program.xlsx
```

Preparation validates before creating the directory. `export.json` retains final-request order, the final result, optional budget lines and hashed map panels. Do not hand-edit it to bypass a rejection. Check `map_complete` and budget status before describing the result.

Visible sheets: **Карта и итог**, **Адресная программа**, and **Бюджет** only when requested. Campaign Reach N+, its own Universe, derived audience, controls and methodology remain visible. Editable low/base/high rates feed rounded amounts, fraction extras and the headline budget. Blank rates propagate as `n.a.`; missing prices cannot become a complete zero-cost campaign. Rate edits do not recalculate Reach; changes to IDs, period, audience or placement controls require a new METER calculation. Costs cover listed components/currency only. Oversized/nonfinite numbers are rejected for Excel precision. IDs are text, coordinates numeric, dates typed; source text is escaped as literal cell data.

The verifier reads this builder's **saved XLSX**, comparing ordered IDs, campaign metrics, coordinates, cost formulas/cached amounts, filters/panes and actual embedded map relationships/bytes. Missing images, external relationships, source text interpreted as formulas and Excel error cells fail. It checks this layout, not arbitrary templates or source authenticity.

Inspect every sheet preview and all map panels at normal scale. Some previews omit images; ZIP relationships and rendered maps establish inclusion, while a native viewer establishes appearance there. Do not claim native Excel recalculation unless tested there. `tests/check-export-runtime.mjs` exercises actual export, rate/blank changes and overwrite rejection with externally supplied paths. Public CI tests preparation/maps/verification; it has no client-specific authoring runtime.
