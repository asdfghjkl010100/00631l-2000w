const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('frontend/index.html', 'utf8');
const source = fs.readFileSync('frontend/financial.js', 'utf8');
const context = { window: {}, Math, Date };
vm.runInNewContext(source, context);
const { navMetrics, goalScenarios, nextTradingDate } = context.window.Financial;

const rows = [
  { d: '2025/12/21', dk: 20251221, n: 10 },
  { d: '2025/12/28', dk: 20251228, n: 10 },
  { d: '2026/01/04', dk: 20260104, n: 10 },
];
assert.equal(navMetrics(rows, 0.015).annualReturn, 0);
assert.equal(navMetrics(rows, 0.015).sharpe, 0);
assert.match(html, /AbortController\(\)/);
assert.match(html, /15000/);
assert.match(html, /資料來源尚未同步/);
assert.match(html, /實際現金流日期/);
assert.equal(nextTradingDate('2026/07/04', {'2026/07/06': 10}), '2026/07/06');
assert.equal(nextTradingDate('2026/07/04', {'2026/07/03': 10}), null);
assert.equal(goalScenarios(1000, 100).length, 3);
console.log('frontend financial regression checks passed');
