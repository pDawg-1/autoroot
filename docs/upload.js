const el=id=>document.getElementById(id);let worker,result;
const escapeText=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function stop(){if(worker)worker.terminate();worker=null;el('run').disabled=false;el('cancel').disabled=true;}
el('cancel').onclick=()=>{stop();el('status').textContent='Analysis cancelled.';};
el('run').onclick=async()=>{
 const file=el('file').files[0];if(!file){el('status').textContent='Choose a CSV first.';return;}
 if(file.size>10*1024*1024){el('status').textContent='File exceeds 10 MB.';return;}
 stop();result=null;el('results').hidden=true;el('run').disabled=true;el('cancel').disabled=false;
 try{const csv=await file.text();worker=new Worker('browser_worker.js');
 worker.onerror=e=>{el('status').textContent='Browser runtime failed: '+e.message;stop();};
 worker.onmessage=({data})=>{if(data.status)el('status').textContent=data.status;
 if(data.error){el('status').textContent=data.error;stop();}
 if(data.result){result=data.result;stop();el('status').textContent='Analysis complete: '+result.quality.rows.toLocaleString()+' records, '+result.quality.weeks+' weeks.';
 el('week').replaceChildren(...Object.keys(result.investigations).map(w=>new Option(w,w)));el('week').value=Object.keys(result.investigations).at(-1);el('results').hidden=false;render();}};
 worker.postMessage({csv,metric:el('metric').value});
 }catch(e){el('status').textContent=String(e);stop();}
};
function render(){if(!result)return;const week=el('week').value,r=result.investigations[week],m=result.metric,row=result.weekly.find(x=>x.week===week);
 el('summary').textContent=m.toUpperCase()+' · '+week+' · '+(row.ensemble?'Movement flagged':'No combined alert')+' · Actual '+r.actual.toFixed(0)+' · Expected '+r.expected.toFixed(0)+' · Gap '+r.gap.toFixed(0);
 el('narrative').textContent=r.narrative;
 Plotly.react('timeline',[{x:result.weekly.map(x=>x.week),y:result.weekly.map(x=>x[m]),name:'Actual',type:'scatter'},{x:result.weekly.map(x=>x.week),y:result.weekly.map(x=>x.expected),name:'Seasonal expected',type:'scatter'},{x:result.weekly.filter(x=>x.ensemble).map(x=>x.week),y:result.weekly.filter(x=>x.ensemble).map(x=>x[m]),mode:'markers',name:'Alerts',marker:{color:'#d15543',size:10}}],{title:'Weekly '+m,margin:{t:50}},{responsive:true});
 Plotly.react('bridge',[{type:'waterfall',x:['Four-week baseline','Volume','Price / mix','Actual'],y:[r.expected,r.volume,r.price,0],measure:['absolute','relative','relative','total']}],{title:'Revenue bridge',margin:{t:50}},{responsive:true});
 el('bridge').hidden=m!=='revenue';renderDrivers();
}
function renderDrivers(){if(!result)return;const r=result.investigations[el('week').value],m=result.metric;
 const d=el('dimension').value,rows=r.drivers[d];const keys=[d,m+'_actual',m+'_expected','delta','contribution_pct'];
 el('drivers').innerHTML='<table><thead><tr>'+keys.map(k=>'<th>'+escapeText(k)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(x=>'<tr>'+keys.map(k=>'<td>'+escapeText(typeof x[k]==='number'?x[k].toFixed(2):x[k]??'—')+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
}
el('week').onchange=render;el('dimension').onchange=renderDrivers;
el('download').onclick=()=>{if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='sales-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
