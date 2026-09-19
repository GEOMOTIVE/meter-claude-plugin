# METER metric semantics

Use these meanings and the selected response's units when interpreting API results.

- **OTS (Opportunity to See):** modeled/projected advertising contacts in a surface's visibility zone. Repeated contacts are included; OTS is not unique people or verified views.
- **LTS (Likelihood to See):** modeled likelihood of visual contact. Factors can include distance, movement direction, speed and dwell time. This does not imply that the plugin exposes those underlying observations or exports them.
- **Universe:** projected audience size for the selected geography, audience and calculation methodology. A standalone `meter_universe` result may differ from the Universe in an OTS/Reach response; retain each response's denominator.
- **Rating:** inspect the response's scale. `OTS / Universe` is an unscaled ratio; multiplying that ratio by 100 produces percentage points. Do not label an unscaled returned `rating` as percentage GRP or assume the field is already multiplied by 100. If deriving a scaled value, label it as calculated and show the formula and response-specific Universe.
- **Reach N+:** projected unique audience with at least N contacts. If returned as a fraction, multiply by 100 for percent; do not multiply a value already expressed in percent again. For estimated people, multiply the fraction by the Universe from that same calculation (or divide a percentage by 100 first). Label converted counts as approximate projected people.
- **Frequency:** average contact repetition among reached audience when returned by the selected calculation.
- **Spectrum:** distribution of audience by contact frequency; retain the response's units.

For example, a Reach fraction of `0.085` represents `8.5%`; with that response's Universe of `1,000,000`, it represents approximately `85,000` projected unique people. Do not use an independently calculated Universe to convert it. Never sum per-surface Reach to obtain campaign Reach: the same person can encounter several surfaces. Request campaign Reach separately with the same audience, dates, complete surface list and campaign controls.

METER metrics are extrapolated from panel devices to the population using weights or projection factors. Describe them as modeled or projected unless the response explicitly identifies a directly observed value. Scheduled ad plays are a separate quantity from OTS and unique Reach.

Common audience dimensions include age, gender, income, residency, and available behavioral or interest segments. Income categories in internal METER data commonly use A (lower quartile), B (middle 50%), C (upper quartile), or combined `abc`. Preserve the audience requested by the user. These aggregate planning dimensions do not provide personal tracking, footfall, device, dwell-time, visit or movement-flow exports.
