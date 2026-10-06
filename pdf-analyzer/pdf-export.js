'use strict';
let pdfExportBusy=false,pdfFontPromise;
function updatePDFButtons() {
  document.querySelectorAll('[data-pdf-export]').forEach(button=>{
    const kind=button.dataset.pdfExport;
    const unavailable=kind==='notebook'?false:['document','object'].includes(kind)?!state.inspector:kind==='summary'?(!state.summaryData||$('#export-summary').disabled):kind==='run'?(!state.job||busy(state.job.status)):kind==='results'?!state.job?.tables?.length:!state.data;
    button.disabled=pdfExportBusy||unavailable;
  });
}
function pdfProgress(message) {const el=document.querySelector('#pdf-export-progress');el.textContent=message;el.classList.remove('hidden');}
async function pdfFonts() {
  if(!pdfFontPromise)pdfFontPromise=Promise.all(['DejaVuSans.ttf','DejaVuSans-Bold.ttf'].map(async name=>{
    const response=await fetch(new URL('vendor/'+name,document.baseURI));if(!response.ok)throw new Error('PDF fonts could not load. Refresh the app and retry.');
    const bytes=new Uint8Array(await response.arrayBuffer());let binary='';
    for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
    return {name,data:btoa(binary)};
  }));
  return pdfFontPromise;
}
async function fullPDFTable(path,parameters) {
  const query=new URLSearchParams(parameters);query.set('export','json');query.delete('offset');query.delete('limit');
  const data=await api(path+'?'+query);
  if(!Array.isArray(data.headers)||!Array.isArray(data.rows))throw new Error('Restart the lab to enable complete PDF exports.');
  return data;
}
function pdfTable(title,headers,rows) {return {title,headers,rows};}
async function buildPDFReport(kind,button) {
  const report={title:'PDF Analyzer evidence',details:[],sections:[],filename:'pdf-analyzer-evidence.pdf'};
  const tableRows=(headers,rows)=>rows.map(row=>headers.map(key=>String(row[key]??'')));
  const addTable=(title,data)=>report.sections.push(pdfTable(title,data.headers,tableRows(data.headers,data.rows)));
  if(kind==='evidence') {
    const mode=state.evidenceMode,query=evidenceQuery(),search=normalizeDocumentSearch($('#evidence-search').value),tool=$('#evidence-tool').value;
    report.title=mode==='documents'?'Document evidence':'Resource evidence';report.filename=mode+'-evidence.pdf';
    report.details=[`Search: ${search||'none'} | Exemplar tool: ${tool||'all'} | Resource type: ${query.get('type')||'all'}`,'All matching rows, across every page.'];
    if(mode==='resources')addTable('Resource marks',await fullPDFTable('/api/resources',query));
    else {
      const headers=['id','producer','creator','tools','resources','marks','available'];
      const rows=state.data.documents.filter(d=>(!search||[d.id,d.producer,d.creator,...d.tools].join(' ').toLowerCase().includes(search.toLowerCase()))&&(!tool||d.tools.includes(tool))).map(d=>({...d,tools:d.tools.join('; ')}));
      rows.sort((a,b)=>{const x=a[state.evidenceSort]??'',y=b[state.evidenceSort]??'';return (typeof x==='number'?x-y:String(x).localeCompare(String(y)))*(state.evidenceDirection==='desc'?-1:1);});
      addTable('Matching documents',{headers,rows});
    }
  } else if(kind==='matrix') {
    report.title='Tool signature comparison';report.filename='tool-signature-comparison.pdf';
    report.details=[`Sparse evidence threshold: ${$('#sparse-threshold').value} documents`,'Counts show distinct matching exemplars. A question mark indicates incomplete evidence, not a proven absence.'];
    addTable('Resource prefixes by exemplar tool',{headers:['tool','producer','exemplars',...types],rows:matrixRows()});
  } else if(kind==='results') {
    const id=state.job.id,label=state.job.label,query=resultQuery(),name=query.get('name');
    report.title='Investigation results';report.filename=id+'-'+name.replace(/\.[^.]+$/,'')+'.pdf';
    report.details=[`Investigation: ${label} | Run: ${id}`,`Table: ${name} | Search: ${query.get('q')||'none'}`,'All matching rows, across every page.'];
    addTable(name,await fullPDFTable(`/api/jobs/${id}/table`,query));
  } else if(kind==='run') {
    const id=state.job.id,job=await api(`/api/jobs/${id}/report`);
    report.title='Complete investigation run';report.filename=id+'-complete-run.pdf';
    report.details=[`Investigation: ${job.label} | Run: ${id}`,`Status: ${job.status} | Exit: ${job.exitCode??'pending'} | Created: ${job.createdAt}`,'All saved tables without search filters, followed by complete console output.'];
    for(const item of job.tables||[])addTable(item.name,await fullPDFTable(`/api/jobs/${id}/table`,{name:item.name}));
    report.sections.push({title:'Standard output',text:job.stdout||'(No output)'},{title:'Progress and errors',text:[job.stderr,job.error].filter(Boolean).join('\n')||'(No errors)'});
  } else if(kind==='summary') {
    const query=new URLSearchParams(state.summaryExportQuery),id=state.summaryData.job,metric=$('#summary-metric').value,includeUnassigned=$('#summary-unassigned').checked,caveat=$('#summary-caveat').textContent;
    query.set('export','json');const data=await api(`/api/jobs/${id}/summary?${query}`);
    report.title='Results across exemplars';report.filename=id+'-'+data.source.replace(/\.[^.]+$/,'')+'-summary.pdf';
    report.details=[`Run: ${id} | Table: ${data.source}`,`Search: ${data.scope.query||'none'} | Tool: ${data.scope.tool||'all'} | Resource type: ${data.scope.resourceType||'all'}`,`${data.counts.matchedRows} matching rows | ${data.counts.matchedDocuments} distinct PDFs | ${data.counts.sourceRows} rows in full source`,caveat];
    report.sections.push({title:'Evidence by exemplar tool',chart:data.overview.filter(r=>r.toolKey!=='__unassigned__'||includeUnassigned||data.scope.tool==='__unassigned__'),metric});
    const headers=['tool','producer',...data.groups,'rows','documents','exemplars','represented','coverage'];
    const rows=data.rows.map(row=>({...row,...Object.fromEntries(data.groups.map((key,i)=>[key,row.values[i]])),coverage:row.coverage===null?'n/a':row.coverage+'%'}));
    addTable('Full summary breakdown',{headers,rows});
  } else if(kind==='document') {
    const id=state.inspector,tab=$('[data-inspect-tab].active')?.dataset.inspectTab||'resources';
    report.title=id+' · '+tab;report.filename=id+'-'+tab+'-evidence.pdf';report.details=[`Document ID: ${id}`];
    if(tab==='strings') {
      const query=stringsQuery(),data=await fullPDFTable(`/api/documents/${id}/strings`,query);
      report.details.push(`View: ${query.get('mode')} | Search: ${query.get('q')||'none'} | Exact tag: ${query.get('tag')||'all'} | Minimum length: ${query.get('minimum')} | Match case: ${query.get('case')==='1'?'yes':'no'}`,data.source||'');
      if(data.truncated)report.details.push(`Index limited to ${data.indexLimit}. This report covers all matching indexed records.`);
      if(data.warning)report.details.push(data.warning);addTable('All matching strings and tags',data);
    } else if(tab==='metadata') {
      const query=$('#metadata-search').value.toLowerCase(),data=await api(`/api/documents/${id}/metadata`);
      report.details.push(data.source,`Filename: ${data.filename} | Bytes: ${data.bytes} | Search: ${query||'none'}`);
      if(data.warning)report.details.push(data.warning);
      const groups=[['Document properties',Object.entries(data.pdfinfo).filter(([key])=>key!=='document').map(([field,value])=>({field,value}))],['Info dictionary',data.info],['Trailer and identifiers',data.trailer]];
      for(const [title,rows] of groups)addTable(title,{headers:['field','value'],rows:rows.filter(row=>(row.field+' '+row.value).toLowerCase().includes(query))});
      if(data.xmp&&(!query||data.xmp.toLowerCase().includes(query)))report.sections.push({title:'XMP metadata',text:data.xmp});
      if(data.truncated)report.details.push('XMP is limited to the 2,000,000 decoded byte preview provided by the metadata tool.');
    } else if(tab==='notes') report.sections.push({title:'Document notes',text:$('#document-notes').value||'(No notes)'});
    else {
      const data=await api(`/api/documents/${id}`);report.details.push(data.source,`Original filename: ${data.filename}`);
      if(data.warning)report.details.push('QPDF warning: '+data.warning);
      if(tab==='resources')addTable('All scoped resources',{headers:['resource_type','subtype','resource_name','prefix','number','reference','scope'],rows:data.resources});
      if(tab==='numbering') {
        report.details.push('Numbers are grouped by type, prefix and local scope. Gaps and reused names alone do not prove editing.');
        addTable('Numbering by local scope',{headers:['resource_type','prefix','scope','start','end','distinct_numbers','missing_between','suffix_equals_object','entries'],rows:data.numbering});
        const grouped=new Map();for(const row of data.resources){const key=row.resource_type+':'+row.resource_name;if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(row);}
        const rows=[...grouped.values()].filter(rows=>new Set(rows.map(r=>r.scope)).size>1).map(rows=>({type:rows[0].resource_type,name:rows[0].resource_name,scopes:[...new Set(rows.map(r=>r.scope))].join('; '),targets:[...new Set(rows.map(r=>r.reference))].join('; ')}));
        addTable('Names reused across scopes',{headers:['type','name','scopes','targets'],rows});
      }
      if(tab==='marks')addTable('Observed toolmarks',{headers:['mark'],rows:data.marks.map(mark=>({mark}))});
    }
  } else if(kind==='object') {
    const id=button.dataset.reportDocument,ref=button.dataset.reportObject,decoded=button.dataset.reportDecoded;
    const data=await api(`/api/documents/${id}/object?`+new URLSearchParams({ref,decoded}));
    report.title=id+' · '+(decoded==='1'?'Decoded stream':'Original object')+' '+ref.replace(',',' ');
    report.filename=id+'-object-'+ref.replace(',','-')+'.pdf';report.details=[data.source,`Bytes: ${data.bytes}`];
    if(data.truncated)report.details.push(`Preview limited to ${data.limit} bytes.`);
    if(data.warning)report.details.push(data.warning);
    report.sections.push({title:'Object evidence',text:data.text});
  } else if(kind==='notebook') {
    report.title='Investigation notebook';report.filename='pdf-investigation-notes.pdf';
    report.sections.push({title:'Investigation notes',text:$('#notebook-text').value||'(No notebook notes)'},...Object.entries(state.notes).filter(([key])=>key!=='_notebook').map(([key,text])=>({title:key+' · Document notes',text})));
  } else throw new Error('Unknown PDF export.');
  return report;
}
async function renderPDFReport(report,save=true) {
  if(!window.jspdf?.jsPDF)throw new Error('PDF tools have not loaded. Refresh the app and retry.');
  const fonts=await pdfFonts(),pdf=new window.jspdf.jsPDF({orientation:'landscape',unit:'mm',format:'a4',compress:true,putOnlyUsedFonts:true});
  fonts.forEach((font,i)=>{pdf.addFileToVFS(font.name,font.data);pdf.addFont(font.name,'LabSans',i?'bold':'normal');});
  pdf.setFont('LabSans','normal');pdf.setProperties({title:report.title,subject:'PDF investigation evidence',creator:'PDF Analyzer · Vice Lab'});
  const width=pdf.internal.pageSize.getWidth(),height=pdf.internal.pageSize.getHeight(),margin=14,bottom=height-16;
  let y=23;
  function page() {pdf.addPage();y=22;}
  function heading(text) {if(y>bottom-15)page();pdf.setFont('LabSans','bold');pdf.setFontSize(13);pdf.setTextColor(60,34,80);const lines=pdf.splitTextToSize(text,width-margin*2);for(const line of lines){if(y>bottom-8)page();pdf.text(line,margin,y);y+=6;}pdf.setFont('LabSans','normal');y+=3;}
  function textBlock(text) {pdf.setFontSize(9);pdf.setTextColor(45,45,55);const lines=pdf.splitTextToSize(String(text),width-margin*2);for(const line of lines){if(y>bottom-5)page();pdf.text(line,margin,y);y+=4.5;}y+=3;}
  heading(report.title);textBlock('Generated: '+new Date().toISOString());
  for(const detail of report.details||[])if(detail)textBlock(detail);
  for(const section of report.sections) {
    if(section.chart) {
      const rows=section.chart,required=20+rows.length*7;if(y+required>bottom)page();heading(section.title);
      const label={documents:'Distinct PDFs',rows:'Result rows',coverage:'Observed coverage (%)'}[section.metric];textBlock(label);
      const maximum=section.metric==='coverage'?100:Math.max(1,...rows.map(row=>row[section.metric]||0));
      for(const [i,row] of rows.entries()) {
        if(y+8>bottom){page();heading(section.title+' (continued)');}
        const value=row[section.metric],plot=width-90;
        pdf.setFontSize(9);pdf.setTextColor(45,45,55);pdf.text(row.tool,margin,y+4);
        pdf.setFillColor(235,237,241);pdf.rect(margin+26,y,plot,5,'F');
        pdf.setFillColor(...(i%2?[35,135,140]:[180,65,120]));pdf.rect(margin+26,y,plot*(value||0)/maximum,5,'F');
        pdf.text(value===null?'n/a':String(value)+(section.metric==='coverage'?'%':''),margin+30+plot,y+4);y+=7;
      }
      y+=5;continue;
    }
    heading(section.title);
    if(section.text!==undefined){textBlock(section.text);continue;}
    if(!section.rows.length){textBlock('No matching rows.');continue;}
    textBlock(section.rows.length.toLocaleString()+' rows');
    // Yield between chunks so long exports keep the GUI responsive. No row cap.
    for(let offset=0;offset<section.rows.length;offset+=1000) {
      pdfProgress(`Building PDF: ${section.title} · ${Math.min(offset+1000,section.rows.length).toLocaleString()} / ${section.rows.length.toLocaleString()} rows`);
      pdf.autoTable({head:[section.headers.map(header=>header.replaceAll('_',' '))],body:section.rows.slice(offset,offset+1000),startY:y,
        margin:{top:19,right:margin,bottom:18,left:margin},styles:{font:'LabSans',fontSize:7.5,cellPadding:1.6,overflow:'linebreak',textColor:[35,35,45]},
        headStyles:{fillColor:[67,45,84],fontStyle:'bold',textColor:[255,255,255]},alternateRowStyles:{fillColor:[244,246,250]},showHead:'everyPage',rowPageBreak:'auto'});
      y=pdf.lastAutoTable.finalY+5;
      if(offset+1000<section.rows.length&&y>bottom-12)page();
      await new Promise(resolve=>setTimeout(resolve,0));
    }
  }
  const count=pdf.getNumberOfPages();
  for(let i=1;i<=count;i++){pdf.setPage(i);pdf.setFont('LabSans','normal');pdf.setFontSize(8);pdf.setTextColor(100,100,110);pdf.text('PDF Analyzer · Vice Lab',margin,height-8);pdf.text(`${i} / ${count}`,width-margin,height-8,{align:'right'});}
  if(save)pdf.save(report.filename);
  return pdf;
}
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-pdf-export]');if(!button||button.disabled||pdfExportBusy)return;
  pdfExportBusy=true;updatePDFButtons();pdfProgress('Preparing the complete PDF report…');
  try {await renderPDFReport(await buildPDFReport(button.dataset.pdfExport,button));pdfProgress('PDF downloaded.');}
  catch(error){pdfProgress('PDF export failed: '+error.message);toast(error.message,true);}
  finally{pdfExportBusy=false;updatePDFButtons();const el=$('#pdf-export-progress'),message=el.textContent;setTimeout(()=>{if(!pdfExportBusy&&el.textContent===message)el.classList.add('hidden');},6000);}
});
