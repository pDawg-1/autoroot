const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,{value:'',files:[],replaceChildren(...options){this.options=options;}});return elements.get(id);};
get('metric').value='revenue';get('dimension').value='region';let worker,plots=0;
const context={document:{getElementById:get,createElement:()=>({click(){}})},Worker:class{constructor(){worker=this;}postMessage(data){this.input=data;}terminate(){this.terminated=true;}},Option:class{constructor(text,value){this.text=text;this.value=value;}},Plotly:{react(){plots++;}},Blob,URL,setTimeout,console};
vm.createContext(context);vm.runInContext(fs.readFileSync('site/upload.js','utf8'),context);
(async()=>{
 await get('run').onclick();assert.match(get('status').textContent,/Choose/);
 get('file').files=[{size:11*1024*1024}];await get('run').onclick();assert.match(get('status').textContent,/exceeds/);
 get('file').files=[{size:100,text:async()=> 'test csv'}];await get('run').onclick();assert.equal(worker.input.csv,'test csv');assert.equal(get('run').disabled,true);
 const result={metric:'revenue',quality:{rows:100,weeks:27},weekly:[{week:'2024-01-01',revenue:10,expected:8,ensemble:true}],investigations:{'2024-01-01':{actual:10,expected:8,gap:2,volume:1,price:1,narrative:'Investigated',drivers:{region:[{region:'<img src=x>',revenue_actual:10,revenue_expected:8,delta:2,contribution_pct:100}]}}}};
 worker.onmessage({data:{result}});assert.equal(get('results').hidden,false);assert.equal(plots,2);assert.match(get('drivers').innerHTML,/&lt;img/);assert.equal(get('run').disabled,false);
 await get('run').onclick();get('cancel').onclick();assert.ok(worker.terminated);assert.match(get('status').textContent,/cancelled/);
 console.log('Upload controls, size limit, worker results, safe driver rendering, and cancellation passed.');
})().catch(e=>{console.error(e);process.exit(1)});
