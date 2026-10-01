// Exercise the exported report's controls without external browser dependencies.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('site/index.html', 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {value: '', checked: true, textContent: '', innerHTML: '', className: '', dataset: {}, callbacks: {}, classList: {toggle() {}}, addEventListener(name, fn) {this.callbacks[name]=fn;}, click() {this.callbacks.click?.();}});
  return elements.get(id);
}
element('metric').value='revenue';
element('method').value='ensemble';
const tabs=['investigation','scorecard','methodology'].map(id=>{const e=element('tab-'+id);e.dataset.tab=id;return e;});
const dimensions=['region','sku','channel'].map(id=>{const e=element('dim-'+id);e.dataset.dim=id;return e;});
const plots=new Map();
const context=vm.createContext({console,Blob,URL,setTimeout,document:{getElementById:element,querySelectorAll:q=>q==='[data-tab]'?tabs:dimensions,createElement:()=>element('download-link')},Plotly:{react:(id,data,layout)=>plots.set(id,{data,layout}),Plots:{resize(){}}}});
vm.runInContext(script,context);
assert.match(element('narrative').textContent,/Validate/);
assert.equal(element('alerts').textContent,9);
assert.match(element('evaluation').innerHTML,/88\.9%/);
assert.equal(plots.get('timeline').data[0].x.length,104);
element('metric').value='units';element('metric').callbacks.change();
assert.equal(element('alerts').textContent,8);
assert.match(element('evaluation').innerHTML,/87\.5%/);
element('only-alerts').checked=false;element('only-alerts').callbacks.change();
assert.equal((element('week').innerHTML.match(/<option/g)||[]).length,78);
element('week').value='2024-01-29';element('week').callbacks.change();
assert.match(element('narrative').textContent,/West/);
for(const control of dimensions)control.click();
for(const control of tabs)control.click();
for(const method of ['rolling_z','seasonal','isolation_forest','ensemble']) {element('method').value=method;element('method').callbacks.change();assert.ok(element('narrative').textContent.length>80);}
element('download').click();element('csv').click();
console.log('Exported demo controls, metrics, week selection, dimensions, tabs, charts, and downloads passed.');
