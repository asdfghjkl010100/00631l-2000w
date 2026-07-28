const assert = require('node:assert/strict');
const fs = require('node:fs');
const html = fs.readFileSync('frontend/index.html', 'utf8');

assert.match(html, /let monthlyReturn = null/);
assert.match(html, /Date\.now\(\) \+ 24 \* 60 \* 60 \* 1000/);
assert.match(html, /const dcaValue = cumShares > 0 && current0050Price > 0/);
assert.doesNotMatch(html, /new Date\('2026-12-01/);
console.log('frontend regression checks passed');
