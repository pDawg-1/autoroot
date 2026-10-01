let runtime;
onmessage = async ({data}) => {
  try {
    if (!runtime) {
      postMessage({status:'Loading Python and scientific packages. First use may take a minute.'});
      importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
      runtime = await loadPyodide();
      await runtime.loadPackage(['pandas','scipy','scikit-learn']);
      for (const name of ['detector.py','detector_config.json','root_cause.py','sales_validation.py','browser_analysis.py']) {
        const response = await fetch('python/'+name);
        if (!response.ok) throw Error('Cannot load analysis module '+name);
        runtime.FS.writeFile('/home/pyodide/'+name,await response.text());
      }
    }
    postMessage({status:'Validating sales and fitting past-only detectors. Large files may take several minutes.'});
    runtime.globals.set('csv_text',data.csv);
    runtime.globals.set('selected_metric',data.metric);
    const result = await runtime.runPythonAsync('from browser_analysis import analyze\nanalyze(csv_text, selected_metric)');
    postMessage({result:JSON.parse(result)});
  } catch(error) { postMessage({error:String(error)}); }
  finally { if(runtime) runtime.runPython('csv_text = None'); }
};
