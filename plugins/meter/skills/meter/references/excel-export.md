# Address-program spreadsheet

Create a workbook only from validated inventory and calculation results. Use the user's language. Default to two sheets: Summary and Address program.

## Summary

Record city/country, period, audience, inventory count, Universe, OTS, requested Reach N+, methodology, and whether a value is projected or unavailable. Scheduled ad plays must have a separate label from OTS. Explain unmet targets and missing data. Do not claim the target was achieved unless the returned calculation supports it.

## Address program

Use columns for sequence number, METER ID (text), address, operator, type/format, OOH/DOOH, and returned OTS/LTS where available. Leave absent fields unavailable rather than inventing values. Use filters, a frozen header, wrapped addresses and readable widths. Derive all row ranges from the actual unique-ID count.

Use the METER palette: plum #390050, purple #780DA3, background #FBFAFC, text #08020B. Bundled wordmarks are at `../../../assets/meter-logo.svg` and `../../../assets/meter-logo-white.svg` relative to this reference file.

If a map is useful and available, use sourced coordinates and an attributed basemap. Do not transmit campaign/coordinate data to external map services without authorization. If no suitable map tool is available, omit the map and say so. Monitoring/clutter/permit-owner data are not provided by this plugin.

## Verification

- The final unique-ID list must match the list sent for campaign Reach. Recalculate after changing the list.
- Never sum individual Reach values. Check Reach percentages are 0–100 and Reach 1+ >= Reach 3+ >= Reach 5+ when available.
- Reconcile table count and summary count. Preserve reporting period and methodology.
- Verify formulas, missing values, readability and that the workbook opens without repair. Include no external workbook links or hidden credentials.
- Deliver the actual XLSX; if file creation is unavailable, say so and deliver a table instead.
