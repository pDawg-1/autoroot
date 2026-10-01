// Extend the exported report with operational decisions and holdout results.
function renderDecision() {
  const m=$('metric').value,w=$('week').value;
  const decision=DATA[m].investigations[w].decision;
  const recovery=Math.min(100,Math.max(0,Number($('recovery').value||50)))/100;
  const margin=Math.min(100,Math.max(0,Number($('margin').value||30)))/100;
  const cost=Math.max(0,Number($('cost').value||500));
  $('recovery-label').textContent=Math.round(recovery*100)+'%';
  $('margin-label').textContent=Math.round(margin*100)+'%';
  $('decision-issue').textContent=decision.issue;
  $('decision-owner').textContent='Owner: '+decision.owner;
  $('decision-action').textContent=decision.action;
  $('decision-success').textContent=decision.success_measure;
  const evidence=decision.evidence || [];
  $('decision-evidence').innerHTML=evidence.length
    ? evidence.map(line=>'<li>'+esc(line)+'</li>').join('')
    : '<li>No qualifying operational evidence is available for this week. Sales changes alone do not establish a cause. Check inventory, availability, pricing, and campaign records before choosing an intervention.</li>';
  const exposure=decision.exposed_revenue;
  $('exposed-value').textContent=amount(exposure,'revenue');
  $('potential-value').textContent=amount(exposure*recovery,'revenue');
  $('net-value').textContent=amount(exposure*recovery*margin-cost,'revenue');
  $('break-even').textContent=exposure*margin>0?'Break-even recovery: '+(cost/(exposure*margin)*100).toFixed(1)+'%. Above 100% means the intervention does not pay back under these assumptions.':'No availability recovery value is established for this selection.';
  $('holdout').innerHTML=table(['Method','Precision','Recall','F1','True alerts','False alerts','Missed'],DATA.benchmark.filter(x=>x.metric===m).map(x=>[names[x.method],(100*x.precision).toFixed(1)+'%',(100*x.recall).toFixed(1)+'%',x.f1.toFixed(3),x.true_positives,x.false_positives,x.false_negatives]));
  $('freshness').textContent='Latest complete week: '+dateLabel(DATA.metadata.last_week)+' · '+DATA.metadata.weeks+' weeks · '+DATA.metadata.records.toLocaleString('en-US')+' synthetic records';
}
const originalRender=render;
render=function(){originalRender();renderDecision();};
['recovery','margin','cost'].forEach(id=>$(id).addEventListener('input',renderDecision));
weeks();
