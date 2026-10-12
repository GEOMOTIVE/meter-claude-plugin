// Host-runtime integration check. All input/output paths are supplied externally.
// node check-export-runtime.mjs <copied-builder.mjs> <export.json> <new-output.xlsx> <verify-export.py> <python>
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [builder, bundle, output, verifier, python] = process.argv.slice(2);
assert.ok(builder && bundle && output && verifier && python, 'builder, bundle, output, verifier and Python paths required');
const stdinImport = spawnSync(process.execPath, ['--input-type=module', '-'], {
  input: `await import(${JSON.stringify(pathToFileURL(path.resolve(builder)).href)}); console.log('imported');`, encoding: 'utf8',
});
assert.equal(stdinImport.status, 0, stdinImport.stderr);
assert.equal(stdinImport.stdout.trim(), 'imported', 'import must not execute the CLI');
const { build } = await import(pathToFileURL(path.resolve(builder)).href);
const result = await build(bundle, output, { previewDirectory: path.join(path.dirname(output), 'previews') });
const wb = result.workbook;
const data = result.data;
const summary = wb.worksheets.getItem('Карта и итог');
assert.equal(summary.getRange('B8').values[0][0], data.result.reach_fraction);
assert.equal(summary.getRange('B21').values[0][0], data.result.ots ?? 'n.a.');
assert.equal(summary.getRange('B22').values[0][0], data.result.lts ?? 'n.a.');
assert.equal(summary.getRange('B24').values[0][0], data.limitations.join('\n'));
assert.equal(summary.getRange('B25').values[0][0], data.summary.stop_reason);
const addresses = wb.worksheets.getItem('Адресная программа');
for (const [i, row] of data.rows.entries()) {
  assert.equal(addresses.getRange(`M${i + 6}`).values[0][0], row.metrics?.ots ?? 'n.a.');
  assert.equal(addresses.getRange(`N${i + 6}`).values[0][0], row.metrics?.lts ?? 'n.a.');
}
const verifySaved = file => {
  const checked = spawnSync(python, ['-B', verifier, bundle, file], { encoding: 'utf8' });
  assert.equal(checked.status, 0, checked.stderr || checked.stdout);
  return JSON.parse(checked.stdout);
};
const saved = verifySaved(output);
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
// A directory symlink reproduces /tmp -> /private/tmp on every host.
const linkRoot = await fs.mkdtemp(path.join(path.dirname(output), 'cli-symlink-'));
try {
  const linked = path.join(linkRoot, 'linked');
  await fs.symlink(await fs.realpath(path.dirname(builder)), linked, 'dir');
  const cliOutput = path.join(linkRoot, 'cli.xlsx');
  const cli = spawnSync(process.execPath, [path.join(linked, path.basename(builder)), bundle, cliOutput], { encoding: 'utf8' });
  assert.equal(cli.status, 0, cli.stderr);
  // The host authoring runtime may emit diagnostics before the CLI result.
  assert.equal(JSON.parse(cli.stdout.trim().split('\n').at(-1)).file, cliOutput, 'CLI must execute, not silently succeed');
  verifySaved(cliOutput);
} finally { await fs.rm(linkRoot, { recursive: true, force: true }); }
console.log(JSON.stringify({ saved: output, verification: saved, symlink_cli_verified: true, rate_change_recalculated: Boolean(data.budget?.line_items.length), blank_rate_unavailable: Boolean(data.budget?.line_items.length), overwrite_rejected: true }));
