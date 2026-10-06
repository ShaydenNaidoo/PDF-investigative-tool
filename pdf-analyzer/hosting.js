'use strict';
const pagesHosting=document.documentElement.dataset.hosting==='pages';
let labConnection={url:'',key:''};
try {
  const url=localStorage.getItem('pdf-analyzer.backend-url')||'';
  const session=JSON.parse(sessionStorage.getItem('pdf-analyzer.connection')||'{}');
  labConnection={url,key:session.url===url?session.key||'':''};
} catch { /* Browser storage is optional until a connection is saved. */ }
function labURL(path) {return (labConnection.url||location.origin)+path;}
function openLabConnection(message='') {
  document.querySelector('#lab-url').value=labConnection.url||(!pagesHosting?location.origin:'');
  document.querySelector('#lab-access-key').value=labConnection.key;
  document.querySelector('#lab-connect-status').textContent=message;
  const dialog=document.querySelector('#lab-connection');if(!dialog.open)dialog.showModal();
}
async function labRequest(path,options={}) {
  if(pagesHosting&&!labConnection.url){openLabConnection('Connect your Render lab to start investigating.');throw new Error('Connect your Render lab first.');}
  const headers=new Headers(options.headers||{});
  if(labConnection.key)headers.set('Authorization','Bearer '+labConnection.key);
  const response=await fetch(labURL(path),{...options,headers,credentials:'omit'});
  if(response.status===401)openLabConnection('Enter your lab access key to reconnect.');
  return response;
}
function downloadLabBlob(blob,filename) {
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
}
async function downloadLabFile(path) {
  const response=await labRequest(path);
  if(!response.ok){const error=await response.json();throw new Error(error.error||'Export failed.');}
  const filename=response.headers.get('Content-Disposition')?.match(/filename="([^"]+)"/)?.[1]||'lab-export';
  downloadLabBlob(await response.blob(),filename);
}
document.querySelector('#connect-lab').addEventListener('click',()=>openLabConnection());
document.querySelector('#close-lab-connection').addEventListener('click',()=>document.querySelector('#lab-connection').close());
document.querySelector('#lab-connect-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=document.querySelector('#save-lab-connection'),status=document.querySelector('#lab-connect-status'),previous=labConnection;
  button.disabled=true;status.textContent='Connecting to your lab…';
  try {
    const input=document.querySelector('#lab-url').value.trim(),url=new URL(input||location.origin);
    if(url.username||url.password||url.search||url.hash||url.pathname!=='/')throw new Error('Use the lab’s base URL, without a path or login details.');
    if(url.protocol!=='https:'&&!(url.protocol==='http:'&&['localhost','127.0.0.1'].includes(url.hostname)))throw new Error('Use an HTTPS lab URL.');
    labConnection={url:url.origin===location.origin&&!pagesHosting?'':url.origin,key:document.querySelector('#lab-access-key').value.trim()};
    const response=await labRequest('/api/dashboard');
    if(!response.ok){const error=await response.json();throw new Error(error.error||'Could not connect.');}
    const data=await response.json();if(!Array.isArray(data.documents)||!data.token)throw new Error('This URL is not a PDF Analyzer lab.');
    try {localStorage.setItem('pdf-analyzer.backend-url',labConnection.url);sessionStorage.setItem('pdf-analyzer.connection',JSON.stringify(labConnection));}
    catch {throw new Error('Allow browser storage for this site to save the connection.');}
    location.reload();
  } catch(error){labConnection=previous;status.textContent=error.message==='Failed to fetch'?'Could not reach the lab. Check its URL, readiness, and allowed origin in Render.':error.message;}
  finally{button.disabled=false;}
});
document.querySelector('#forget-lab-connection').addEventListener('click',()=>{
  try {localStorage.removeItem('pdf-analyzer.backend-url');sessionStorage.removeItem('pdf-analyzer.connection');}catch{}
  labConnection={url:'',key:''};location.reload();
});
// API attachments use authenticated fetch; access keys never appear in URLs.
document.addEventListener('click',async event=>{
  const link=event.target.closest('a[href^="/api/"]');if(!link)return;
  event.preventDefault();const path=link.getAttribute('href');
  try {
    if(link.id==='open-pdf'){
      const tab=window.open('about:blank','_blank');
      try {const response=await labRequest(path);if(!response.ok)throw new Error('Could not open the original PDF.');const blob=await response.blob(),url=URL.createObjectURL(blob);if(tab)tab.location.replace(url);else downloadLabBlob(blob,(typeof state!=='undefined'?state.inspector:'document')+'.pdf');setTimeout(()=>URL.revokeObjectURL(url),300000);}
      catch(error){if(tab)tab.close();throw error;}
    }else await downloadLabFile(path);
  }catch(error){if(typeof toast==='function')toast(error.message,true);}
});
