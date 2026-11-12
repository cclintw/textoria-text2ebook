#!/usr/bin/env node
// Exercise the search UI without fetch, a server, or browser-global network APIs.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const script = fs.readFileSync(path.join(__dirname, '../themes/default/static/js/search.js'), 'utf8');
function setup(indexScript) {
  const fields = Object.fromEntries(['q', 'results', 'activeSearchTerms'].map(id => [id, {
    value: '', innerHTML: '', textContent: '', listeners: {},
    addEventListener(event, fn) { this.listeners[event] = fn; }
  }]));
  const context = vm.createContext({window: {}, document: {
    getElementById: id => fields[id], addEventListener() {}, querySelectorAll: () => []
  }});
  if (indexScript) vm.runInContext(indexScript, context);
  vm.runInContext(script, context);
  return {fields, query(term) { fields.q.value = term; fields.q.listeners.input(); return fields.results.innerHTML; }};
}
const fixture = {paragraphs: [
  {paragraph_id: 'p1', division_title: '卷一', paragraph_index: 1, text: '白馬寺在洛陽。', href: 'read/div1.html#p1'},
  {paragraph_id: 'p2', division_title: '卷二', paragraph_index: 2, text: '白馬寺 <img src=x onerror=alert(1)>。', href: 'read/div2.html#p2'}
]};
const ui = setup('window.TEXTORIA_SEARCH_INDEX = ' + JSON.stringify(fixture) + ';');
const results = ui.query('白馬寺');
assert.match(results, /共找到.*>2<.*筆/);
assert.match(results, /href="read\/div1.html#p1"/);
assert.match(results, /<mark>白馬寺<\/mark>/);
assert.ok(!results.includes('<img src=x'));
assert.match(results, /&lt;img/);
assert.match(ui.query('不存在的字詞'), /共找到.*>0<.*筆/);
assert.equal(ui.query(''), '');
const missing = setup();
assert.match(missing.fields.results.textContent, /搜尋資料遺失/);
missing.query('白馬寺');
assert.equal(missing.fields.results.innerHTML, '');
if (process.argv[2]) {
  const site = path.resolve(process.argv[2]);
  const generated = setup(fs.readFileSync(path.join(site, 'data/search_index.js'), 'utf8'));
  const data = JSON.parse(fs.readFileSync(path.join(site, 'data/search_index.js'), 'utf8').trim().slice('window.TEXTORIA_SEARCH_INDEX = '.length, -1));
  const term = [...data.paragraphs[0].text].slice(0, 3).join('');
  const expected = data.paragraphs.filter(row => row.text.includes(term)).length;
  assert.ok(generated.query(term).includes('>' + expected + '</span> 筆'));
}
console.log('PASS: script-loaded index, Chinese matches, escaped markup, anchors, empty/no matches and missing-index handling; no fetch available');
