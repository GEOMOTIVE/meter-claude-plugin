# Address-program spreadsheet

Use this reference for an Excel/XLSX address program or client-ready spreadsheet. Follow the client's spreadsheet-authoring skill when available. Preserve the user's language, requested columns and layout. The public plugin supplies inventory and projected audience calculations; it does not supply monitoring, clutter, permit-owner information, bookable availability or operator prices.

## One validated campaign dataset

Prepare one normalized dataset before authoring. Use it for the summary, table, formulas and map:

- Campaign: city/country, reporting period, requested audience, category when supplied, requested Reach N+, actual methodology and campaign controls.
- Calculation: the complete submitted surface-ID list, that calculation's Universe, projected OTS/LTS and campaign Reach; retain unavailable results as unavailable.
- Selected rows: stable METER ID, sequence number, sourced address, operator, type/format, OOH/DOOH, coordinates, source warnings and returned metrics where available.
- Budget, only when requested: sourced rates or an explicitly labeled estimation model, currency, date/basis and assumptions. Estimates are not confirmed operator tariffs. Keep media, production/installation and any tax, fees or reserve assumptions identifiable.

Validate unique IDs and finish inventory pagination before using a list as the final program. Distinguish inventory cards/sides from physical constructions; do not silently change what the count means. Retain dismantled/inactive warnings with affected rows and explain exclusions. A returned record does not confirm availability.

The final IDs must equal the IDs submitted for the reported campaign Reach. If selection changes, rerun campaign Reach with the same brief and controls or label that result unavailable. A validated model output remains a projection, not observed campaign delivery. Never imply global optimality merely because a program was calculated or won a limited scenario comparison.

## Workbook layout

Default to two visible sheets, named in the user's language:

1. **Map and summary:** campaign and audience, inventory count, projected OTS/LTS, the requested campaign Reach N+, actual methodology and controls, a large map, and a short decision/limitations paragraph. Include budget and its status when requested. Separate scheduled ad plays from OTS. Do not claim an unmet or unavailable target was achieved.
2. **Address program:** sequence number, METER ID stored as text, address, operator, type/format, OOH/DOOH, available OTS/LTS, and relevant source warnings. Add requested cost/availability fields without inventing them. Use filters, frozen headers and identifier columns, wrapped addresses and readable widths. Keep coordinates as helper columns unless the user wants them visible.

Add budget/scenario or audit sheets only when they serve the requested deliverable. Preserve existing workbook structure when editing an export; add the requested map without reorganizing unrelated sheets.

Use the METER palette: plum `#390050`, purple `#780DA3`, background `#FBFAFC`, text `#08020B`, and a portable font such as Arial. Use bundled wordmarks when the client has access to the package assets. Derive all row ranges from the actual unique-ID count.

## City map

Include a map in a client-ready XLSX address program unless the user explicitly requests a table-only export. Create it before final delivery; do not defer an available map to an optional follow-up.

- Use sourced latitude/longitude and a real, attributed city basemap. Do not infer coordinates from an address, draw invented roads or substitute an unlabeled scatter plot.
- Plot every selected surface. Number points to match the table's sequence column; keep exact coordinates visible even when several records share a location. Fit bounds with padding.
- Use purple markers with a white halo. Use numbers instead of printing full addresses. For dense areas, add enlarged detail panels; every point number must remain identifiable in at least one panel. Do not hide selected records inside unexplained static clusters.
- If a number must move to avoid overlap, connect it to the exact point with a short leader line and explain that line in the legend. These lines are not routes or connections between constructions.
- Include the campaign period, numbering legend and basemap attribution. Do not add competitor heatmaps or category clutter without an available authorized source; the public METER tools do not provide those datasets.
- Prefer a local or cached basemap. Do not send campaign, coordinate or account data to external map services without authorization. The plugin does not install a map renderer; use a suitable available local renderer and embed its image in the workbook.

If a map cannot be made, identify the concrete missing input or capability and mark the export partial. For missing coordinates on some rows, show mapped/selected counts and list the unmapped IDs. Keep those rows and the original campaign result; do not remove selected surfaces merely to make map counts agree. Never invent points or claim that an incomplete map covers the whole program.

## Metrics, formulas and budget

Use [metrics.md](metrics.md) for units. Show OTS/LTS as projected contacts with thousands separators, and Reach as a percentage. Derive people only after verifying `reach_fraction × calculation_universe`. Never sum individual Reach values to obtain campaign Reach. Check `0 ≤ Reach ≤ 100%` and `Reach 1+ ≥ Reach 3+ ≥ Reach 5+` when those results are available.

Use formulas for editable budget calculations and totals. Editing rates changes budget, not the stored METER audience result. Editing surfaces, period, audience or campaign controls requires a new METER calculation. Explain this distinction in a workbook with editable inputs.

Keep confirmed prices, estimates and unavailable costs distinct. Use [inventory-budget.md](inventory-budget.md) for matching rates, billing units, component totals and ranges. When the user asks for an estimate, disclose its model and assumptions rather than calling it a tariff. Do not present an arbitrary reserve as an established tax rate. Show missing prices as unavailable and known subtotals as partial; never turn them into a complete zero-cost budget.

## Verification and delivery

Before delivery:

- Reconcile selected unique IDs, address-table IDs, campaign-request IDs and map point IDs; verify the same sequence-to-ID mapping throughout. For a disclosed partial map, verify its mapped-ID subset and unmapped-ID list against the complete program instead.
- Reconcile counts and available contact totals with the source dataset. Check the first and last address rows; preserve reporting period, audience, methodology and controls.
- Inspect formulas and errors, missing values and actual readability. Keep source warnings and price status visible.
- Render the map and affected sheets for visual review. Confirm that the map is embedded and readable in the exported XLSX, not merely stored beside it. Some spreadsheet previews omit worksheet images: check the archive's image/drawing relationships and, when available, open it in a spreadsheet viewer.
- Confirm the workbook opens without repair and contains no external workbook links or hidden credentials. Do not present debug sheets or intermediate previews as the deliverable.

Deliver the actual XLSX. State any missing map, calculation or price data. If file creation is unavailable, provide a labeled table and say explicitly that no XLSX was produced.
