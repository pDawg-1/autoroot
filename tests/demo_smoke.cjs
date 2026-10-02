// Exercise the exported report's controls without external browser dependencies.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(process.argv[2]||'site/index.html', 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    const classes=new Set();
    elements.set(id, {value: '', checked: true, textContent: '', innerHTML: '', className: '', dataset: {}, callbacks: {}, classList: {toggle(name,force){const enabled=force===undefined?!classes.has(name):force;if(enabled)classes.add(name);else classes.delete(name);},contains(name){return classes.has(name);}}, addEventListener(name, fn) {this.callbacks[name]=fn;}, click() {this.callbacks.click?.();}});
  }
  return elements.get(id);
}
element('metric').value='revenue';
element('method').value='ensemble';
const tabs=['investigation','scorecard','methodology'].map(id=>{const e=element('tab-'+id);e.dataset.tab=id;return e;});
const dimensions=['region','sku','channel'].map(id=>{const e=element('dim-'+id);e.dataset.dim=id;return e;});
const plots=new Map();
const context=vm.createContext({console,Blob,URL,setTimeout,document:{getElementById:element,querySelectorAll:q=>q==='[data-tab]'?tabs:dimensions,createElement:()=>element('download-link')},Plotly:{react:(id,data,layout)=>plots.set(id,{data,layout}),Plots:{resize(){}}}});
vm.runInContext(script,context);
assert.ok(!element('effects').classList.contains('hidden'));
assert.ok(element('effects-unavailable').classList.contains('hidden'));
assert.match(element('narrative').textContent,/Validate/);
assert.ok(element('alerts').textContent>0);
assert.match(element('holdout').innerHTML,/85\.0%/);
assert.ok(plots.get('timeline').data[0].x.length>=104);
element('metric').value='units';element('metric').callbacks.change();
assert.ok(element('effects').classList.contains('hidden'));
assert.ok(!element('effects-unavailable').classList.contains('hidden'));
assert.ok(element('alerts').textContent>0);
assert.match(element('holdout').innerHTML,/82\.9%/);
element('only-alerts').checked=false;element('only-alerts').callbacks.change();
assert.ok((element('week').innerHTML.match(/<option/g)||[]).length>=78);
element('week').value='2024-01-29';element('week').callbacks.change();
assert.match(element('narrative').textContent,/West/);
assert.equal(element('decision-issue').textContent,'Stock availability');
assert.match(element('decision-evidence').innerHTML,/stockout/);
const emptyWeek=vm.runInContext("Object.keys(DATA.units.investigations).find(w=>!DATA.units.investigations[w].decision.evidence.length)",context);
assert.ok(emptyWeek,'The report must include an unverified week for the empty-evidence regression');
element('week').value=emptyWeek;element('week').callbacks.change();
assert.match(element('decision-evidence').innerHTML,/No qualifying operational evidence/);
element('week').value='2024-01-29';element('week').callbacks.change();
assert.match(element('decision-evidence').innerHTML,/stockout/);
const before=element('potential-value').textContent;
element('recovery').value='75';element('recovery').callbacks.input();
assert.notEqual(element('potential-value').textContent,before);
element('cost').value='0';element('cost').callbacks.input();
assert.match(element('break-even').textContent,/0\.0%/);
for(const control of dimensions)control.click();
for(const control of tabs)control.click();
for(const method of ['rolling_z','seasonal','isolation_forest','ensemble']) {element('method').value=method;element('method').callbacks.change();assert.ok(element('narrative').textContent.length>80);}
element('download').click();element('csv').click();
console.log('Exported demo controls, metrics, week selection, dimensions, tabs, charts, and downloads passed.');
