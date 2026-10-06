'use strict';

// Markdown stays as plain text in saved notes; only the reading view is rendered.
function noteEditorMarkup(sourceId, value, label) {
  return `<div class="note-editor" data-note-editor>
    <div class="note-toolbar"><div class="segmented" role="group" aria-label="${label} view">
      <button type="button" data-note-mode="read" aria-pressed="false">Read</button>
      <button type="button" data-note-mode="edit" aria-pressed="false">Edit</button>
      <button type="button" data-note-mode="split" aria-pressed="false">Split</button>
    </div><span class="muted small">Markdown · headings, lists, tables &amp; code</span></div>
    <div class="note-layout"><label class="field note-source">${label}
      <textarea id="${sourceId}" aria-label="${label}" spellcheck="true" placeholder="# Investigation notes&#10;&#10;## Hypothesis&#10;What are you testing?&#10;&#10;## Evidence&#10;- PDF ID and original object reference&#10;&#10;## Findings&#10;Observations, limitations and counterexamples">${escapeNoteText(value)}</textarea>
    </label><div class="note-reading"><details class="note-contents" hidden><summary>On this page</summary><nav aria-label="Note headings"></nav></details><article class="markdown-note" aria-label="${label} preview"></article></div></div>
  </div>`;
}

function escapeNoteText(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));
}

function renderNotePreview(editor) {
  const source=editor.querySelector('textarea'), preview=editor.querySelector('.markdown-note');
  const text=source.value;
  if (!text.trim()) {
    preview.innerHTML='<div class="note-empty"><span class="label">YOUR EVIDENCE, YOUR WORDS</span><h3>Your notebook starts here</h3><p>Choose Edit to write notes. Use # for headings, - for lists and backticks for PDF tags or code.</p></div>';
  } else if (!window.marked || !window.DOMPurify) {
    preview.textContent=text;
  } else {
    preview.innerHTML=DOMPurify.sanitize(marked.parse(text, {gfm:true, breaks:false}), {
      ALLOWED_TAGS:['h1','h2','h3','h4','h5','h6','p','br','hr','strong','em','del','s','blockquote','ul','ol','li','pre','code','a','table','thead','tbody','tr','th','td','input'],
      ALLOWED_ATTR:['href','title','start','align','type','checked','disabled'],
      ALLOW_DATA_ATTR:false, ALLOW_ARIA_ATTR:false
    });
    preview.querySelectorAll('input').forEach(input=>{input.type='checkbox';input.disabled=true;input.tabIndex=-1;});
    preview.querySelectorAll('a').forEach(link=>{
      const href=link.getAttribute('href')||'';
      if(!/^(https?:\/\/|mailto:|#)/i.test(href)){link.removeAttribute('href');return;}
      if(!href.startsWith('#')){link.target='_blank';link.rel='noopener noreferrer';}
    });
    preview.querySelectorAll('table').forEach(table=>{const wrap=document.createElement('div');wrap.className='note-table-scroll';table.replaceWith(wrap);wrap.append(table);});
  }
  const headings=[...preview.querySelectorAll('h1,h2,h3,h4,h5,h6')],contents=editor.querySelector('.note-contents');
  contents.hidden=!text.trim()||headings.length<2;
  const slugs=new Map();
  headings.forEach((heading,index)=>{
    const slug=heading.textContent.toLowerCase().replace(/[^\p{L}\p{N}_ -]/gu,'').trim().replace(/\s+/g,'-')||'heading';
    const count=slugs.get(slug)||0;slugs.set(slug,count+1);heading.dataset.noteSlug=slug+(count?'-'+count:'');
    heading.id=source.id+'-heading-'+index;
  });
  contents.querySelector('nav').innerHTML=headings.map(heading=>`<a href="#${heading.id}" data-note-heading="${heading.id}" class="note-heading-level-${heading.tagName.slice(1)}">${escapeNoteText(heading.textContent)}</a>`).join('');
  preview.querySelectorAll('a[href^="#"]').forEach(link=>{
    let slug;try{slug=decodeURIComponent(link.getAttribute('href').slice(1));}catch{return;}
    const heading=headings.find(item=>item.dataset.noteSlug===slug);
    if(heading){link.href='#'+heading.id;link.dataset.noteHeading=heading.id;}
  });
}

function setNoteMode(editor, mode) {
  editor.dataset.mode=mode;
  editor.querySelector('.note-source').hidden=mode==='read';
  editor.querySelector('.note-reading').hidden=mode==='edit';
  editor.querySelectorAll('[data-note-mode]').forEach(button=>{
    const active=button.dataset.noteMode===mode;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
  });
  if(mode!=='edit')renderNotePreview(editor);
}

function initNoteEditor(editor) {
  if(!editor)return;
  const source=editor.querySelector('textarea');source.dataset.savedNote=source.value;
  setNoteMode(editor,source.value.trim()?'read':'edit');
}

function noteSaved(id, value) {
  const source=document.getElementById(id);if(source)source.dataset.savedNote=value;
}

document.addEventListener('click',event=>{
  const button=event.target.closest('[data-note-mode]');
  if(button){const editor=button.closest('[data-note-editor]');setNoteMode(editor,button.dataset.noteMode);if(button.dataset.noteMode==='edit')editor.querySelector('textarea').focus();}
  const link=event.target.closest('[data-note-heading]');
  if(link){event.preventDefault();document.getElementById(link.dataset.noteHeading)?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
});

let notePreviewTimer;
document.addEventListener('input',event=>{
  const editor=event.target.closest('[data-note-editor]');if(!editor||event.target.tagName!=='TEXTAREA')return;
  const status=document.getElementById(event.target.id==='notebook-text'?'notes-status':'document-notes-status');
  if(status)status.textContent=event.target.value===event.target.dataset.savedNote?'':'Unsaved changes';
  clearTimeout(notePreviewTimer);notePreviewTimer=setTimeout(()=>{if(editor.isConnected&&editor.dataset.mode!=='edit')renderNotePreview(editor);},150);
});
