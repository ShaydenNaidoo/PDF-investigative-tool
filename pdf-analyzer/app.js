'use strict';
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const state = {data:null, view:'overview', evidenceMode:'documents', evidenceOffset:0, evidenceSort:'id', evidenceDirection:'asc', studioMode:'library', job:null, running:null, resultOffset:0, resultSort:'', resultDirection:'asc', inspector:null, request:0, notes:{}, timer:null};
const types = ['Font','XObject','ColorSpace','ExtGState','Pattern','Shading','Properties'];
const number = value => Number(value).toLocaleString();
function animateCount(el, value) {
  const previous=Number(el.dataset.count || 0);el.dataset.count=value;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches||previous===value){el.textContent=number(value);return;}
  const start=performance.now();function frame(time){const progress=Math.min(1,(time-start)/700);el.textContent=number(Math.round(previous+(value-previous)*(1-Math.pow(1-progress,3))));if(progress<1)requestAnimationFrame(frame);}requestAnimationFrame(frame);
}
const date = value => value ? new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—';
const busy = status => ['running','queued'].includes(status);
let toastTimer;
function toast(message, error=false) { $('#toast').textContent=message; $('#toast').className=`toast${error?' error':''}`; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').classList.add('hidden'),5000); }
function debounce(fn, delay=220) {let timer; return (...args)=>{clearTimeout(timer);timer=setTimeout(()=>fn(...args),delay);};}
async function api(path, body, reconnect=true) {
  const response=await fetch(path, body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Lab-Token':state.data?.token || ''},body:JSON.stringify(body)});
  const result=await response.json();
  if(response.status===403 && body!==undefined && reconnect && result.error==='Reload the local lab to reconnect.') {
    const fresh=await api('/api/dashboard');
    if(state.data)state.data.token=fresh.token;
    return api(path,body,false);
  }
  if(!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function download(name,text,type='text/plain') {const blob=new Blob([text],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function csv(headers,rows) {const quote=x=>`"${String(x??'').replace(/^[=+@-]/,"'$&").replace(/"/g,'""')}"`;return '\ufeff'+[headers.map(quote).join(','),...rows.map(r=>headers.map(h=>quote(r[h])).join(','))].join('\r\n');}
function docLink(id) {return `<button class="doc-link" data-document="${esc(id)}">${esc(id)}</button>`;}
function toolTags(tools) {return tools?.length?tools.map(t=>`<span class="tool-tag">${esc(t)}</span>`).join(' '):'<span class="muted-dash">—</span>';}
const titles={setup:'LAB SETUP',overview:'DASHBOARD',evidence:'EVIDENCE EXPLORER',comparison:'TOOL COMPARISON',scripts:'SCRIPT STUDIO',notebook:'FIELD NOTEBOOK'};
function showView(view) {
  if(!titles[view])return;
  const changed=state.view!==view;state.view=view;if(changed)window.scrollTo({top:0,behavior:'instant'});$$('.nav-item').forEach(el=>{const active=el.dataset.view===view;el.classList.toggle('active',active);if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});$$('.view').forEach(el=>el.classList.toggle('active',el.id===view));$('#page-title').textContent=titles[view];history.replaceState(null,'',`#${view}`);
  if(state.data && view==='evidence')renderEvidence();
  if(state.data && view==='scripts')loadHistory().catch(e=>toast(e.message,true));
  if(state.data && view==='setup')loadSetup();
}
function table(headers, rows, {labels={}, context='', empty='No evidence matches this selection.'}={}) {
  if(!rows.length)return `<div class="empty">${esc(empty)}</div>`;
  return `<div class="table-scroll"><table><thead><tr>${headers.map(h=>`<th>${context?`<button data-sort="${esc(h)}" data-sort-context="${context}">${esc(labels[h] || h.replaceAll('_',' ').toUpperCase())} ↕</button>`:esc(labels[h] || h.replaceAll('_',' ').toUpperCase())}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
}
function pagination(target, total, offset, limit, context) {$(target).innerHTML=`<span>${total?`${number(offset+1)}–${number(Math.min(offset+limit,total))} of ${number(total)}`:'0'} matching entries</span><div class="pagination-controls"><button data-page="${Math.max(0,offset-limit)}" data-page-context="${context}" ${offset===0?'disabled':''}>← Previous</button><button data-page="${offset+limit}" data-page-context="${context}" ${offset+limit>=total?'disabled':''}>Next →</button></div>`;}
function fillTools(selector) {const select=$(selector),value=select.value,first=select.options[0].outerHTML;select.innerHTML=first+state.data.tools.map(t=>`<option value="${esc(t.id)}">${esc(t.id)} · ${t.exemplars} exemplars</option>`).join('');select.value=value;}
function renderDashboard() {
  const {counts,documents,summary,dependencies}=state.data;
  ['documents','resources','prefixes','marks'].forEach(key=>animateCount($(`#count-${key}`),counts[key]));
  $('#dataset-count').textContent=`${number(documents.filter(d=>d.available).length)} PDFs available locally`;
  $('#scan-count').textContent=`${number(counts.scanned)} documents with extracted entries`;
  $('#updated-at').textContent=`Updated ${date(state.data.generatedAt)}`;
  const byPrefix=new Map();summary.forEach(r=>{const existing=byPrefix.get(r.prefix);if(!existing||existing.documents<r.documents)byPrefix.set(r.prefix,r);});
  const top=[...byPrefix.values()].sort((a,b)=>b.documents-a.documents).slice(0,7);const max=Math.max(...top.map(r=>r.documents),1);
  $('#prefix-bars').innerHTML=top.length?top.map(r=>`<button class="prefix-row" data-prefix="${esc(r.prefix)}" title="${esc(r.resource_type)} · ${r.documents} documents"><span>${esc(r.prefix)}</span><span class="track"><span class="fill" style="width:${r.documents/max*100}%"></span></span><span class="prefix-count">${number(r.documents)}</span></button>`).join(''):'<div class="empty">No extracted resource data yet. Run your extraction in Script studio.</div>';
  $('#tool-health').innerHTML=Object.entries(dependencies).filter(([name])=>['qpdf','pdfinfo','awk','bash'].includes(name)).map(([name,ok])=>`<span class="health-item ${ok?'':'missing'}">${ok?'✓':'!'} ${esc(name)}</span>`).join('');
  const examples=['CUF7M','QZ74K','GGGXC','MM5SP','MZRWQ','GKMDO'].map(id=>documents.find(d=>d.id===id)).filter(Boolean);
  $('#radar-table').innerHTML=documentTable(examples.length?examples:documents.slice(0,6));
  fillTools('#evidence-tool');fillTools('#builder-tool');
  $('#evidence-type').innerHTML='<option value="">All resource types</option>'+types.map(t=>`<option>${t}</option>`).join('');
}
function documentTable(docs,context='') {
 return table(['id','producer','tools','resources','marks','inspect'],docs.map(d=>`<tr><td><div class="doc-cell"><svg><use href="#i-file"/></svg>${docLink(d.id)}</div></td><td class="producer-cell" title="${esc(d.producer)}">${esc(d.producer)||'<span class="muted-dash">Not recorded</span>'}</td><td>${toolTags(d.tools)}</td><td class="mono">${number(d.resources)}</td><td class="mono">${number(d.marks)}</td><td><button class="text-button" data-document="${esc(d.id)}" ${d.available?'':'disabled'}>${d.available?'Inspect ↗':'PDF missing'}</button>${d.available?`<div class="document-view-actions"><button class="text-button" data-document="${esc(d.id)}" data-document-tab="strings">Strings</button><button class="text-button" data-document="${esc(d.id)}" data-document-tab="metadata">Metadata</button></div>`:''}</td></tr>`),{context,labels:{id:'DOCUMENT',tools:'EXEMPLAR TOOL',resources:'RESOURCES',marks:'MARKS',inspect:''}});
}
function evidenceQuery() {return new URLSearchParams({q:$('#evidence-search').value,tool:$('#evidence-tool').value,type:state.evidenceMode==='resources'?$('#evidence-type').value:'',offset:state.evidenceOffset,limit:50,sort:state.evidenceSort,direction:state.evidenceDirection});}
async function renderEvidence() {
  if(!state.data)return;
  const request=++state.request;
  $('#evidence-type').classList.toggle('hidden',state.evidenceMode!=='resources');
  if(state.evidenceMode==='documents') {
    const q=$('#evidence-search').value.toLowerCase(),tool=$('#evidence-tool').value;
    let docs=state.data.documents.filter(d=>(!q||[d.id,d.producer,d.creator,...d.tools].join(' ').toLowerCase().includes(q))&&(!tool||d.tools.includes(tool)));
    docs.sort((a,b)=>{let x=a[state.evidenceSort]??'',y=b[state.evidenceSort]??'';return (typeof x==='number'?x-y:String(x).localeCompare(String(y)))*(state.evidenceDirection==='desc'?-1:1);});
    state.evidenceOffset=Math.min(state.evidenceOffset,Math.max(0,Math.floor((docs.length-1)/50)*50));
    $('#evidence-table').innerHTML=documentTable(docs.slice(state.evidenceOffset,state.evidenceOffset+50),'evidence');
    $('#evidence-context').textContent='Metadata from producer.txt · Resource counts from your extraction · Click a document for original PDF evidence';
    pagination('#evidence-pagination',docs.length,state.evidenceOffset,50,'evidence');
  } else {
    try {
      const result=await api('/api/resources?'+evidenceQuery());if(request!==state.request)return;
      $('#evidence-table').innerHTML=table(result.headers,result.rows.map(r=>`<tr>${result.headers.map(h=>`<td class="${['producer','resource_type'].includes(h)?'':'mono'}">${h==='document'?docLink(r[h]):h==='tool'?toolTags(r[h]?r[h].split(', '):[]):esc(r[h])||'<span class="muted-dash">—</span>'}</td>`).join('')}</tr>`),{context:'evidence'});
      $('#evidence-context').textContent=state.data.resourceSource+' · Use the document inspector for original object references.';
      pagination('#evidence-pagination',result.total,result.offset,result.limit,'evidence');
    } catch(error) {toast(error.message,true);}
  }
}
function matrixRows() {
  const threshold=Math.max(1,Number($('#sparse-threshold').value)||3);
  return state.data.tools.map(tool=>{const row={tool:tool.id,producer:tool.label,exemplars:tool.exemplars};types.forEach(type=>{const entries=state.data.matrix.filter(r=>r.tool===tool.id&&r.resource_type===type);row[type]=entries.length?entries.map(r=>`${r.prefix}${r.documents<threshold?'?':''} (${r.documents}/${r.exemplars})`).join('; '):'?';});return row;});
}
function renderMatrix() {
  if(!state.data)return;const threshold=Math.max(1,Number($('#sparse-threshold').value)||3);
  $('#matrix-table').innerHTML=`<div class="table-scroll"><table class="matrix"><thead><tr><th>TOOL / EXEMPLARS</th>${types.map(t=>`<th>${t.toUpperCase()}</th>`).join('')}</tr></thead><tbody>${state.data.tools.map(tool=>`<tr><td><span class="tool-tag">${esc(tool.id)}</span> <span class="muted small">${tool.exemplars} exemplars</span><small>${esc(tool.label)}</small></td>${types.map(type=>{const entries=state.data.matrix.filter(r=>r.tool===tool.id&&r.resource_type===type);return `<td>${entries.length?entries.map(r=>`<div class="matrix-entry ${r.documents<threshold?'sparse':''}">${esc(r.prefix)}${r.documents<threshold?'?':''}<span>${r.documents}/${r.exemplars}</span></div>`).join(''):'<span class="question" title="No extracted example; capability has not been determined">?</span>'}</td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function setStudioMode(mode) {state.studioMode=mode;$$('[data-studio-mode]').forEach(el=>el.classList.toggle('active',el.dataset.studioMode===mode));$('#library-pane').classList.toggle('hidden',mode!=='library');$('#editor-pane').classList.toggle('hidden',mode!=='editor');}
function renderScripts(selected) {
  const select=$('#script-select'),value=selected||select.value;
  select.innerHTML=state.data.scripts.map(script=>`<option value="${esc(script.id)}">${script.custom?'★ ':''}${esc(script.label)}</option>`).join('');
  if(state.data.scripts.some(s=>s.id===value))select.value=value;
  updateScriptDescription();
}
function runBlockReason() {
  if(!state.data)return 'Connect to the lab before running an investigation.';
  if(state.starting)return 'Saving and starting your investigation…';
  if(state.running||state.setup?.activeInvestigation)return 'Wait for the current investigation to finish, or stop it.';
  if(state.uploadBusy||importBusy(state.setup?.import?.status))return 'Wait for your PDF import to finish.';
  return '';
}
function updateRunAvailability() {
  const reason=runBlockReason();$('#run-script').disabled=!!reason;$('#run-script').title=reason||'Run this investigation';
}
function updateScriptDescription() {
  const script=state.data?.scripts.find(s=>s.id===$('#script-select').value);
  $('#script-description').textContent=script?.description || 'No scripts found in observations.';
  const arg=script?.argument||'none';$('#arguments-field').classList.toggle('hidden',arg==='none');
  $('#script-arguments').placeholder=arg==='document'?'e.g. 22ZOC':arg==='tool'?'e.g. pr01':arg==='set'?'e.g. tools/pr01':'e.g. tools/pr01 tools/pr02';
  updateRunAvailability();
}
function shellQuote(value) {return "'"+String(value).replaceAll("'","'\\''")+"'";}
function generateScript() {
  const mode=$('#template-mode').value;
  let source='#!/usr/bin/env bash\nset -euo pipefail\n\n# Working directory: observations\n';
  if(mode==='blank')source+='# Print a TSV header and rows to build a results table.\nprintf \'document\\tobservation\\n\'\n\n';
  else {
    const args=[mode];if($('#builder-tool').value)args.push('--tool',shellQuote($('#builder-tool').value));if($('#builder-documents').value.trim())args.push('--document',shellQuote($('#builder-documents').value.trim()));if($('#builder-type').value&&['resources','numbering'].includes(mode))args.push('--type',shellQuote($('#builder-type').value));if($('#builder-prefix').value.trim()&&['resources','numbering'].includes(mode))args.push('--prefix',shellQuote($('#builder-prefix').value.trim()));
    source+='# Read original PDFs; keep source object references.\n# Structured output becomes a results table automatically.\npython3 "$PDF_ANALYZER_HOME/lab.py" '+args.join(' ')+'\n';
  }
  $('#script-source').value=source;$('#script-name').value=mode==='blank'?'my-investigation':mode+'-investigation';$('#save-status').textContent='Draft generated';editorLines();
}
function editorLines() {const count=$('#script-source').value.split('\n').length;$('#editor-lines').textContent=`${count} LINES`;}
async function saveScript() {
  const result=await api('/api/scripts',{name:$('#script-name').value.trim(),source:$('#script-source').value});
  state.data.scripts=result.scripts;renderScripts(result.id);$('#save-status').textContent='Saved to observations/gui-scripts';return result.id;
}
async function startRun() {
  const blocked=runBlockReason();if(blocked){$('#run-status').textContent=blocked;return;}
  state.starting=true;updateRunAvailability();$('#run-status').textContent='Saving and starting your investigation…';
  try {
    const script=state.studioMode==='editor'?await saveScript():$('#script-select').value;
    const job=await api('/api/run',{script,arguments:state.studioMode==='library'?$('#script-arguments').value:'',label:state.studioMode==='editor'?$('#script-name').value:$('#script-select').selectedOptions[0]?.textContent});
    state.running=job.id;state.job=job;state.resultOffset=0;resetSummary();$('#result-table').innerHTML='<div class="empty">Investigation in progress. Results appear when the run finishes.</div>';$('#result-pagination').innerHTML='';$('#result-select').innerHTML='';$('#export-results').disabled=true;$('#jump-results').disabled=true;
    updateRun(job);pollRun(job.id);
  } catch(error) {toast(error.message,true);$('#run-status').textContent=error.message;$('#save-status').textContent=error.message;$('#run-badge').textContent='NOT STARTED';$('#run-badge').className='tag failed';$('#run-meta').textContent='Your investigation could not start.';$('#console').innerHTML='<span class="stderr">'+esc(error.message)+'</span>';}
  finally {state.starting=false;updateRunAvailability();}
}
function updateRun(job) {
  state.job=job;$('#run-badge').textContent=job.status.toUpperCase();$('#run-badge').className='tag '+job.status;
  $('#cancel-run').classList.toggle('hidden',!state.running);updateRunAvailability();
  const started=job.startedAt || job.createdAt;const duration=Math.max(0,Math.round(((job.endedAt?new Date(job.endedAt):new Date())-new Date(started))/1000));
  $('#run-meta').textContent=`${job.label} · ${job.id} · ${duration}s${job.exitCode!==null?' · exit '+job.exitCode:''}`;
  $('#run-status').textContent=busy(job.status)?'Investigation running…':job.status==='completed'?'Run complete. Evidence refreshed.':job.error || `Run ${job.status}. Inspect the output for details.`;
  if(job.stdout!==undefined) {
    const output=$('#console');const atBottom=output.scrollHeight-output.scrollTop-output.clientHeight<70;
    output.innerHTML=esc(job.stdout || '')+(job.stderr?`\n<span class="stderr">[progress / stderr]\n${esc(job.stderr)}</span>`:'')+(job.error?`\n<span class="stderr">${esc(job.error)}</span>`:'');
    if(!output.textContent.trim())output.textContent=busy(job.status)?'Waiting for script output…':'Script finished without console output.';
    if(atBottom)output.scrollTop=output.scrollHeight;
  }
}
async function pollRun(id) {
  clearTimeout(state.timer);
  try {
    const job=await api('/api/jobs/'+id);updateRun(job);
    if(busy(job.status)||job.finalized===false) {state.running=id;state.timer=setTimeout(()=>pollRun(id),1000);}
    else {state.running=null;updateRun(job);await refreshData();await loadHistory();await loadSetup();setupResults(job);}
  } catch(error) {$('#run-status').textContent='Connection lost. Retrying…';state.timer=setTimeout(()=>pollRun(id),2500);}
}
async function loadHistory() {
  const jobs=await api('/api/jobs');
  $('#history-table').innerHTML=table(['investigation','status','created','exit','tables'],jobs.map(job=>`<tr class="history-row ${state.job?.id===job.id?'active':''}" data-job="${esc(job.id)}"><td><button class="run-history-label" data-job="${esc(job.id)}">${esc(job.label)}</button><div class="muted small mono">${esc(job.id)}</div></td><td><span class="tag ${esc(job.status)}">${esc(job.status.toUpperCase())}</span></td><td>${esc(date(job.createdAt))}</td><td class="mono">${job.exitCode??'—'}</td><td class="mono">${number(job.tables?.reduce((total,t)=>total+t.rows,0)||0)} rows</td></tr>`),{empty:'No investigations yet. Your run history will appear here.'});
  return jobs;
}
function setupResults(job) {
  resetSummary();
  const tables=job.tables||[];$('#result-select').innerHTML=tables.map(t=>`<option value="${esc(t.name)}">${esc(t.name)} · ${number(t.rows)} rows</option>`).join('');$('#export-results').disabled=!tables.length;
  $('#jump-results').disabled=!tables.length;$('#output-hint').textContent=tables.length?`${number(tables.reduce((sum,t)=>sum+t.rows,0))} result rows saved across ${tables.length} table${tables.length===1?'':'s'}.`:'Run snapshots, logs and tables are saved in observations/gui-runs.';
  state.resultOffset=0;state.resultSort='';$('#result-search').value='';
  if(tables.length)renderResults();else {$('#result-table').innerHTML=`<div class="empty">${job.status==='completed'?'This script produced no table.':'No structured table is available for this run.'}<small>Print tab-separated output, or write a .tsv file to $PDF_RUN_DIR. Build helpers are summarized from their saved files.</small></div>`;$('#result-pagination').innerHTML='';}
}
function resultQuery() {return new URLSearchParams({name:$('#result-select').value,q:$('#result-search').value,offset:state.resultOffset,limit:50,sort:state.resultSort,direction:state.resultDirection});}
async function renderResults() {
  const id=state.job?.id,name=$('#result-select').value;if(!id||!name)return;
  const request=state.resultRequest=(state.resultRequest||0)+1;
  try {
    const result=await api(`/api/jobs/${id}/table?${resultQuery()}`);if(id!==state.job?.id||name!==$('#result-select').value||request!==state.resultRequest)return;
    if(!state.resultHeaders)configureSummary(result.headers);
    $('#result-table').innerHTML=table(result.headers,result.rows.map(row=>`<tr>${result.headers.map(h=>`<td class="mono">${h==='document'&&state.data.documents.some(d=>d.id===row[h])?docLink(row[h]):esc(row[h])||'<span class="muted-dash">—</span>'}</td>`).join('')}</tr>`),{context:'result'});
    pagination('#result-pagination',result.total,result.offset,result.limit,'result');
  }catch(error){toast(error.message,true);}
}
function resetSummary() {
  state.summaryActive=false;state.summaryData=null;state.summaryOffset=0;state.resultHeaders=null;state.summaryRequest=(state.summaryRequest||0)+1;
  $('#results-summary').classList.add('hidden');$('#generate-summary').disabled=true;$('#export-summary').disabled=true;$('#export-summary-chart').disabled=true;
  $('#summary-content').classList.add('hidden');$('#summary-status').textContent='';
}
function configureSummary(headers) {
  state.resultHeaders=headers;
  const candidates=['document','document_id','pdf','id'].filter(h=>headers.includes(h)),document=candidates[0]||'';
  const documentColumns=candidates.length?candidates:headers;
  $('#summary-document').innerHTML=(document?'':'<option value="">Choose a PDF ID column…</option>')+documentColumns.map(h=>`<option value="${esc(h)}">${esc(h)}</option>`).join('');$('#summary-document').value=document;$('#summary-document').disabled=candidates.length===1;
  const options=[{fields:[],label:'By tool · overall'}];
  if(headers.includes('resource_type')&&headers.includes('prefix'))options.push({fields:['resource_type','prefix'],label:'Resource type + prefix'});
  headers.filter(h=>h!==document).forEach(h=>options.push({fields:[h],label:h.replaceAll('_',' ')}));
  $('#summary-group').innerHTML=options.map(o=>`<option value="${esc(JSON.stringify(o.fields))}">${esc(o.label)}</option>`).join('');
  $('#summary-group').value=JSON.stringify(headers.includes('resource_type')?['resource_type']:[]);
  $('#summary-tool').innerHTML='<option value="">All exemplar tools</option>'+state.data.tools.map(t=>`<option value="${esc(t.id)}">${esc(t.id)} · ${esc(t.label)}</option>`).join('')+'<option value="__unassigned__">Unassigned PDFs</option>';
  $('#summary-type').innerHTML='<option value="">All resource types</option>'+types.map(t=>`<option>${esc(t)}</option>`).join('');$('#summary-type').disabled=!headers.includes('resource_type');
  $('#generate-summary').disabled=false;
}
function summaryQuery() {
  const query=new URLSearchParams({name:$('#result-select').value,q:$('#result-search').value,documentColumn:$('#summary-document').value,tool:$('#summary-tool').value,type:$('#summary-type').disabled?'':$('#summary-type').value,offset:state.summaryOffset||0,limit:50});
  JSON.parse($('#summary-group').value||'[]').forEach(group=>query.append('group',group));return query;
}
async function generateSummary(scroll=false) {
  const id=state.job?.id,name=$('#result-select').value;if(!id||!name||!state.resultHeaders)return;
  state.summaryActive=true;const request=state.summaryRequest=(state.summaryRequest||0)+1;
  $('#results-summary').classList.remove('hidden');$('#summary-status').innerHTML='<span class="spinner"></span> Summarizing the full result table…';$('#summary-content').classList.add('hidden');$('#export-summary').disabled=true;$('#export-summary-chart').disabled=true;
  if(scroll)$('#results-summary').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  const query=summaryQuery();$('#summary-scope').textContent=`${state.job.label} · ${name} · Full saved table${query.get('q')?' · Result search: '+query.get('q'):' · No result search filter'}`;
  try {
    const data=await api(`/api/jobs/${id}/summary?${query}`);if(request!==state.summaryRequest||id!==state.job?.id||name!==$('#result-select').value||!state.summaryActive)return;
    if(!Array.isArray(data.overview)||!Array.isArray(data.rows)||!Array.isArray(data.groups)||!Array.isArray(data.resourceTypes)||!data.counts)throw new Error('The running app server needs an update. Stop the Start PDF Analyzer task, start it again, then refresh this page.');
    state.summaryData=data;state.summaryExportQuery=query.toString();$('#summary-status').textContent='';$('#summary-content').classList.remove('hidden');$('#export-summary').disabled=false;$('#export-summary-chart').disabled=!data.overview.length;
    const selectedType=$('#summary-type').value;$('#summary-type').innerHTML='<option value="">All resource types</option>'+data.resourceTypes.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join('');$('#summary-type').value=selectedType;
    const c=data.counts;$('#summary-counts').innerHTML=[['Matching result rows',c.matchedRows],['Distinct matching PDFs',c.matchedDocuments],['Rows in full source',c.sourceRows],['PDFs in full source',c.sourceDocuments]].map(([label,value])=>`<div><span>${label}</span><b>${number(value)}</b></div>`).join('');
    $('#summary-caveat').textContent='Rows count recorded entries, including repeats. Distinct PDFs are counted once per tool/category. Tool membership uses the current exemplar sets. Known exemplars is the full tool set; PDFs in source is the number represented in this saved table before filters. Observed coverage = matching PDFs ÷ known exemplars; a missing result does not establish absence.'+(c.unassignedDocuments?` ${number(c.unassignedDocuments)} matching PDFs have no exemplar membership and appear as Unassigned.`:'')+(c.missingDocumentRows?` ${number(c.missingDocumentRows)} matching rows have no PDF ID; they contribute rows only.`:'')+(c.overlapDocuments?` ${number(c.overlapDocuments)} matching PDFs belong to multiple tool sets, so tool totals can overlap.`:'');
    const columns=['tool','producer',...(data.groups.length?['breakdown']:[]),'rows','documents','exemplars','represented','coverage'];
    $('#summary-table').innerHTML=table(columns,data.rows.map(r=>`<tr>${columns.map(h=>`<td class="${h==='producer'?'summary-producer':h==='breakdown'?'mono summary-breakdown':'mono'}">${h==='tool'?`<button class="text-button" data-summary-tool="${esc(r.toolKey)}">${esc(r.tool)}</button>`:h==='breakdown'?r.values.map((v,i)=>`<span title="${esc(data.groups[i])}">${esc(v)||'<span class="muted-dash">(empty)</span>'}</span>`).join(' · '):h==='coverage'?r.coverage===null?'—':number(r.coverage)+'%':h==='producer'?esc(r[h]):number(r[h])}</td>`).join('')}</tr>`),{labels:{breakdown:data.groups.map(g=>g.replaceAll('_',' ').toUpperCase()).join(' / '),rows:'RESULT ROWS',documents:'DISTINCT PDFs',exemplars:'KNOWN EXEMPLARS',represented:'PDFs IN SOURCE',coverage:'OBSERVED COVERAGE'},empty:'No matching summary groups. Clear the result search or summary filters.'});
    pagination('#summary-pagination',data.total,data.offset,data.limit,'summary');renderSummaryChart();
  }catch(error){if(request!==state.summaryRequest)return;state.summaryData=null;$('#summary-content').classList.add('hidden');$('#export-summary').disabled=true;$('#export-summary-chart').disabled=true;$('#summary-status').textContent=error.message;}
}
function summaryChartSVG(data,metric) {
  const labels={documents:'Distinct PDFs',rows:'Result rows',coverage:'Observed coverage (%)'},rows=data.overview;
  const max=metric==='coverage'?100:Math.max(1,...rows.map(r=>r[metric]||0)),left=92,right=88,plot=620,width=left+plot+right,height=82+rows.length*34;
  const ticks=Array.from({length:5},(_,i)=>{const x=left+plot*i/4,value=max*i/4;return `<line x1="${x}" y1="38" x2="${x}" y2="${height-34}" stroke="#32374e"/><text x="${x}" y="${height-12}" text-anchor="middle" fill="#a0a7bf" font-size="10">${esc(metric==='coverage'?value+'%':number(Math.round(value)))}</text>`;}).join('');
  const bars=rows.map((r,i)=>{const y=48+i*34,value=r[metric],length=(value||0)/max*plot;return `<g class="summary-chart-bar" role="button" tabindex="0" data-summary-tool="${esc(r.toolKey)}" aria-label="${esc(r.tool+' '+labels[metric]+': '+(value===null?'not available':number(value)))}"><title>${esc(r.tool+' · '+r.producer+' · '+labels[metric]+': '+(value===null?'not available':number(value)))}</title><rect x="0" y="${y-7}" width="${width}" height="32" fill="transparent"/><text x="${left-12}" y="${y+12}" text-anchor="end" fill="#d4daec" font-size="12">${esc(r.tool)}</text><rect x="${left}" y="${y}" width="${plot}" height="18" rx="3" fill="#1f2335"/><rect class="summary-bar-fill" x="${left}" y="${y}" width="${length}" height="18" rx="3" fill="${i%2?'#75dfdd':'#ff79b9'}"/><text x="${left+plot+12}" y="${y+12}" fill="#d4daec" font-size="11">${value===null?'n/a':esc(number(value)+(metric==='coverage'?'%':''))}</text></g>`;}).join('');
  const scope=`Run ${data.job}, ${data.source}. Search: ${data.scope.query||'none'}. Resource type: ${data.scope.resourceType||'all'}. Tool: ${data.scope.tool||'all'}. ${data.counts.matchedRows} matching rows, ${data.counts.matchedDocuments} distinct PDFs. Tool memberships can overlap.`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="summary-chart-title summary-chart-description" style="font-family:ui-monospace,monospace"><title id="summary-chart-title">${esc(labels[metric])} across exemplar tools</title><desc id="summary-chart-description">${esc(scope)}</desc><rect width="${width}" height="${height}" rx="8" fill="#111422"/><text x="${left}" y="24" fill="#a0a7bf" font-size="11">${esc(labels[metric])}</text>${ticks}${bars}</svg>`;
}
function renderSummaryChart() {
  if(!state.summaryData)return;
  const data=state.summaryData,includeUnassigned=$('#summary-unassigned').checked||data.scope.tool==='__unassigned__';
  const overview=data.overview.filter(r=>r.toolKey!=='__unassigned__'||includeUnassigned);
  $('#summary-chart-note').textContent='Select a bar to filter this summary to that tool.'+(data.counts.unassignedDocuments&&!includeUnassigned?` ${number(data.counts.unassignedDocuments)} unassigned PDFs are listed in the table; use the checkbox to chart them.`:'');
  $('#summary-chart').innerHTML=overview.length?summaryChartSVG({...data,overview},$('#summary-metric').value):'<div class="empty">No exemplar tools match this selection.</div>';
  $('#export-summary-chart').disabled=!overview.length;
}
async function openJob(id) {
  if(state.running && state.running!==id){toast('Stop or finish the active investigation before opening another run.');return;}
  try{const job=await api('/api/jobs/'+id);state.job=job;updateRun(job);setupResults(job);await loadHistory();if(busy(job.status)){state.running=id;pollRun(id);}showView('scripts');}catch(error){toast(error.message,true);}
}
function highlighted(value, query, sensitive=false) {
  const text=String(value??'');if(!query)return esc(text);
  const haystack=sensitive?text:text.toLocaleLowerCase(),needle=sensitive?query:query.toLocaleLowerCase();
  let result='',start=0,index=haystack.indexOf(needle);while(index!==-1){result+=esc(text.slice(start,index))+`<mark>${esc(text.slice(index,index+query.length))}</mark>`;start=index+query.length;index=haystack.indexOf(needle,start);}return result+esc(text.slice(start));
}
function stringsPane() {
  return `<div class="strings-controls"><label class="field">Content view<select id="strings-mode"><option value="raw">File strings · original bytes</option><option value="objects">PDF objects & tags · decoded dictionaries</option><option value="text">Page text · extracted content</option></select></label><label class="field string-minimum">Minimum length<input id="strings-minimum" type="number" min="2" max="64" value="4"></label><label class="string-case"><input id="strings-case" type="checkbox"> Match case</label></div><div class="strings-search-row"><label class="search"><svg><use href="#i-search"/></svg><input id="strings-search" aria-label="Search PDF strings" placeholder="Search /Font, /Producer, resource names, text…"></label><select id="strings-tag" class="hidden" aria-label="Filter exact PDF tag"><option value="">All PDF tags</option></select><button class="secondary" id="clear-strings">Clear</button></div><div id="strings-tags" class="string-tag-cloud"></div><div class="inspection-source"><span id="strings-source">Choose a view to inspect the original PDF.</span><div><a id="strings-export-text" class="text-button">Export matches TXT ↗</a><a id="strings-export-csv" class="text-button">CSV ↗</a></div></div><div id="strings-notice" class="hidden"></div><div id="strings-results" aria-live="polite"></div><div id="strings-pagination" class="pagination"></div><div id="strings-object-preview" class="object-preview hidden"></div>`;
}
function metadataPane(id) {
  return `<div class="metadata-toolbar"><label class="search"><svg><use href="#i-search"/></svg><input id="metadata-search" placeholder="Search metadata fields, values and XMP…" aria-label="Search PDF metadata"></label><a class="secondary" href="/api/documents/${encodeURIComponent(id)}/metadata?export=json">Export JSON</a><a class="secondary" href="/api/documents/${encodeURIComponent(id)}/metadata?export=csv">CSV</a></div><div id="metadata-results" aria-live="polite"><div class="empty"><span class="spinner"></span>Reading PDF metadata…</div></div><div id="metadata-object-preview" class="object-preview hidden"></div>`;
}
async function inspectDocument(id,tab='resources') {
  const session=(state.inspectorSession||0)+1;state.inspectorSession=session;state.inspector=id;state.inspectorData=null;state.inspectorLoading=null;state.metadataData=null;state.metadataLoading=false;
  state.strings={offset:0,request:0};state.objectRequests={};
  $('#inspect-title').textContent=id;$('#open-pdf').href=`/api/documents/${encodeURIComponent(id)}/pdf`;
  const tabs=[['resources','Resources'],['strings','Strings & tags'],['metadata','Metadata'],['numbering','Numbering & reuse'],['marks','Toolmarks'],['notes','Document notes']];
  $('#inspect-body').innerHTML=`<div id="inspect-summary" class="inspect-summary"><span>Original PDF investigation</span><button class="text-button" data-investigate="${esc(id)}">Investigate this PDF ↗</button></div><div class="inspector-tabs" role="tablist" aria-label="PDF inspection views">${tabs.map(([key,label])=>`<button role="tab" aria-selected="false" aria-controls="inspect-${key}" data-inspect-tab="${key}">${label}</button>`).join('')}</div>${tabs.map(([key])=>`<div id="inspect-${key}" class="inspect-pane" role="tabpanel">${key==='strings'?stringsPane():key==='metadata'?metadataPane(id):key==='notes'?`<textarea id="document-notes" class="inspect-note" aria-label="Document notes" placeholder="Hypothesis, evidence and original object references…">${esc(state.notes[id]||'')}</textarea><button class="primary" id="save-document-notes">Save document notes</button>`:'<div class="empty"><span class="spinner"></span>Reading original PDF evidence…</div>'}</div>`).join('')}`;
  if(!$('#inspector').open)$('#inspector').showModal();
  selectInspectorTab(tab);return session;
}
function selectInspectorTab(tab) {
  if(!$('#inspect-'+tab))return;
  $$('[data-inspect-tab]').forEach(el=>{const selected=el.dataset.inspectTab===tab;el.classList.toggle('active',selected);el.setAttribute('aria-selected',String(selected));});
  $$('.inspect-pane').forEach(el=>el.classList.toggle('active',el.id==='inspect-'+tab));
  if(tab==='strings')loadStrings();else if(tab==='metadata')loadMetadata();else if(['resources','numbering','marks'].includes(tab))loadDocumentEvidence();
}
async function loadDocumentEvidence() {
  if(state.inspectorData||state.inspectorLoading)return;
  const id=state.inspector,session=state.inspectorSession;
  state.inspectorLoading=true;
  try {
    const detail=await api(`/api/documents/${encodeURIComponent(id)}`);if(state.inspector!==id||state.inspectorSession!==session)return;state.inspectorData=detail;
    const headers=['resource_type','subtype','resource_name','prefix','number','reference','scope'];
    const resources=detail.resources.slice(0,1000),grouped=new Map();detail.resources.forEach(r=>{const key=r.resource_type+':'+r.resource_name;if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(r);});
    const reused=[...grouped.values()].filter(rows=>new Set(rows.map(r=>r.scope)).size>1),changed=reused.filter(rows=>new Set(rows.map(r=>r.reference)).size>1);
    const numberHeaders=['resource_type','prefix','scope','start','end','distinct_numbers','missing_between','suffix_equals_object','entries'];
    $('#inspect-summary').innerHTML=`<span>${number(detail.resources.length)} scoped resources</span><span>${number(detail.marks.length)} existing marks</span><button class="text-button" data-investigate="${esc(id)}">Investigate this PDF ↗</button>`;
    $('#inspect-resources').innerHTML=`${detail.warning?`<div class="alert">QPDF warning: ${esc(detail.warning)}</div>`:''}<div class="inspect-caption">${esc(detail.source)}. Scope identifies the local resource dictionary. Click an object reference to inspect its definition. ${detail.resources.length>1000?`Showing the first 1,000 of ${number(detail.resources.length)} entries.`:''} <a class="text-button" href="/api/documents/${encodeURIComponent(id)}?export=csv">Export all resource evidence ↗</a></div>${table(headers,resources.map(r=>`<tr>${headers.map(h=>`<td class="mono">${h==='reference'&&r.reference!=='direct'?`<button class="object-link" data-object="${esc(r.reference.split(' ').slice(0,2).join(','))}">${esc(r.reference)}</button>`:esc(r[h])||'—'}</td>`).join('')}</tr>`))}<div id="object-preview" class="object-preview hidden"></div>`;
    $('#inspect-numbering').innerHTML=`<div class="numbering-note">Numbers are grouped by type, prefix and local scope. Gaps are missing values between the observed minimum and maximum. A gap or a reused name is an observation to investigate; it does not by itself prove editing. “Suffix equals object” counts matches to the original object number.</div>${table(numberHeaders,detail.numbering.slice(0,1000).map(r=>`<tr>${numberHeaders.map(h=>`<td class="mono">${esc(r[h])||'—'}</td>`).join('')}</tr>`))}${detail.numbering.length>1000?'<div class="inspect-caption">Showing the first 1,000 scopes. Use a numbering investigation in Script studio to export the full table.</div>':''}<p class="reuse">${reused.length} resource names recur across local scopes; ${changed.length} point to different targets.</p>${table(['type','name','scopes','targets'],reused.slice(0,200).map(rows=>`<tr><td>${esc(rows[0].resource_type)}</td><td class="mono">${esc(rows[0].resource_name)}</td><td class="mono">${esc([...new Set(rows.map(r=>r.scope))].join('; '))}</td><td class="mono">${esc([...new Set(rows.map(r=>r.reference))].join('; '))}</td></tr>`),{empty:'No resource name repeats across different local scopes.'})}${reused.length>200?'<div class="inspect-caption">Showing the first 200 reused names.</div>':''}`;
    $('#inspect-marks').innerHTML=`<p class="inspect-caption">Existing toolmark membership from observations/marks. These are observed marks, rather than automatic creator attribution.</p><div class="mark-cloud">${detail.marks.map(mark=>`<span class="tag">${esc(mark)}</span>`).join('')||'<div class="empty">No existing toolmarks recorded.</div>'}</div>`;
  } catch(error) {if(state.inspectorSession===session)['resources','numbering','marks'].forEach(tab=>$('#inspect-'+tab).innerHTML=`<div class="empty">${esc(error.message)}<small>You can still inspect original file strings using Strings & tags.</small></div>`);}
  finally{if(state.inspectorSession===session)state.inspectorLoading=false;}
}
function stringsQuery() {
  return new URLSearchParams({mode:$('#strings-mode').value,q:$('#strings-search').value,tag:$('#strings-mode').value==='objects'?$('#strings-tag').value:'',minimum:$('#strings-minimum').value||4,case:$('#strings-case').checked?'1':'0',offset:state.strings.offset,limit:20});
}
async function loadStrings() {
  const id=state.inspector,session=state.inspectorSession;if(!id||!$('#strings-mode'))return;
  const mode=$('#strings-mode').value,query=$('#strings-search').value,sensitive=$('#strings-case').checked,request=++state.strings.request;
  $('#strings-minimum').parentElement.classList.toggle('hidden',mode!=='raw');$('#strings-tag').classList.toggle('hidden',mode!=='objects');
  $('#strings-results').innerHTML='<div class="empty"><span class="spinner"></span>Reading PDF '+(mode==='raw'?'strings':mode==='objects'?'objects':'text')+'…</div>';
  const parameters=stringsQuery();const base=`/api/documents/${encodeURIComponent(id)}/strings?`;
  const textExport=new URLSearchParams(parameters);textExport.set('export','txt');$('#strings-export-text').href=base+textExport;
  const csvExport=new URLSearchParams(parameters);csvExport.set('export','csv');$('#strings-export-csv').href=base+csvExport;
  try {
    const result=await api(base+parameters);if(state.inspectorSession!==session||state.strings.request!==request)return;
    $('#strings-source').textContent=result.source;
    const selectedTag=$('#strings-tag').value;$('#strings-tag').innerHTML='<option value="">All PDF tags</option>'+result.tags.map(tag=>`<option value="${esc(tag.tag)}">${esc(tag.tag)} · ${number(tag.objects)} objects</option>`).join('');$('#strings-tag').value=selectedTag;
    $('#strings-tags').innerHTML=result.tags.slice(0,35).map(tag=>`<button class="pdf-tag ${selectedTag===tag.tag?'active':''}" data-pdf-tag="${esc(tag.tag)}" title="${tag.occurrences} occurrences in ${tag.objects} indexed objects">${esc(tag.tag)}<span>${number(tag.objects)}</span></button>`).join('');
    $('#strings-notice').className=result.truncated||result.warning?'inspection-notice':'hidden';$('#strings-notice').textContent=[result.truncated?`Index limited to ${result.indexLimit}. Search and exports cover the indexed portion of this view.`:'',result.warning].filter(Boolean).join('\n');
    $('#strings-results').innerHTML=result.rows.length?`<div class="string-results-list">${result.rows.map(row=>`<article class="string-record"><div class="string-record-head"><span class="mono string-location">${esc(row.location)}</span><span class="tag">${esc(row.kind)}</span>${row.reference?`<button class="text-button" data-object="${esc(row.reference.split(' ').slice(0,2).join(','))}" data-object-target="strings">Inspect object ↗</button>`:''}${row.stream?`<button class="text-button" data-object="${esc(row.reference.split(' ').slice(0,2).join(','))}" data-object-target="strings" data-decoded="1">Decode stream ↗</button>`:''}</div><pre>${highlighted(row.text,query,sensitive)}</pre>${row.previewTruncated?`<div class="string-preview-note">Partial record preview${row.previewOffset?' starting at character '+number(row.previewOffset):''}. Export matching strings for the full indexed record.</div>`:''}</article>`).join('')}</div>`:`<div class="empty">${result.indexed?'No strings match this search.':'No strings were found in this view.'}<small>${mode==='raw'?'Try PDF objects & tags to inspect dictionaries stored in compressed object streams.':mode==='text'?'Image-only scans may have no extractable page text. Try File strings or PDF objects & tags.':'Clear the text search or exact tag filter to show more objects.'}</small></div>`;
    pagination('#strings-pagination',result.total,result.offset,result.limit,'strings');
  } catch(error) {if(state.inspectorSession===session&&state.strings.request===request){$('#strings-results').innerHTML=`<div class="empty">${esc(error.message)}</div>`;$('#strings-pagination').innerHTML='';}}
}
async function loadMetadata() {
  if(state.metadataData){renderMetadata();return;}if(state.metadataLoading)return;
  const id=state.inspector,session=state.inspectorSession;state.metadataLoading=true;
  try {const data=await api(`/api/documents/${encodeURIComponent(id)}/metadata`);if(state.inspectorSession!==session)return;state.metadataData=data;renderMetadata();}
  catch(error){if(state.inspectorSession===session)$('#metadata-results').innerHTML=`<div class="empty">${esc(error.message)}</div>`;}
  finally{if(state.inspectorSession===session)state.metadataLoading=false;}
}
function renderMetadata() {
  const data=state.metadataData;if(!data||!$('#metadata-search'))return;const query=$('#metadata-search').value;
  const filtered=rows=>rows.filter(row=>[row.field,row.value].join(' ').toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  const fields=(rows,empty)=>table(['field','value'],filtered(rows).map(row=>`<tr><td class="metadata-field">${highlighted(row.field,query)}</td><td class="metadata-value">${highlighted(row.value,query)}</td></tr>`),{empty});
  const properties=Object.entries(data.pdfinfo).filter(([key])=>key!=='document').map(([field,value])=>({field,value}));
  const refButton=(reference,label)=>typeof reference==='string'&&/^\d+ \d+ R$/.test(reference)?`<button class="text-button" data-object="${esc(reference.split(' ').slice(0,2).join(','))}" data-object-target="metadata">${esc(label)} ${esc(reference)} ↗</button>`:'';
  $('#metadata-results').innerHTML=`<p class="inspect-caption">${esc(data.source)}<br>${esc(data.filename)} · ${number(data.bytes)} bytes</p>${data.warning?`<div class="inspection-notice">${esc(data.warning)}</div>`:''}<div class="metadata-section"><div class="metadata-section-head"><h3>Document properties</h3><span class="tag">PDFINFO</span></div>${fields(properties,'No document properties match this search.')}</div><div class="metadata-section"><div class="metadata-section-head"><h3>Info dictionary</h3>${refButton(data.infoReference,'Original object')}</div>${fields(data.info,data.info.length?'No Info fields match this search.':'This PDF has no Info dictionary fields.')}</div><div class="metadata-section"><div class="metadata-section-head"><h3>Trailer & identifiers</h3><span class="tag">ORIGINAL PDF</span></div>${fields(data.trailer,'No trailer fields match this search.')}</div><div class="metadata-section"><div class="metadata-section-head"><h3>XMP metadata</h3>${refButton(data.xmpReference,'Original stream')}</div>${data.xmp?(query&&!data.xmp.toLocaleLowerCase().includes(query.toLocaleLowerCase())?'<div class="empty">No XMP text matches this search.</div>':`<pre class="xmp-content">${highlighted(data.xmp,query)}</pre>`):'<div class="empty">No catalog XMP metadata stream found.</div>'}${data.truncated?'<div class="inspection-notice">XMP preview is limited to 2,000,000 decoded bytes. Export JSON includes this preview.</div>':''}</div>`;
}
async function inspectObject(ref,decoded=false,targetName='resources') {
  const id=state.inspector,session=state.inspectorSession;if(!id)return;
  const target=targetName==='resources'?$('#object-preview'):$(`#${targetName}-object-preview`);if(!target)return;
  const request=(state.objectRequests[target.id]||0)+1;state.objectRequests[target.id]=request;
  target.classList.remove('hidden');target.innerHTML='<div class="empty"><span class="spinner"></span>Reading '+(decoded?'decoded stream':'object')+'…</div>';
  try {
    const params=new URLSearchParams({ref,decoded:decoded?'1':'0'}),result=await api(`/api/documents/${id}/object?${params}`);
    if(state.inspectorSession!==session||state.objectRequests[target.id]!==request||!target.isConnected)return;
    params.set('export','txt');
    target.innerHTML=`<div class="object-preview-heading"><span class="label">${decoded?'DECODED STREAM':'ORIGINAL OBJECT'} ${esc(ref.replace(',',' '))}</span><div><button class="text-button" data-object="${esc(ref)}" data-object-target="${targetName}">Definition</button>${result.stream?`<button class="text-button" data-object="${esc(ref)}" data-decoded="1" data-object-target="${targetName}">Decoded stream</button>`:''}<a class="text-button" href="/api/documents/${id}/object?${params}">Export TXT ↗</a><button class="icon-button" data-close-object="${target.id}" aria-label="Close object preview">✕</button></div></div><div class="inspect-caption object-source">${esc(result.source)} · ${number(result.bytes)} bytes${result.truncated?` · preview limited to ${number(result.limit)} bytes`:''}</div><pre>${esc(result.text)}${result.warning?'\n'+esc(result.warning):''}</pre>`;
    target.scrollIntoView({block:'nearest',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  } catch(error){if(state.inspectorSession===session&&state.objectRequests[target.id]===request)target.innerHTML=`<div class="empty">${esc(error.message)}</div>`;}
}
async function saveNotes() {await api('/api/notes',{notes:state.notes});}
async function refreshData(initial=false) {
  const data=await api('/api/dashboard');state.data=data;
  if(initial){state.notes=data.notes||{};$('#notebook-text').value=state.notes._notebook||'';}
  $('#offline').classList.add('hidden');$('#connection-text').textContent='Local lab connected';$('#connection-dot').classList.remove('offline');
  renderDashboard();renderMatrix();renderScripts();if(state.view==='evidence')renderEvidence();
}
function importBusy(status) {return ['uploading','extracting','validating','installing'].includes(status);}
function renderSetup() {
  const data=state.setup;if(!data)return;const toolsReady=Object.values(data.dependencies).every(Boolean),dataset=data.dataset;
  $('#setup-mode').textContent=data.container?'DOCKER LAB':'LOCAL LAB';
  $('#script-permissions-note').textContent=data.container?'Custom scripts run inside your Docker lab.':'Custom scripts run with your local account permissions.';
  $('#setup-tools-status').textContent=toolsReady?'All required tools are installed and ready.':'Missing: '+Object.entries(data.dependencies).filter(([,ok])=>!ok).map(([name])=>name).join(', ');
  $('#setup-tools-badge').textContent=toolsReady?'READY':'NEEDS SETUP';$('#setup-tools-badge').className='tag '+(toolsReady?'cyan':'pink');
  $('#setup-dataset-status').textContent=dataset.pdfs?`${number(dataset.available)} PDFs ready to inspect · ${number(dataset.missing)} observation IDs still have no PDF.`:'Your lab is prepared. Import PDFs or the assignment dataset ZIP to begin.';
  $('#setup-dataset-badge').textContent=dataset.available?'READY':'ADD PDFs';$('#setup-dataset-badge').className='tag '+(dataset.available?'cyan':'pink');
  $('#setup-ready-badge').textContent=data.ready?'READY':'WAITING';$('#setup-ready-badge').className='tag '+(data.ready?'cyan':'');
  $('#setup-workspace-counts').innerHTML=[['PDFs',dataset.pdfs],['Scripts',data.scripts],['Exemplar tools',data.tools]].map(([label,value])=>`<div><b>${number(value)}</b><span>${label}</span></div>`).join('');
  $('#setup-tool-list').innerHTML=Object.entries(data.dependencies).map(([name,ok])=>`<span class="health-item ${ok?'':'missing'}">${ok?'✓':'!'} ${esc(name)}</span>`).join('');
  $('#setup-storage').textContent=`${data.storage} · ${number(Math.floor(data.freeBytes/1024**3))} GiB free. PDFs, saved scripts, notes and results stay available between lab restarts.`;
  $('#setup-native-note').classList.toggle('hidden',data.container);
  $('#setup-next-hint').textContent=data.ready?'Your lab is ready. Start with a small investigation, then explore your PDFs and compare exemplars.':'Add your PDFs and check the tools above to start your first investigation.';
  const blocked=state.uploadBusy||importBusy(data.import.status)||data.activeInvestigation;
  updateRunAvailability();
  $('#setup-first-investigation').disabled=!data.ready||blocked;$('#setup-open-evidence').disabled=!dataset.available;
  $('#dataset-files').disabled=!!blocked;$('#import-dataset').disabled=!state.datasetFiles?.length||!data.canImport||!!state.uploadBusy;
  const message=$('#setup-import-message');message.className=['completed','failed'].includes(data.import.status)?data.import.status==='failed'?'alert':'setup-success':'hidden';message.textContent=data.import.message||'';
  if(data.activeInvestigation){message.className='inspection-notice';message.textContent='An investigation is running. You can import more PDFs when it finishes.';}
  if(importBusy(data.import.status)&&!state.uploadBusy){$('#setup-import-progress').classList.remove('hidden');$('#dataset-progress').removeAttribute('value');$('#dataset-progress-text').textContent=data.import.message||'Preparing your PDFs…';}
  else if(!state.uploadBusy)$('#setup-import-progress').classList.add('hidden');
}
async function loadSetup() {
  clearTimeout(state.setupTimer);const request=state.setupRequest=(state.setupRequest||0)+1;
  try {
    const previous=state.setup?.import?.status,data=await api('/api/setup');if(request!==state.setupRequest)return;
    state.setup=data;renderSetup();
    if((importBusy(data.import.status)||data.activeInvestigation)&&!state.uploadBusy)state.setupTimer=setTimeout(loadSetup,1000);
    if(importBusy(previous)&&data.import.status==='completed'&&!state.uploadBusy)await refreshData();
    return data;
  }catch(error){$('#setup-tools-status').textContent='Could not check the lab. Restart it with the Start Lab launcher, then check again.';$('#setup-import-message').className='alert';$('#setup-import-message').textContent=error.message;}
}
function chooseDataset(files) {
  const selected=Array.from(files),invalid=selected.find(f=>!(/\.(pdf|zip)$/i.test(f.name))||f.size===0||f.size>(state.setup?.maxUploadBytes||4*1024**3));
  state.datasetFiles=invalid?[]:selected;$('#setup-selected').textContent=selected.length?`${selected.length} file${selected.length===1?'':'s'} selected · ${number(Math.ceil(selected.reduce((n,f)=>n+f.size,0)/1024**2))} MiB`:'No files selected.';
  renderSetup();if(invalid){$('#setup-import-message').className='alert';$('#setup-import-message').textContent=`${invalid.name}: choose a non-empty PDF or ZIP no larger than 4 GiB.`;}
}
function uploadDatasetFile(file,index,total) {
  return new Promise((resolve,reject)=>{
    const xhr=new XMLHttpRequest();xhr.open('POST','/api/setup/import?filename='+encodeURIComponent(file.name));xhr.setRequestHeader('X-Lab-Token',state.data.token);xhr.setRequestHeader('Content-Type','application/octet-stream');
    xhr.upload.onprogress=event=>{if(event.lengthComputable){const percent=Math.round(event.loaded/event.total*100);$('#dataset-progress').value=percent;$('#dataset-progress-text').textContent=`Uploading ${index+1}/${total}: ${file.name} · ${percent}%`;}};
    xhr.onload=()=>{let result;try{result=JSON.parse(xhr.responseText);}catch{reject(new Error('The upload returned an unexpected response. Restart the lab and try again.'));return;}if(xhr.status>=200&&xhr.status<300)resolve(result);else reject(new Error(result.error||'The upload failed. Try again.'));};
    xhr.onerror=()=>reject(new Error('Connection lost during upload. Reopen the lab and try again.'));xhr.onabort=()=>reject(new Error('Upload cancelled.'));xhr.send(file);
  });
}
async function importDataset() {
  const files=state.datasetFiles||[];if(!files.length||state.uploadBusy)return;
  state.uploadBusy=true;state.setupRequest++;clearTimeout(state.setupTimer);renderSetup();$('#setup-import-message').className='hidden';$('#setup-import-progress').classList.remove('hidden');
  let imported=0,skipped=0,rejected=[],finalMessage='',failed=false;
  try {
    for(let i=0;i<files.length;i++) {
      $('#dataset-progress').value=0;$('#dataset-progress-text').textContent=`Uploading ${i+1}/${files.length}: ${files[i].name}`;
      await uploadDatasetFile(files[i],i,files.length);$('#dataset-progress').removeAttribute('value');
      while(true) {
        const data=await api('/api/setup');state.setup=data;renderSetup();$('#dataset-progress-text').textContent=`File ${i+1}/${files.length}: ${data.import.message||'Preparing PDFs…'}`;
        if(data.import.status==='failed')throw new Error(data.import.message);
        if(data.import.status==='completed'){imported+=data.import.imported;skipped+=data.import.skipped;rejected.push(...(data.import.rejected||[]));break;}
        await new Promise(resolve=>setTimeout(resolve,1000));
      }
    }
    state.datasetFiles=[];$('#dataset-files').value='';$('#setup-selected').textContent='No files selected.';
    await refreshData();state.uploadBusy=false;await loadSetup();
    finalMessage=`${number(imported)} PDFs added · ${number(skipped)} originals already present. You can now investigate in the web app.`+(rejected.length?` ${number(rejected.length)} files named .pdf did not contain PDF data and were skipped: ${rejected.slice(0,20).join(', ')}${rejected.length>20?' …':''}`:'');
  }catch(error){failed=true;state.uploadBusy=false;await loadSetup();finalMessage=error.message+(imported?` ${number(imported)} PDFs from earlier files in this batch were already added.`:'');}
  finally{state.uploadBusy=false;$('#setup-import-progress').classList.add('hidden');renderSetup();$('#setup-import-message').className=failed?'alert':'setup-success';$('#setup-import-message').textContent=finalMessage;}
}
async function boot() {
  ['#builder-type'].forEach(selector=>$(selector).innerHTML='<option value="">Any resource</option>'+types.map(t=>`<option>${t}</option>`).join(''));
  generateScript();showView(location.hash.slice(1)||'overview');
  try {await refreshData(true);const setup=await loadSetup();if(setup&&!setup.ready)showView('setup');const jobs=await loadHistory();const active=jobs.find(j=>busy(j.status));if(active){state.running=active.id;pollRun(active.id);}else if(jobs.length){const job=await api('/api/jobs/'+jobs[0].id);updateRun(job);setupResults(job);}}
  catch(error){$('#offline').classList.remove('hidden');$('#offline').textContent='Could not connect to the lab. Start Docker, open the Start Lab launcher, then refresh this page. '+error.message;$('#connection-text').textContent='Lab disconnected';$('#connection-dot').classList.add('offline');$('#run-script').disabled=true;}
}
// Delegated controls keep tables interactive after paging and refreshes.
document.addEventListener('click',async event=>{
  const target=event.target.closest('button, a, tr[data-job], [data-summary-tool]');if(!target)return;
  if(target.dataset.view){event.preventDefault();showView(target.dataset.view);}
  if(target.dataset.prefix){state.evidenceMode='resources';state.evidenceOffset=0;state.evidenceSort='document';$('#evidence-search').value=target.dataset.prefix;$$('[data-evidence-mode]').forEach(el=>el.classList.toggle('active',el.dataset.evidenceMode==='resources'));showView('evidence');}
  if(target.dataset.evidenceMode){state.evidenceMode=target.dataset.evidenceMode;state.evidenceOffset=0;state.evidenceSort=state.evidenceMode==='documents'?'id':'document';$$('[data-evidence-mode]').forEach(el=>el.classList.toggle('active',el===target));renderEvidence();}
  if(target.dataset.studioMode)setStudioMode(target.dataset.studioMode);
  if(target.dataset.document)inspectDocument(target.dataset.document,target.dataset.documentTab||'resources');
  if(target.dataset.job)openJob(target.dataset.job);
  if(target.dataset.object)inspectObject(target.dataset.object,target.dataset.decoded==='1',target.dataset.objectTarget||'resources');
  if(target.dataset.closeObject)$('#'+target.dataset.closeObject)?.classList.add('hidden');
  if(target.dataset.inspectTab)selectInspectorTab(target.dataset.inspectTab);
  if(target.dataset.pdfTag){$('#strings-mode').value='objects';$('#strings-tag').value=target.dataset.pdfTag;state.strings.offset=0;loadStrings();}
  if(target.id==='clear-strings'){$('#strings-search').value='';$('#strings-tag').value='';$('#strings-case').checked=false;state.strings.offset=0;loadStrings();}
  if(target.dataset.investigate){$('#builder-documents').value=target.dataset.investigate;$('#builder-tool').value='';$('#builder-type').value='';$('#builder-prefix').value='';$('#template-mode').value='resources';generateScript();setStudioMode('editor');$('#inspector').close();state.inspector=null;showView('scripts');}
  if(target.dataset.pageContext==='evidence'){state.evidenceOffset=Number(target.dataset.page);renderEvidence();}
  if(target.dataset.pageContext==='strings'){state.strings.offset=Number(target.dataset.page);loadStrings();}
  if(target.dataset.pageContext==='result'){state.resultOffset=Number(target.dataset.page);renderResults();}
  if(target.dataset.pageContext==='summary'){state.summaryOffset=Number(target.dataset.page);generateSummary();}
  if(target.dataset.summaryTool){$('#summary-tool').value=$('#summary-tool').value===target.dataset.summaryTool?'':target.dataset.summaryTool;state.summaryOffset=0;generateSummary();}
  if(target.dataset.sortContext==='evidence'){state.evidenceDirection=state.evidenceSort===target.dataset.sort&&state.evidenceDirection==='asc'?'desc':'asc';state.evidenceSort=target.dataset.sort;state.evidenceOffset=0;renderEvidence();}
  if(target.dataset.sortContext==='result'){state.resultDirection=state.resultSort===target.dataset.sort&&state.resultDirection==='asc'?'desc':'asc';state.resultSort=target.dataset.sort;state.resultOffset=0;renderResults();}
  if(target.id==='save-document-notes'){try{state.notes[state.inspector]=$('#document-notes').value;await saveNotes();toast('Document notes saved.');}catch(error){toast(error.message,true);}}
});
$('#global-search').addEventListener('input',debounce(()=>{state.evidenceMode='documents';state.evidenceOffset=0;$('#evidence-search').value=$('#global-search').value;$$('[data-evidence-mode]').forEach(el=>el.classList.toggle('active',el.dataset.evidenceMode==='documents'));showView('evidence');}));
$('#evidence-search').addEventListener('input',debounce(()=>{state.evidenceOffset=0;renderEvidence();}));
['#evidence-tool','#evidence-type'].forEach(id=>$(id).addEventListener('change',()=>{state.evidenceOffset=0;renderEvidence();}));
$('#sparse-threshold').addEventListener('input',renderMatrix);
$('#export-matrix').addEventListener('click',()=>{if(!state.data)return;const rows=matrixRows();download('tool-prefix-matrix.csv',csv(['tool','producer','exemplars',...types],rows),'text/csv');});
$('#export-evidence').addEventListener('click',()=>{if(!state.data)return;if(state.evidenceMode==='resources'){const query=evidenceQuery();query.set('export','csv');location.href='/api/resources?'+query;}else{const q=$('#evidence-search').value.toLowerCase(),tool=$('#evidence-tool').value;const rows=state.data.documents.filter(d=>(!q||[d.id,d.producer,d.creator,...d.tools].join(' ').toLowerCase().includes(q))&&(!tool||d.tools.includes(tool))).map(d=>({...d,tools:d.tools.join('; ')}));download('document-evidence.csv',csv(['id','producer','creator','tools','resources','marks','available'],rows),'text/csv');}});
$('#script-select').addEventListener('change',()=>{$('#script-arguments').value='';updateScriptDescription();});
$('#generate-script').addEventListener('click',generateScript);
$('#script-source').addEventListener('input',()=>{editorLines();$('#save-status').textContent='Unsaved changes';});
$('#script-source').addEventListener('keydown',event=>{if(event.key==='Tab'){event.preventDefault();const el=event.target,start=el.selectionStart,end=el.selectionEnd;el.setRangeText('  ',start,end,'end');editorLines();}});
$('#save-script').addEventListener('click',async()=>{try{await saveScript();toast('Investigation script saved.');}catch(error){toast(error.message,true);$('#save-status').textContent=error.message;}});
$('#edit-script').addEventListener('click',async()=>{try{const id=$('#script-select').value,result=await api('/api/script?id='+encodeURIComponent(id));$('#script-source').value=result.source;$('#script-name').value=id.startsWith('custom:')?id.slice(7).replace(/\.sh$/,''):id.replace(/\.sh$/,'')+'-custom';$('#save-status').textContent='Editable copy';editorLines();setStudioMode('editor');}catch(error){toast(error.message,true);}});
$('#run-script').addEventListener('click',startRun);
$('#cancel-run').addEventListener('click',async()=>{try{if(state.running){await api(`/api/jobs/${state.running}/cancel`,{});pollRun(state.running);}}catch(error){toast(error.message,true);}});
$('#jump-results').addEventListener('click',()=>$('#investigation-results').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'}));
$('#result-select').addEventListener('change',()=>{state.resultOffset=0;resetSummary();renderResults();});
$('#result-search').addEventListener('input',debounce(()=>{state.resultOffset=0;renderResults();if(state.summaryActive){state.summaryOffset=0;generateSummary();}}));
$('#export-results').addEventListener('click',()=>{if(state.job){const query=resultQuery();query.set('export','csv');location.href=`/api/jobs/${state.job.id}/table?${query}`;}});
$('#generate-summary').addEventListener('click',()=>{state.summaryOffset=0;generateSummary(true);});
['#summary-document','#summary-group','#summary-tool','#summary-type'].forEach(id=>$(id).addEventListener('change',()=>{state.summaryOffset=0;generateSummary();}));
$('#summary-metric').addEventListener('change',renderSummaryChart);
$('#summary-unassigned').addEventListener('change',renderSummaryChart);
$('#close-summary').addEventListener('click',()=>{state.summaryActive=false;state.summaryRequest++;$('#results-summary').classList.add('hidden');});
$('#export-summary').addEventListener('click',()=>{if(!state.summaryData)return;const query=new URLSearchParams(state.summaryExportQuery);query.set('export','csv');location.href=`/api/jobs/${state.summaryData.job}/summary?${query}`;});
$('#export-summary-chart').addEventListener('click',()=>{const svg=$('#summary-chart svg');if(svg&&state.summaryData)download(`${state.summaryData.job}-${state.summaryData.source.replace(/\.[^.]+$/,'')}-${$('#summary-metric').value}-summary.svg`,svg.outerHTML,'image/svg+xml');});
$('#summary-chart').addEventListener('keydown',event=>{const bar=event.target.closest('[data-summary-tool]');if(bar&&['Enter',' '].includes(event.key)){event.preventDefault();bar.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
$('#save-notes').addEventListener('click',async()=>{state.notes._notebook=$('#notebook-text').value;try{await saveNotes();$('#notes-status').textContent='Saved '+new Date().toLocaleTimeString();}catch(error){toast(error.message,true);}});
$('#export-notes').addEventListener('click',()=>{state.notes._notebook=$('#notebook-text').value;const text=['# PDF Analyzer — Investigation notes',state.notes._notebook||'',...Object.entries(state.notes).filter(([key])=>key!=='_notebook').map(([key,value])=>`## ${key}\n\n${value}`)].join('\n\n');download('pdf-investigation-notes.md',text);});
$('#refresh').addEventListener('click',async()=>{$('#refresh').classList.add('refreshing');try{await refreshData(!state.data);toast('Evidence refreshed.');}catch(error){toast(error.message,true);}finally{$('#refresh').classList.remove('refreshing');}});
$('#dataset-files').addEventListener('change',event=>chooseDataset(event.target.files));
$('#dataset-drop').addEventListener('dragover',event=>{event.preventDefault();if(!state.uploadBusy)$('#dataset-drop').classList.add('dragging');});
$('#dataset-drop').addEventListener('dragleave',()=>$('#dataset-drop').classList.remove('dragging'));
$('#dataset-drop').addEventListener('drop',event=>{event.preventDefault();$('#dataset-drop').classList.remove('dragging');if(!state.uploadBusy&&state.setup?.canImport)chooseDataset(event.dataTransfer.files);});
$('#import-dataset').addEventListener('click',importDataset);
$('#refresh-setup').addEventListener('click',loadSetup);
$('#setup-open-evidence').addEventListener('click',()=>showView('evidence'));
$('#setup-first-investigation').addEventListener('click',()=>{const first=state.data?.documents.find(d=>d.available);if(!first)return;$('#builder-documents').value=first.id;$('#builder-tool').value='';$('#builder-type').value='';$('#builder-prefix').value='';$('#template-mode').value='resources';generateScript();setStudioMode('editor');showView('scripts');});
$('#close-inspector').addEventListener('click',()=>{$('#inspector').close();state.inspector=null;});
$('#inspector').addEventListener('cancel',()=>state.inspector=null);
$('#inspector').addEventListener('click',event=>{if(event.target===$('#inspector')){const rect=event.target.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom){event.target.close();state.inspector=null;}}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('#inspector').open){event.preventDefault();$('#global-search').focus();}});
document.addEventListener('pointerdown',event=>{const button=event.target.closest('.primary, .nav-item');if(!button||button.disabled||matchMedia('(prefers-reduced-motion: reduce)').matches)return;const rect=button.getBoundingClientRect(),ripple=document.createElement('span');ripple.className='click-ripple';ripple.style.left=(event.clientX-rect.left)+'px';ripple.style.top=(event.clientY-rect.top)+'px';button.append(ripple);setTimeout(()=>ripple.remove(),650);});
boot();

const searchInspector=debounce(event=>{if(event.target.id==='strings-search'&&state.inspector){state.strings.offset=0;loadStrings();}else if(event.target.id==='metadata-search')renderMetadata();},200);
document.addEventListener('input',event=>{if(['strings-search','metadata-search'].includes(event.target.id))searchInspector(event);});
document.addEventListener('change',event=>{if(['strings-mode','strings-minimum','strings-tag','strings-case'].includes(event.target.id)&&state.inspector){state.strings.offset=0;if(event.target.id==='strings-mode'){$('#strings-tag').value='';$('#strings-object-preview').classList.add('hidden');}loadStrings();}});
