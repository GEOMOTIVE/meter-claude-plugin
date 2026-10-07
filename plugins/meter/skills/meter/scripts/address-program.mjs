#!/usr/bin/env node
// Run from a writable directory with the host's @oai/artifact-tool available.
import fs from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const require = (condition, message) => { if (!condition) throw new Error(message); };
const text = value => {
  const s = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
  // Inventory descriptions are data. Prevent spreadsheet formula interpretation.
  return /^[=+@'-]/.test(s) ? "'" + s : s;
};
const number = value => { const n = Number(value); require(value !== '' && value != null && Number.isFinite(n) && Math.abs(n) < 1e15, 'invalid or oversized Excel number'); return n; };
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical(v[k])])) : v;
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

export async function build(bundlePath, outputPath, { previewDirectory = null } = {}) {
  require(path.extname(outputPath).toLowerCase() === '.xlsx', 'output must be an XLSX file');
  try { await fs.access(outputPath); throw new Error('output already exists; choose a new file'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  const data = JSON.parse(await fs.readFile(bundlePath, 'utf8'));
  require(data.schema_version === 1 && data.summary.final_confirmed, 'validated final campaign bundle required');
  const ids = data.rows.map(r => r.id);
  require(same(ids, data.summary.best.surface_ids) && new Set(ids).size === ids.length && ids.length > 0, 'bundle roster mismatch');
  require(data.rows.every((r, i) => r.seq === i + 1 && Number.isSafeInteger(r.id)), 'invalid address numbering');
  require(data.result.scope === 'campaign' && data.result.frequency === data.summary.frequency &&
    data.result.reach_fraction >= 0 && data.result.reach_fraction <= 1 && data.result.universe > 0 &&
    Math.abs(data.result.reach_fraction * 100 - data.summary.best.reach_percent) < 1e-10 &&
    data.result.universe === data.summary.best.universe, 'campaign result differs from ledger summary');
  require(same(data.map.mapped_ids, ids.filter(id => data.map.mapped_ids.includes(id))) &&
    same(data.map.unmapped_ids, ids.filter(id => !data.map.mapped_ids.includes(id))) &&
    data.map.complete === (data.map.unmapped_ids.length === 0), 'invalid map coverage');
  const images = [];
  const readable = new Set();
  for (const panel of data.map.panels) {
    require(path.basename(panel.file) === panel.file && panel.file.endsWith('.png'), 'invalid local map filename');
    require(panel.point_ids.every(id => ids.includes(id)) && panel.readable_ids.every(id => panel.point_ids.includes(id)), 'map point IDs differ from roster');
    const bytes = await fs.readFile(path.join(path.dirname(bundlePath), panel.file));
    require(createHash('sha256').update(bytes).digest('hex') === panel.sha256, 'map image changed after preparation');
    require(bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])), 'map must be a PNG');
    require(bytes.readUInt32BE(16) === panel.width && bytes.readUInt32BE(20) === panel.height, 'map dimensions mismatch');
    panel.readable_ids.forEach(id => readable.add(id));
    images.push({ panel, bytes });
  }
  require(same(ids.filter(id => readable.has(id)), data.map.mapped_ids), 'map labels do not cover mapped roster');
  let budgetData = data.budget;
  if (budgetData) {
    require(same(budgetData.selected_ids, ids), 'budget roster mismatch');
    require(budgetData.campaign.currency === data.brief.constraints.currency, 'budget currency mismatch');
    require(same(budgetData.campaign.parameters, data.brief.parameters), 'budget parameters mismatch');
  }
  const { Workbook, SpreadsheetFile } = await import('@oai/artifact-tool');
  const wb = Workbook.create();
  const summary = wb.worksheets.add('Карта и итог');
  const addresses = wb.worksheets.add('Адресная программа');
  const budget = budgetData ? wb.worksheets.add('Бюджет') : null;
  const style = (sheet, range) => {
    sheet.showGridLines = false;
    sheet.tabColor = '#390050';
    sheet.getRange(range).format.font = { name: 'Arial', size: 11, color: '#08020B' };
    sheet.getRange(range).format.verticalAlignment = 'center';
    sheet.getRange(range).format.rowHeight = 24;
  };
  const header = (sheet, range) => {
    sheet.getRange(range).format = { fill: '#390050', font: { name: 'Arial', size: 11, bold: true, color: '#FFFFFF' }, wrapText: true, horizontalAlignment: 'center', verticalAlignment: 'center', rowHeight: 36 };
  };
  const p = data.brief.parameters;
  const audience = p.audience || { age_from: p.ageFrom, age_to: p.ageTo, gender: p.gender, income: p.income };
  const controls = Object.fromEntries(Object.entries(p).filter(([k]) => !['city','periodFrom','periodTo','audience','ageFrom','ageTo','gender','income'].includes(k)));
  const info = [
    ['METER — адресная программа', null],
    ['Город', text(p.city)], ['Период с', new Date(p.periodFrom + 'T00:00:00Z')], ['Период по', new Date(p.periodTo + 'T00:00:00Z')],
    ['Аудитория', text(`${audience.gender}, ${audience.age_from}–${audience.age_to}, ${audience.income}`)],
    ['Поверхности', ids.length], [`Reach ${data.summary.frequency}+ программы`, data.result.reach_fraction],
    ['Universe этого расчёта', data.result.universe], ['Прогноз уникальной аудитории', null],
    ['Метод', text(data.summary.methodology)], ['Параметры кампании', text(controls)],
    ['Карта: нанесено / выбрано', `${data.map.mapped_ids.length} / ${ids.length}`],
    ['ID без читаемой точки на карте', text(data.map.unmapped_ids.join(', ') || 'нет')],
    ['Карта', text(data.map.complete ? 'полная' : 'частичная: ' + data.map.reason)],
    ['Размещение', 'Наличие не подтверждено'],
    ['Оптимизация', 'Лучшая проверенная программа; глобальный максимум не доказан'],
    ['Бюджет', budgetData ? text(budgetData.budget_status) : 'не запрошен'],
    ['Стоимость программы', budgetData ? null : 'не рассчитывалась'],
    ['Известная часть бюджета', budgetData ? null : 'не рассчитывалась'],
  ];
  style(summary, 'A2:N22');
  summary.getRange('A2:B20').values = info;
  summary.getRange('A2').format.font = { name: 'Arial', size: 15, bold: true, color: '#390050' };
  summary.getRange('A3:A20').format.columnWidth = 34;
  summary.getRange('B3:B20').format.columnWidth = 96;
  summary.getRange('B12:B18').format.wrapText = true;
  summary.getRange('B12').format.rowHeight = 56;
  summary.getRange('B15:B17').format.rowHeight = 38;
  for (let r = 12; r <= 18; r++) summary.getRange(`B${r}`).format.rowHeight = Math.max(38, Math.ceil(String(info[r - 2][1]).length / 85) * 18 + 12);
  summary.getRange('B4:B5').setNumberFormat('yyyy-mm-dd');
  summary.getRange('B8').setNumberFormat('0.00%');
  summary.getRange('B9:B10').setNumberFormat('#,##0');
  summary.getRange('B10').formulas = [['=B8*B9']];
  const start = 6, last = start + ids.length - 1;
  style(addresses, `A2:L${last + 1}`);
  addresses.getRange('A2').values = [['Адресная программа']];
  addresses.getRange('A2').format.font = { name: 'Arial', size: 15, bold: true, color: '#390050' };
  addresses.getRange('A3').values = [[text(`METER: ${data.rows[0].source_reference}; расчёт: ${data.result.source_reference}; ${data.result.calculated_at}`)]];
  addresses.getRange('A5:L5').values = [['№','ID','Адрес','Оператор / ID','Тип','Формат','OOH / DOOH','Сторона','Предупреждения','Наличие','Широта','Долгота']];
  header(addresses, 'A5:L5');
  addresses.getRange(`A${start}:L${last}`).values = data.rows.map(r => [r.seq, text(r.id), text(r.metadata.address || 'нет адреса в источнике'), text(r.metadata.supplierId), text(r.metadata.type), text(r.metadata.dimension), r.media_class === 'digital' ? 'DOOH' : 'OOH', text(r.metadata.side), text(r.warnings.join('; ')), 'не подтверждено', r.coordinates?.lat ?? null, r.coordinates?.lng ?? null]);
  const widths = [6,16,62,20,20,15,14,10,52,22,14,14];
  widths.forEach((w, i) => addresses.getRangeByIndexes(4, i, ids.length + 1, 1).format.columnWidth = w);
  addresses.getRange(`B${start}:B${last}`).setNumberFormat('@');
  addresses.getRange(`C${start}:J${last}`).format.wrapText = true;
  addresses.getRange(`A${start}:L${last}`).format.rowHeight = 52;
  data.rows.forEach((r, i) => addresses.getRange(`A${start + i}:L${start + i}`).format.rowHeight = Math.max(52, Math.ceil(Math.max(String(r.metadata.address || '').length / 55, r.warnings.join('; ').length / 45)) * 17 + 14));
  addresses.getRange(`K${start}:L${last}`).setNumberFormat('0.000000');
  addresses.freezePanes.freezeRows(5);
  addresses.freezePanes.freezeColumns(2);
  const addressTable = addresses.tables.add(`A5:L${last}`, true, 'AddressProgram');
  addressTable.style = 'TableStyleLight1';
  addressTable.showFilterButton = true;
  let totalRow = null;
  if (budget) {
    const lines = budgetData.line_items;
    style(budget, `A2:R${lines.length + budgetData.missing_costs.length + 16}`);
    budget.getRange('A2').values = [[`Бюджет, ${budgetData.campaign.currency}`]];
    budget.getRange('A2').format.font = { name: 'Arial', size: 15, bold: true, color: '#390050' };
    budget.getRange('A3').values = [['Синие ставки редактируются. Изменение ID, периода, аудитории или размещения требует нового расчёта METER.']];
    budget.getRange('A4').values = [[text(`Статус: ${budgetData.budget_status}; не включено: ${budgetData.not_included_components.join(', ')}. Low / Base / High — сценарии модели.`)]];
    budget.getRange('A6:R6').values = [['ID','Компонент','Единица','База Low','База Base','База High','Ставка Low','Ставка Base','Ставка High','Сумма Low','Сумма Base','Сумма High','Статус','Источник','Основание','Дата цены','Действует с','Действует по']];
    header(budget, 'A6:R6');
    const componentRows = new Map();
    const precision = budgetData.campaign.money_decimals ?? 2;
    const fmt = precision ? '#,##0.' + '0'.repeat(precision) : '#,##0';
    lines.forEach((line, index) => {
      const r = index + 7;
      const quantities = line.unit === 'fraction' ? [null,null,null] : Array(3).fill(number(line.quantity ?? 1));
      budget.getRange(`A${r}:R${r}`).values = [
        [line.id == null ? 'программа' : text(line.id), text(line.component), text(line.unit), ...quantities,
          ...['low','base','high'].map(k => number(line.rate_amounts[k])), null,null,null, text(line.status), text(line.source_reference), text(line.basis),
          ...['as_of','valid_from','valid_to'].map(k => line[k] ? new Date(line[k] + 'T00:00:00Z') : null)]
      ];
      if (line.unit === 'fraction') {
        const previous = line.applies_to.flatMap(c => componentRows.get(c) || []);
        require(previous.length > 0, 'fraction extra has no prior component base');
        ['J','K','L'].forEach((amountCol, j) => {
          const refs = previous.map(i => `${amountCol}${i}`).join(',');
          budget.getRange(`${['D','E','F'][j]}${r}`).formulas = [[`=IF(COUNT(${refs})=${previous.length},SUM(${refs}),"n.a.")`]];
        });
      }
      ['J','K','L'].forEach((col, j) => {
        const q = ['D','E','F'][j] + r, rate = ['G','H','I'][j] + r;
        budget.getRange(`${col}${r}`).formulas = [[`=IF(COUNT(${q},${rate})=2,ROUND(${q}*${rate},${precision}),"n.a.")`]];
      });
      if (!componentRows.has(line.component)) componentRows.set(line.component, []);
      componentRows.get(line.component).push(r);
    });
    const lastLine = 6 + lines.length;
    totalRow = lastLine + 2;
    budget.getRange(`A${totalRow}`).values = [['Известная часть']];
    budget.getRange(`A${totalRow + 1}`).values = [['Итого программа']];
    ['J','K','L'].forEach(col => {
      budget.getRange(`${col}${totalRow}`).formulas = [[lines.length ? `=IF(COUNT(${col}7:${col}${lastLine})=${lines.length},SUM(${col}7:${col}${lastLine}),"n.a.")` : '=0']];
      if (budgetData.budget_complete) budget.getRange(`${col}${totalRow + 1}`).formulas = [[`=${col}${totalRow}`]];
      else budget.getRange(`${col}${totalRow + 1}`).values = [['n.a.']];
    });
    budget.getRange(`J${totalRow}:L${totalRow + 1}`).format.font.bold = true;
    if (lines.length) {
      budget.getRange(`G7:I${lastLine}`).format.font.color = '#0000FF';
      budget.getRange(`G7:I${lastLine}`).format.fill = '#FFF5CC';
      budget.getRange(`N7:O${lastLine}`).format.wrapText = true;
      budget.getRange(`A7:R${lastLine}`).format.rowHeight = 44;
      budget.getRange(`P7:R${lastLine}`).setNumberFormat('yyyy-mm-dd');
    }
    budget.getRange(`D7:F${totalRow + 1}`).setNumberFormat('#,##0.0000');
    budget.getRange(`G7:L${totalRow + 1}`).setNumberFormat(fmt);
    [16,19,19,17,17,17,18,18,18,19,19,19,16,48,64,16,16,16].forEach((w, i) => budget.getRangeByIndexes(5, i, Math.max(lines.length, 1), 1).format.columnWidth = w);
    budget.freezePanes.freezeRows(6);
    budget.freezePanes.freezeColumns(2);
    budget.getRange(`A${totalRow + 3}`).values = [[text('Недостающие цены: ' + (budgetData.missing_costs.map(m => `${m.id ?? 'программа'} / ${m.component}: ${m.reason}`).join('; ') || 'нет'))]];
    summary.getRange('B19').formulas = [[`='Бюджет'!K${totalRow + 1}`]];
    summary.getRange('B20').formulas = [[`='Бюджет'!K${totalRow}`]];
    summary.getRange('B19:B20').setNumberFormat(fmt);
  }
  let imageRow = 22;
  for (const { panel, bytes } of images) {
    summary.images.add({ dataUrl: 'data:image/png;base64,' + bytes.toString('base64'), anchor: { from: { row: imageRow, col: 0 }, extent: { widthPx: panel.width, heightPx: panel.height } } });
    const lastImageRow = imageRow + Math.ceil(panel.height / 32) + 2;
    summary.getRange(`A${imageRow + 1}:N${lastImageRow}`).format.rowHeightPx = 32;
    imageRow = lastImageRow;
  }
  wb.recalculate();
  require(Math.abs(number(summary.getRange('B10').values[0][0]) - data.result.reach_fraction * data.result.universe) < 1e-6, 'Reach people calculation mismatch');
  if (budget && budgetData.line_items.length) {
    for (const [j, k] of ['low','base','high'].entries()) {
      const actual = number(budget.getRange(`${['J','K','L'][j]}${totalRow}`).values[0][0]);
      require(Math.abs(actual - number(budgetData.known_subtotal[k])) < 0.00001, 'budget formula reconciliation failed: ' + k);
    }
  }
  const errors = await wb.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!', options: { useRegex: true, maxResults: 20 }, maxChars: 3000 });
  // Independently validate persisted formulas/values using verify-export.py after export.
  if (previewDirectory) {
    await fs.mkdir(previewDirectory, { recursive: true });
    for (const [sheetName, range, file] of [['Карта и итог','A2:B20','summary.png'],['Адресная программа',`A5:J${Math.min(last, 11)}`,'addresses.png'], ...(budget ? [['Бюджет', `A6:M${Math.min(totalRow + 1, 15)}`, 'budget.png']] : [])]) {
      const image = await wb.render({ sheetName, range, scale: 1.4 });
      await fs.writeFile(path.join(previewDirectory, file), new Uint8Array(await image.arrayBuffer()));
    }
  }
  const xlsx = await SpreadsheetFile.exportXlsx(wb);
  // Reserve atomically; two concurrent invocations must not overwrite an output.
  const staging = await fs.mkdtemp(path.join(path.dirname(outputPath), '.meter-export-'));
  try {
    const temporary = path.join(staging, 'program.xlsx');
    await xlsx.save(temporary);
    await fs.writeFile(outputPath, await fs.readFile(temporary), { flag: 'wx' });
  } finally { await fs.rm(staging, { recursive: true, force: true }); }
  return { workbook: wb, data, budgetTotalRow: totalRow, formulaInspection: errors.ndjson, outputPath };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const [bundle, output, previewDirectory] = process.argv.slice(2);
  if (!bundle || !output) { console.error('Usage: node address-program.mjs export.json output.xlsx [preview-directory]'); process.exitCode = 2; }
  else try {
    const result = await build(bundle, output, { previewDirectory });
    console.log(JSON.stringify({ file: result.outputPath, surfaces: result.data.rows.length, map_complete: result.data.map.complete }));
  } catch (error) { console.error('Cannot build XLSX: ' + error.message); process.exitCode = 2; }
}
