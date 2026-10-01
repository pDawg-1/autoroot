// Execute the deployed Python modules in the pinned WebAssembly runtime.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
async function main(){
 const runtimeDir=path.resolve(process.argv[2]||'.runtime');
 const {loadPyodide}=require(path.join(runtimeDir,'pyodide.js'));
 const py=await loadPyodide({indexURL:runtimeDir+path.sep});
 const lock=JSON.parse(fs.readFileSync(path.join(runtimeDir,'pyodide-lock.json')));
 const needed=new Set();function include(name){if(needed.has(name))return;needed.add(name);for(const d of lock.packages[name].depends)include(d);}
 ['pandas','scipy','scikit-learn'].forEach(include);
 await py.loadPackage(['pandas','scipy','scikit-learn']);
 for(const name of fs.readdirSync('site/python'))py.FS.writeFile('/home/pyodide/'+name,fs.readFileSync('site/python/'+name,'utf8'));
 py.globals.set('csv_text',fs.readFileSync('data/sales.csv','utf8'));
 const result=JSON.parse(await py.runPythonAsync("from browser_analysis import analyze\nanalyze(csv_text, 'revenue')"));
 assert.equal(result.quality.rows,37440);assert.equal(result.weekly.length,104);assert.equal(Object.keys(result.investigations).length,78);
 const native=JSON.parse(fs.readFileSync('reports/manifest.json','utf8'));assert.ok(native);
 const rows=fs.readFileSync('reports/detections_revenue.csv','utf8').trim().split(/\r?\n/);const keys=rows.shift().split(',');
 for(let i=0;i<rows.length;i++){const values=rows[i].split(',');assert.equal(result.weekly[i].ensemble,values[keys.indexOf('ensemble')]==='True');}
 await assert.rejects(py.runPythonAsync("analyze('week,region,sku,channel,units,revenue\\n2024-01-01,A,B,C,-1,5', 'revenue')"),/Negative sales/);
 console.log('WebAssembly runtime: full sample, native alert parity, investigations, and invalid input passed.');
}
main().catch(e=>{console.error(e);process.exit(1)});
