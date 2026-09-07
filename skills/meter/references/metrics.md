# METER metric semantics

Use these meanings when interpreting API responses.

- **OTS (Opportunity to See):** modeled advertising contacts while people are in a surface's visibility zone. It is a contact count, not a count of unique people.
- **LTS (Likelihood to See):** modeled likelihood of actual visual contact. The model accounts for factors such as distance, movement direction, speed, and dwell time.
- **Universe:** projected size of the audience matching the selected geography and demographic filters.
- **Rating:** OTS divided by Universe, multiplied by 100.
- **Reach N+:** projected audience with at least N contacts. Reach is unique audience; OTS counts contacts.
- **Frequency:** average contact repetition among the reached audience when returned by the selected calculation.
- **Spectrum:** distribution of audience by contact frequency.

METER metrics are extrapolated from panel devices to the population using weights or projection factors. Describe them as modeled or projected unless the response explicitly identifies a directly observed value.

Common audience dimensions include age, gender, income, residency, and available behavioral or interest segments. METER income categories use A (lower quartile), B (middle 50%), C (upper quartile), or combined `abc`.
