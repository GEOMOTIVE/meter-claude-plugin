// Host-runtime integration check. All input/output paths are supplied externally.
// node check-export-runtime.mjs <copied-builder.mjs> <export.json> <new-output.xlsx>
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [builder, bundle, output] = process.argv.slice(2);
const { build } = await import(pathToFileURL(path.resolve(builder)).href);
const result = await build(bundle, output, { previewDirectory: path.join(path.dirname(output), 'previews') });
const wb = result.workbook;
const data = result.data;
const summary = wb.worksheets.getItem('Карта и итог');
assert.equal(summary.getRange('B8').values[0][0], data.result.reach_fraction);
if (data.budget?.line_items.length) {
  const b = wb.worksheets.getItem('Бюджет');
  const rateCell = b.getRange('H7');
  const original = rateCell.values[0][0];
  const updated = original + 10;
  const components = new Map();
  const precision = data.budget.campaign.money_decimals ?? 2;
  const round = n => Math.round((n + Number.EPSILON) * 10 ** precision) / 10 ** precision;
  let expected = 0;
  for (const [i, line] of data.budget.line_items.entries()) {
    const qty = line.unit === 'fraction' ? line.applies_to.reduce((n, c) => n + (components.get(c) || 0), 0) : Number(line.quantity ?? 1);
    const cost = round(qty * (i === 0 ? updated : Number(line.rate_amounts.base)));
    components.set(line.component, (components.get(line.component) || 0) + cost);
    expected += cost;
  }
  rateCell.values = [[updated]];
  wb.recalculate();
  assert.ok(Math.abs(b.getRange(`K${result.budgetTotalRow}`).values[0][0] - expected) < 0.00001, 'rate change must update extras and subtotal');
  if (data.budget.budget_complete) assert.ok(Math.abs(summary.getRange('B19').values[0][0] - expected) < 0.00001);
  rateCell.values = [[null]];
  wb.recalculate();
  assert.equal(b.getRange('K7').values[0][0], 'n.a.', 'blank rate must not become zero');
  assert.equal(summary.getRange('B20').values[0][0], 'n.a.', 'blank rate must propagate to known subtotal');
  rateCell.values = [[original]];
  wb.recalculate();
}
await assert.rejects(() => build(bundle, output), /already exists/);
console.log(JSON.stringify({ saved: output, rate_change_recalculated: Boolean(data.budget?.line_items.length), blank_rate_unavailable: Boolean(data.budget?.line_items.length), overwrite_rejected: true }));
