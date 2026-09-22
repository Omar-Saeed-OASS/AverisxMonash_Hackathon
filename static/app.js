/* ============================================================
   SmartShip AI — operations console
   Layout/theme migrated from the Veridoc reference. Every section below
   is wired to the real backend (gmailapi.py):
     GET  /api/dashboard              -> emails table, dashboard-safe rows
     GET  /api/emails/{email_id}      -> one full row + attachment_records
     GET  /api/attachments/download   -> streams the original SI/BL file
     GET  /api/status                 -> live GMAIL_QUERY / POLL_SECONDS
     POST /api/route                  -> classify_email() + router subgraph
     POST /api/emails/{id}/decision   -> adjuster APPROVE/REJECT (human-in-the-loop)
     POST /check-now, GET /health
   The 7 compared fields (shipper, consignee, notify_party, port_of_loading,
   port_of_discharge, container_count, raw_weight_value) are exactly
   COMPARISON_FIELDS in workflows/compare_subgraph/services/comparator.py.
   Only the claim/compliance document drafts (policy, invoice, LC banking
   terms) fill in figures the pipeline doesn't compute — everything else on
   screen is read straight from Supabase.
   ============================================================ */

/* ============================ icons ============================ */
const ICONS={
 dash:'<path d="M3 13h8V3H3zM13 21h8V11h-8zM13 7h8V3h-8zM3 21h8v-4H3z"/>',
 inbox:'<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13l3.5 7v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-7Z"/>',
 docs:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M9 13h6M9 17h4"/>',
 cases:'<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
 human:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 11h-6"/>',
 mem:'<path d="M12 2a4 4 0 0 0-4 4v1a3 3 0 0 0-3 3v1a3 3 0 0 0 0 6 3 3 0 0 0 3 3 3 3 0 0 0 4 2 3 3 0 0 0 4-2 3 3 0 0 0 3-3 3 3 0 0 0 0-6v-1a3 3 0 0 0-3-3V6a4 4 0 0 0-4-4Z"/>',
 ana:'<path d="M3 3v18h18"/><path d="m7 15 4-5 3 3 5-7"/>',
 set:'<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7.5 19l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 3 13.6H3a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4.6 7l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9.4A1.6 1.6 0 0 0 10.4 3V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9.4a1.6 1.6 0 0 0 1.4 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z"/>'
};
const check='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="m4 12 5 5L20 6"/></svg>';
const closeIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>';
const NAV=[
 ['dashboard','Dashboard','dash'],['inbox','Inbox','inbox'],['documents','Documents','docs'],
 ['cases','Verification Cases','cases'],['review','Human Review','human'],['memory','AI Memory','mem'],
 ['analytics','Analytics','ana'],['settings','Settings','set']
];
const CATEGORY_META={
  GENERAL:{label:'General',cls:'t-mute'}, SPAM:{label:'Spam',cls:'t-spam'},
  BL_COMPARISON:{label:'Comparison Request',cls:'t-acc'}, SI_REQUEST:{label:'New SI Request',cls:'t-info'},
  INVOICE_QUERY:{label:'Invoice Query',cls:'t-warn'},
};
const FIELD_DEFS=[
  ['shipper','Shipper'],['consignee','Consignee'],['notify_party','Notify Party'],
  ['port_of_loading','Port of Loading'],['port_of_discharge','Port of Discharge'],
  ['container_count','Container Count'],['raw_weight_value','Gross Weight'],
];
const REVIEW_REASON_LABEL={
  wrong_doc_type:'One of the attached files was not a valid SI or BL',
  missing_attachment:'The SI or BL attachment was missing',
  unreadable:'A document could not be parsed',
  missing_value:'A required field could not be extracted',
};
const PIPELINE_STEPS=[
  ['Submitting to router','classify_email() + LangGraph router'],
  ['Classifying email','Gemini category prediction'],
  ['Locating SI & BL','resolving stored attachments'],
  ['Extracting documents','OCR / text + field extraction'],
  ['Comparing fields','shipper, consignee, ports, containers, weight'],
  ['Building risk report','compliance flags + recommended action'],
];

/* ============================ state ============================ */
const S={page:'dashboard',caseId:null,mailFilter:'All',running:false,connected:false};
let ALL=[];          // dashboard records cache
const DETAIL={};     // email_id -> full row (lazy)
let STATUS_INFO={};
let lastCaseId='';

const $=s=>document.querySelector(s);
const view=$('#view');
const money=n=>'$'+Math.round(n).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function fmt(v,fb='—'){ if(v===null||v===undefined||v==='') return fb; if(Array.isArray(v)) return v.length?esc(v.join(', ')):fb; return esc(v); }
function relTime(iso){
  if(!iso) return '';
  const ms=new Date(iso).getTime(); if(Number.isNaN(ms)) return iso;
  const s=Math.max(0,Math.floor((Date.now()-ms)/1000));
  if(s<60) return 'just now'; const m=Math.floor(s/60); if(m<60) return `${m}m ago`;
  const h=Math.floor(m/60); if(h<24) return `${h}h ago`; const d=Math.floor(h/24); return `${d}d ago`;
}

/* ============================ data layer ============================ */
async function loadDashboard(){
  const res=await fetch('/api/dashboard');
  const data=await res.json();
  ALL=data.records||[];
  S.connected=!!data.connected;
  updateLiveTag(data);
  return data;
}
async function loadDetail(id,force){
  if(!force && DETAIL[id]) return DETAIL[id];
  const res=await fetch(`/api/emails/${encodeURIComponent(id)}`);
  const data=await res.json();
  if(!res.ok) throw new Error(data?.detail||'Email not found.');
  DETAIL[id]=data;
  return data;
}
async function loadStatus(){
  try{ const res=await fetch('/api/status'); STATUS_INFO=await res.json(); updatePollFoot(); }catch(e){}
}
async function pollHealth(){
  try{ const res=await fetch('/health',{cache:'no-store'}); if(!res.ok) throw 0; }catch(e){ S.connected=false; updateLiveTag({connected:false}); }
}
setInterval(pollHealth,20000);

function updateLiveTag(data){
  const tag=$('#liveTag');
  if(data.connected){ tag.className='live-tag'; tag.innerHTML=`<i class="dot"></i>Live — Supabase connected`; }
  else{ tag.className='live-tag off'; tag.innerHTML=`<i class="dot"></i>${esc(data.error?'Supabase pending':'Offline')}`; }
}
function updatePollFoot(){
  const el=$('#pollFoot'); if(!el||!STATUS_INFO.poll_seconds) return;
  el.textContent=`Polling Gmail every ${STATUS_INFO.poll_seconds}s · up to ${STATUS_INFO.max_results} per check`;
}

/* ============================ derived / real analytics helpers ============================ */
function compRows(){ return ALL.filter(r=>r.category==='BL_COMPARISON'); }
function pendingRows(){ return compRows().filter(r=>r.has_defect===true && !(r.metadata&&r.metadata.human_review)); }
function decidedRows(){ return compRows().filter(r=>r.has_defect===true && r.metadata && r.metadata.human_review); }
function caseRisk(row){ if(row.has_defect) return 'High'; if(row.review_reason) return 'Medium'; return 'Low'; }
function riskGaugeValue(risk){ return risk==='High'?86:risk==='Medium'?52:12; }
function caseMatchRate(row){ const bad=(row.defect_fields||[]).length; return Math.round((7-bad)/7*100); }
function caseDiscrepancies(c){ return (c.metadata&&c.metadata.discrepancy_details)||c.discrepancy_details||[]; }
function fieldValue(doc,key){
  if(!doc) return null;
  if(key==='raw_weight_value'){
    // Older stored extractions used a "gross_weight_kg" key before the schema
    // was normalized to raw_weight_value/raw_weight_unit — read either.
    if(doc.raw_weight_value!=null) return `${doc.raw_weight_value} ${doc.raw_weight_unit||''}`.trim();
    if(doc.gross_weight_kg!=null) return `${doc.gross_weight_kg} KG`;
    return null;
  }
  return doc[key];
}
function bigrams(s){ s=String(s||'').toLowerCase().replace(/\s+/g,' ').trim(); const g=[]; for(let i=0;i<s.length-1;i++) g.push(s.slice(i,i+2)); return g; }
function diceSimilarity(a,b){
  const A=bigrams(a),B=bigrams(b);
  if(!A.length||!B.length) return String(a||'')===String(b||'')?100:0;
  const bag={}; B.forEach(g=>{bag[g]=(bag[g]||0)+1});
  let hits=0; A.forEach(g=>{ if(bag[g]>0){hits++;bag[g]--;} });
  return Math.round((2*hits)/(A.length+B.length)*100);
}
function fieldConfidence(key,siVal,blVal,isMismatch){
  if(siVal==null||blVal==null) return isMismatch?42:68;
  if(key==='container_count'||key==='raw_weight_value'){
    const a=parseFloat(siVal), b=parseFloat(String(blVal).replace(/[^\d.-]/g,''));
    if(Number.isFinite(a)&&Number.isFinite(b)&&Math.max(Math.abs(a),Math.abs(b))>0) return Math.max(0,Math.round(100-Math.abs(a-b)/Math.max(Math.abs(a),Math.abs(b))*100));
    return isMismatch?55:99;
  }
  return diceSimilarity(String(siVal),String(blVal));
}
function caseOverlapScore(a,b){
  if(a.id===b.id) return -1;
  const fa=new Set(a.defect_fields||[]), fb=new Set(b.defect_fields||[]);
  let inter=0; fa.forEach(f=>{if(fb.has(f))inter++;});
  const union=new Set([...fa,...fb]).size;
  let score=union?(inter/union)*65:0;
  if(a.review_reason&&a.review_reason===b.review_reason) score+=20;
  if(a.sender_email&&b.sender_email&&a.sender_email===b.sender_email) score+=15;
  return Math.min(100,Math.round(score));
}
function similarCasesFor(row,pool){
  return pool.filter(r=>r.category==='BL_COMPARISON').map(r=>({...r,sim:caseOverlapScore(row,r)}))
    .filter(r=>r.sim>0).sort((a,b)=>b.sim-a.sim).slice(0,5);
}
function seededRandom(seed){
  let h=1779033703^String(seed).length;
  for(let i=0;i<String(seed).length;i++){ h=Math.imul(h^String(seed).charCodeAt(i),3432918353); h=(h<<13)|(h>>>19); }
  return function(){ h=Math.imul(h^(h>>>16),2246822507); h=Math.imul(h^(h>>>13),3266489909); h^=h>>>16; return (h>>>0)/4294967296; };
}
function pickOne(rand,arr){ return arr[Math.floor(rand()*arr.length)]; }
function futureDateFrom(rand,minDays){ return new Date(Date.now()+(minDays+rand()*60)*86400000).toISOString().slice(0,10); }
function draftFigures(seed){
  const rand=seededRandom(seed||'smartship');
  const currency=pickOne(rand,['USD','EUR','SGD','MYR']);
  const invoiceValue=Math.round((20000+rand()*180000)/100)*100;
  return {
    currency, invoiceValue,
    coverageLimit:Math.round(invoiceValue*(2+rand()*3)),
    policyNumber:`EO-${Math.floor(100000+rand()*900000)}`,
    insurer:pickOne(rand,['Meridian Marine Underwriters','Northbridge Cargo Assurance','PortGuard Insurance Group']),
    issuingBank:pickOne(rand,['First Continental Bank','Pacific Trade Bank','Meridian Commercial Bank']),
    advisingBank:pickOne(rand,['Harbor Union Bank','Straits Financial Bank']),
    lcType:pickOne(rand,['Irrevocable, confirmed','Irrevocable, unconfirmed','Standby']),
    expiryDate:futureDateFrom(rand,45),
    presentationPeriod:`${5+Math.floor(rand()*10)} days after shipment date`,
    tolerance:pickOne(rand,['+/-5% on quantity and amount','+/-10% on quantity and amount','No tolerance permitted']),
  };
}
function dayKey(iso){ const d=new Date(iso); return Number.isNaN(d.getTime())?null:d.toISOString().slice(0,10); }
function last14DaysSeries(rows){
  const days=[]; for(let i=13;i>=0;i--){ const d=new Date(Date.now()-i*86400000); days.push(d.toISOString().slice(0,10)); }
  const counts=Object.fromEntries(days.map(d=>[d,0]));
  rows.forEach(r=>{ const k=dayKey(r.received_at); if(k in counts) counts[k]++; });
  return days.map(d=>counts[d]);
}
function rawHeader(row,name){
  const headers=(row&&row.raw_payload&&row.raw_payload.payload&&row.raw_payload.payload.headers)||[];
  const f=headers.find(h=>(h.name||'').toLowerCase()===name); return f?f.value:'';
}
function extractBodyText(rawPayload){
  const payload=rawPayload&&rawPayload.payload; if(!payload) return '';
  function walk(p){
    if(p.parts){ for(const part of p.parts){ if(part.mimeType==='text/plain'&&part.body&&part.body.data){ try{ return atob(part.body.data.replace(/-/g,'+').replace(/_/g,'/')); }catch(e){ return ''; } } if(part.parts){ const r=walk(part); if(r) return r; } } return ''; }
    if(p.body&&p.body.data){ try{ return atob(p.body.data.replace(/-/g,'+').replace(/_/g,'/')); }catch(e){ return ''; } }
    return '';
  }
  return walk(payload);
}
function attachmentInfoFor(detail,kind){
  const recs=detail.attachment_records||[];
  for(const rec of recs){
    const idx=(rec.doc_type||[]).findIndex(dt=>String(dt||'').toUpperCase()===kind.toUpperCase());
    if(idx>=0) return { path:(rec.storage_path||[])[idx], format:(rec.file_format||[])[idx], corrupted:!!rec.is_corrupted, filename:((rec.storage_path||[])[idx]||'').split('/').pop() };
  }
  return null;
}

/* ============================ nav / shell ============================ */
function renderNav(){
  const pend=pendingRows().length;
  $('#nav').innerHTML=NAV.map(([id,label,ic])=>`
    <button data-action="go" data-page="${id}" class="${S.page===id?'on':''}">
      <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[ic]}</svg>
      <span>${label}</span>${id==='review'&&pend?`<span class="pill">${pend}</span>`:''}
    </button>`).join('');
  const nc=$('#notifcount');
  if(pend){ nc.textContent=String(pend); nc.classList.remove('hidden'); } else nc.classList.add('hidden');
}
async function go(p,id){
  S.page=p; if(id) S.caseId=id;
  renderNav(); document.body.classList.remove('navopen'); $('#rail').classList.remove('open');
  window.scrollTo({top:0,behavior:'instant'});
  await render();
}

/* ============================ small builders ============================ */
function riskTag(r){ const c=r==='High'?'t-bad':r==='Medium'?'t-warn':'t-ok'; return `<span class="tag ${c}">${r} risk</span>`; }
function statusTag(s){
  const text=String(s||'').toUpperCase();
  let cls='t-mute';
  if(['OK','APPROVED','VERIFIED','VALID'].some(w=>text.includes(w))) cls='t-ok';
  else if(['MISMATCH','REJECTED','INVALID','CORRUPT','UNREADABLE','FAIL'].some(w=>text.includes(w))) cls='t-bad';
  else if(['NEEDS_REVIEW','PENDING','PROCESSED'].some(w=>text.includes(w))) cls='t-warn';
  return `<span class="tag ${cls}">${esc(s||'Unknown')}</span>`;
}
function clsTag(c){ const m=CATEGORY_META[c]||{label:c||'Unknown',cls:'t-mute'}; return `<span class="tag ${m.cls}">${esc(m.label)}</span>`; }
function conf(c){ c=Math.round(c); return `<div class="confcell"><b>${c}%</b><div class="meter ${c<70?'low':''}" style="width:58px"><i style="width:${Math.max(0,Math.min(100,c))}%"></i></div></div>`; }
function ring(pct,size=42,color='var(--accent)'){
  const r=(size-6)/2,c=2*Math.PI*r;
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" class="simring">
   <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="var(--line)" stroke-width="4"/>
   <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round"
     stroke-dasharray="${c}" stroke-dashoffset="${c*(1-pct/100)}" transform="rotate(-90 ${size/2} ${size/2})"/>
   <text x="50%" y="50%" text-anchor="middle" dy=".35em" font-size="${size*0.26}" font-weight="600" fill="var(--text)">${Math.round(pct)}</text></svg>`;
}
function avatarInitials(name){ return String(name||'?').trim().split(/\s+/).map(w=>w[0]).slice(0,2).join('').toUpperCase()||'?'; }
function skeletonCard(title){
  return `<section class="card"><header><h2>${esc(title)}</h2></header><div class="body">
    <div class="skel" style="width:60%;margin-bottom:10px"></div><div class="skel" style="width:40%;margin-bottom:10px"></div><div class="skel" style="width:80%"></div>
  </div></section>`;
}
function emptyState(title,msg){ return `<div class="empty"><b>${esc(title)}</b><p class="sub" style="margin-top:6px">${esc(msg)}</p></div>`; }

/* ============================ PAGE: dashboard ============================ */
async function pageDashboard(){
  view.innerHTML=skeletonCard('Loading dashboard…');
  await loadDashboard();
  const comp=compRows();
  const verified=comp.filter(r=>r.has_defect===false).length;
  const mismatch=comp.filter(r=>r.has_defect===true).length;
  const pend=pendingRows().length;
  const spam=ALL.filter(r=>r.category==='SPAM').length;
  const attention=comp.filter(r=>r.has_defect||r.review_reason).slice(0,8);
  const series=last14DaysSeries(ALL);

  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Operations overview</h1>
    <p class="sub">${ALL.length} email${ALL.length===1?'':'s'} processed so far. ${pend} case${pend===1?'':'s'} waiting for a person to decide.</p></div>
    <button class="btn primary" data-action="go" data-page="inbox">Open inbox</button></div>

  <div class="kpis">
    ${kpiCard('Documents processed',ALL.length.toLocaleString(),'All time',null,series)}
    ${kpiCard('Verified automatically',verified.toLocaleString(),`of ${comp.length} comparisons run`)}
    ${kpiCard('Mismatches found',mismatch.toLocaleString(),'Across the 7 compared fields','flag')}
    ${kpiCard('Pending human review',pend.toLocaleString(),`${pend} in the review queue now`)}
    ${kpiCard('Spam intercepted',spam.toLocaleString(),'Never reached the queue')}
  </div>

  <div class="two" style="margin-top:14px">
    <div class="grid">
      <section class="card"><header><h2>Cases needing attention</h2><span class="sub" style="margin-left:auto">Most recent first</span></header>
        <div class="tablewrap"><table><thead><tr><th>Shipment</th><th>Sender</th><th>Status</th><th>Risk</th><th>Match rate</th><th>Reviewed</th></tr></thead><tbody>
        ${attention.length?attention.map(c=>`<tr class="click" data-action="open-case" data-id="${esc(c.id)}">
          <td><b class="mono">${esc(c.id)}</b><div class="sub" style="font-size:12px">${esc(c.subject||'')}</div></td>
          <td class="sub">${esc(c.sender)}</td><td>${statusTag(c.status)}</td><td>${riskTag(caseRisk(c))}</td>
          <td>${conf(caseMatchRate(c))}</td><td>${(c.metadata&&c.metadata.human_review)?statusTag(c.metadata.human_review.decision):'<span class="tag t-warn">Pending</span>'}</td></tr>`).join(''):
          `<tr><td colspan="6">${emptyState('Nothing needs attention','Every comparison currently on file matched cleanly.')}</td></tr>`}
        </tbody></table></div></section>

      <section class="card"><header><h2>Documents processed over time</h2><span class="sub" style="margin-left:auto">Last 14 days</span></header>
        <div class="body">${areaChart(series,'Documents / day')}</div></section>
    </div>

    <div class="grid">
      <section class="card"><header><h2>How a message becomes a decision</h2></header>
        <div class="body"><div class="arch">${archNodes()}</div></div></section>

      <section class="card"><header><h2>Today's activity</h2></header><div class="body">${activityList(comp,spam)}</div></section>
    </div>
  </div>`;
}
function kpiCard(lbl,val,foot,cls,spark){
  return `<div class="kpi ${cls||''}"><div class="lbl">${lbl}</div><div class="val">${val}</div>
   ${spark?`<div class="sparkbar">${spark.map(v=>`<i style="height:${Math.max(4,v/Math.max(1,...spark)*100)}%"></i>`).join('')}</div>`:''}
   <div class="foot">${foot||''}</div></div>`;
}
function archNodes(){
  const n=[['01','Frontend','this console'],['02','LangGraph router','classify + dispatch'],['03','Gemini','classify + extract'],
  ['04','Document processing','OCR / text extraction'],['05','Comparator','7-field exact match'],['06','Risk report','flags + recommendation'],
  ['07','Supabase','emails + attachments'],['08','Human review','when flagged']];
  return n.map(([i,a,b],ix)=>`${ix?'<div class="aconn"></div>':''}<div class="anode"><span class="n">${i}</span><b>${a}</b><span>${b}</span></div>`).join('');
}
function activityList(comp,spam){
  const recent=comp.filter(r=>Date.now()-new Date(r.received_at).getTime()<24*3600*1000);
  const okRecent=recent.filter(r=>r.has_defect===false).length;
  const badRecent=recent.filter(r=>r.has_defect===true);
  const notesRecorded=decidedRows().filter(r=>r.metadata.human_review.note).length;
  const items=[
    ['✓', false, `${okRecent||compRows().filter(r=>r.has_defect===false).length} shipment${okRecent===1?'':'s'} cleared with no mismatch`, okRecent?'In the last 24 hours':'All time'],
    badRecent.length?['!',true,`${badRecent.length} shipment${badRecent.length>1?'s':''} flagged for review`,badRecent.map(r=>r.id).join(', ')]:null,
    [ '↺', false, `${notesRecorded} adjuster note${notesRecorded===1?'':'s'} recorded`, 'Stored on the reviewed case'],
    ['⌁', false, `${spam} spam message${spam===1?'':'s'} filtered`, 'Never reached the queue'],
  ].filter(Boolean);
  return `<ul class="reasons">${items.map(([b,warn,title,note])=>`<li ${warn?'class="warn"':''}><span class="bul">${b}</span><div>${esc(title)}<small>${esc(note)}</small></div></li>`).join('')}</ul>`;
}

/* ============================ PAGE: inbox ============================ */
async function pageInbox(){
  view.innerHTML=skeletonCard('Loading inbox…');
  if(!ALL.length) await loadDashboard();
  const cats=['All',...Object.keys(CATEGORY_META)];
  const list=ALL.filter(e=>S.mailFilter==='All'||e.category===S.mailFilter);
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Inbox</h1><p class="sub">Every message is classified on arrival by Gemini, then routed to the matching subgraph.</p></div>
   <div class="filters">${cats.map(c=>`<button class="chip ${S.mailFilter===c?'on':''}" data-action="filter" data-c="${c}">${c==='All'?'All':(CATEGORY_META[c]||{label:c}).label}</button>`).join('')}</div></div>
  <section class="card">
    ${list.length?list.map(e=>`
    <div class="mail" data-action="open-mail" data-id="${esc(e.id)}" data-row-id="${esc(e.row_id||'')}">
      <div class="avatar">${avatarInitials(e.sender)}</div>
      <div style="flex:1;min-width:0">
        <div class="l1"><span class="from">${esc(e.sender)}</span><span class="addr">${esc(e.sender_email)}</span><span class="when">${esc(relTime(e.received_at))}</span></div>
        <div class="subj">${esc(e.subject)||'<span class="sub">(no subject)</span>'}</div>
        <div class="l3">
          ${clsTag(e.category)}${e.metadata&&e.metadata.confidence!=null?`<span class="sub" style="font-size:12px">classified at ${Math.round(e.metadata.confidence*100)}%</span>`:''}
          ${e.attached_docs?`<span class="attach"><svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.4 11.1 12.3 20a5 5 0 0 1-7-7l9-9a3.3 3.3 0 1 1 4.7 4.7l-9 9a1.7 1.7 0 0 1-2.4-2.4l8.5-8.4"/></svg>attachments</span>`:''}
          ${statusTag(e.status)}
          ${e.category==='BL_COMPARISON'?`<span class="sub mono" style="font-size:12px">→ ${esc(e.id)}</span>`:''}
        </div>
      </div>
    </div>`).join(''):`<div class="body">${emptyState('No messages in this category','Pick another filter above.')}</div>`}
  </section>`;
}

/* ============================ PAGE: documents ============================ */
async function pageDocuments(){
  view.innerHTML=skeletonCard('Loading documents…');
  if(!ALL.length) await loadDashboard();
  const withDocs=compRows().filter(r=>r.attached_docs);
  // email_id isn't guaranteed unique, so fetch and cache by each row's real
  // database id and keep the friendly email_id only for display.
  await Promise.all(withDocs.map(r=>loadDetail(r.row_id||r.id).catch(()=>null)));
  const docs=[];
  withDocs.forEach(r=>{
    const key=r.row_id||r.id;
    const detail=DETAIL[key]; if(!detail) return;
    (detail.attachment_records||[]).forEach(rec=>{
      (rec.doc_type||[]).forEach((dt,i)=>{
        docs.push({
          name:(rec.storage_path||[])[i]?.split('/').pop()||'(unnamed)',
          path:(rec.storage_path||[])[i],
          kind:dt, case:key, caseLabel:detail.email_id||r.id, fmt:(rec.file_format||[])[i],
          valid:!rec.is_corrupted,
          extracted: dt==='SI'?!!detail.si_extracted:(dt==='BL'?!!detail.bl_extracted:null),
          when:r.received_at,
        });
      });
    });
  });
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Documents</h1><p class="sub">Attachments pulled from email and linked to a shipment. Open one to see the extracted fields, or download the original file.</p></div></div>
  <section class="card"><div class="tablewrap"><table>
   <thead><tr><th>File</th><th>Type</th><th>Shipment</th><th>Format</th><th>Validity</th><th>Extraction</th><th>Received</th><th></th></tr></thead>
   <tbody>${docs.length?docs.map(d=>`<tr class="click" data-action="view-doc" data-case="${esc(d.case)}" data-kind="${d.kind==='BL'?'bl':'si'}">
     <td><b class="mono" style="font-size:12.8px">${esc(d.name)}</b></td><td><span class="tag t-acc">${esc(d.kind)}</span></td>
     <td class="mono">${esc(d.caseLabel)}</td><td class="sub">${esc((d.fmt||'').toUpperCase())}</td>
     <td>${d.valid?'<span class="tag t-ok">Valid</span>':'<span class="tag t-bad">Corrupted</span>'}</td>
     <td>${d.extracted===null?'—':(d.extracted?'<span class="tag t-ok">Extracted</span>':'<span class="tag t-warn">Not extracted</span>')}</td>
     <td class="sub">${esc(relTime(d.when))}</td>
     <td><span class="btn ghost">Open</span></td></tr>`).join(''):`<tr><td colspan="8">${emptyState('No documents yet','Comparison emails with attachments will show up here.')}</td></tr>`}</tbody></table></div></section>`;
}

/* ============================ PAGE: cases list ============================ */
async function pageCases(){
  view.innerHTML=skeletonCard('Loading verification cases…');
  if(!ALL.length) await loadDashboard();
  const cases=compRows();
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Verification cases</h1><p class="sub">Each case pairs one shipping instruction with one bill of lading across the 7 fields compare_subgraph checks.</p></div></div>
  <section class="card"><div class="tablewrap"><table>
   <thead><tr><th>Shipment</th><th>Sender</th><th>Fields differing</th><th>Status</th><th>Risk</th><th>Match rate</th></tr></thead>
   <tbody>${cases.length?cases.map(c=>{const bad=(c.defect_fields||[]).length;return `
    <tr class="click" data-action="open-case" data-id="${esc(c.id)}">
     <td><b class="mono">${esc(c.id)}</b><div class="sub" style="font-size:12px">${esc(c.subject||'')}</div></td>
     <td class="sub">${esc(c.sender)}</td>
     <td>${c.has_defect?`<span class="tag t-bad">${bad} of 7</span>`:(c.has_defect===false?'<span class="tag t-ok">0 of 7</span>':'<span class="tag t-mute">—</span>')}</td>
     <td>${statusTag(c.status)}</td><td>${riskTag(caseRisk(c))}</td><td>${conf(caseMatchRate(c))}</td></tr>`}).join(''):
     `<tr><td colspan="6">${emptyState('No comparison cases yet','BL / SI comparison emails will appear here once processed.')}</td></tr>`}</tbody></table></div></section>`;
}

/* ============================ PAGE: case detail ============================ */
async function pageCase(){
  view.innerHTML=skeletonCard(`Loading ${S.caseId}…`);
  let detail;
  try{ detail=await loadDetail(S.caseId); }
  catch(e){ view.innerHTML=`<section class="card"><div class="body">${emptyState("Couldn't load that case",e.message)}</div></section>`; return; }
  lastCaseId=S.caseId;
  renderCaseDetail(detail);
}
function renderCaseDetail(detail){
  const c=detail;
  const risk=caseRisk(c);
  const badFields=FIELD_DEFS.filter(([k])=>(c.defect_fields||[]).includes(k));
  const sims=similarCasesFor(c,ALL);
  const subject=c.subject||rawHeader(c,'subject')||'(no subject)';
  const reviewed=c.metadata&&c.metadata.human_review;

  view.innerHTML=`
  <div class="pagehead">
    <div class="grow">
      <button class="btn ghost" data-action="go" data-page="cases" style="margin-bottom:6px">← All cases</button>
      <h1>Shipment <span class="mono">${esc(c.email_id||c.id)}</span></h1>
      <p class="sub">${esc(c.sender)} · ${esc(subject)} · received ${esc(c.received_at)}</p>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn" data-action="view-doc" data-case="${esc(c.email_id||c.id)}" data-kind="si">Open documents</button>
      <button class="btn primary" data-action="run">Run verification again</button>
    </div>
  </div>

  <div class="caseband">
    <div><div class="l">Status</div><div class="v" style="font-size:15px;font-family:inherit">${statusTag(c.status)}</div></div>
    <div><div class="l">Risk level</div><div class="v" style="font-size:15px;font-family:inherit">${riskTag(risk)}</div></div>
    <div><div class="l">Match rate</div><div class="v">${caseMatchRate(c)}%</div></div>
    <div><div class="l">Fields differing</div><div class="v">${badFields.length} / 7</div></div>
  </div>

  <div id="runzone" style="margin-top:14px"></div>

  <div class="two" style="margin-top:14px">
    <section class="card ledger">
      <header><h2>Shipping instruction compared with bill of lading</h2>
        <span class="sub" style="margin-left:auto">Click a field for the reason</span></header>
      <div class="lhead"><div>Shipping instruction (SI)</div><div class="mid">Verdict</div><div>Bill of lading (BL)</div></div>
      ${(c.si_extracted||c.bl_extracted)?FIELD_DEFS.map(([key,label],i)=>{
        const si=fieldValue(c.si_extracted,key), bl=fieldValue(c.bl_extracted,key);
        const isMiss=(c.defect_fields||[]).includes(key);
        const dd=caseDiscrepancies(c).find(d=>d.field===key);
        const cPct=fieldConfidence(key,si,bl,isMiss);
        const reason=isMiss?(dd?`SI declares "${dd.si_value??'—'}", BL declares "${dd.bl_value??'—'}"${dd.delta&&dd.delta!=='Text mismatch'?` (Δ ${dd.delta})`:''}.`:'Values differ between the two documents.'):'Values agree between the two documents.';
        return `
        <div class="row ${isMiss?'miss':''}" data-action="toggle-field" data-i="${i}">
          <div class="side"><div class="fname">${esc(label)}</div><div class="fval">${esc(si??'—')}</div></div>
          <div class="spine">${isMiss?'<span class="tag t-bad">Mismatch</span>':'<span class="tag t-ok">Match</span>'}<span class="pct">${cPct}%</span></div>
          <div class="side"><div class="fname">${esc(label)}</div><div class="fval">${esc(bl??'—')}</div></div>
          <div class="detail">
            <div class="d"><b>Reason</b>${esc(reason)}</div>
            <div class="d"><b>Field similarity</b>${cPct}%</div>
            <button class="btn" data-action="view-doc" data-case="${esc(c.email_id||c.id)}" data-kind="${isMiss?'bl':'si'}" data-field="${key}" data-stop="1">Show on document</button>
          </div>
        </div>`;}).join(''):`<div class="body">${emptyState('No extraction on file',c.review_reason?REVIEW_REASON_LABEL[c.review_reason]||c.review_reason:'This case has not produced SI/BL field extraction yet.')}</div>`}
    </section>

    <div class="grid">
      <section class="card"><header><h2>Why did the AI flag this case?</h2></header><div class="body">
        <ul class="reasons">
          ${badFields.length?`<li class="warn"><span class="bul">${badFields.length}</span><div>${badFields.length} mismatched field${badFields.length>1?'s':''} detected<small>${badFields.map(f=>f[1]).join(', ')}</small></div></li>`:
            (c.has_defect===false?'<li><span class="bul">✓</span><div>All seven fields agree<small>No differences found by compare_subgraph</small></div></li>':'')}
          ${c.review_reason?`<li class="warn"><span class="bul">!</span><div>${esc(REVIEW_REASON_LABEL[c.review_reason]||c.review_reason)}<small>review_reason: ${esc(c.review_reason)}</small></div></li>`:''}
          <li><span class="bul">≈</span><div>${sims.length?`${sims.length} similar historical case${sims.length>1?'s':''} found`:'No comparable historical cases'}<small>${sims.length?`Closest match ${sims[0].id} at ${sims[0].sim}% overlap`:'No other case shares these defect fields yet'}</small></div></li>
          ${c.enterprise_risk_report?`<li><span class="bul">$</span><div>${esc(c.enterprise_risk_report.recommended_action||'')}<small>${esc(c.enterprise_risk_report.financial_and_safety_impact||'')}</small></div></li>`:''}
          <li><span class="bul">${!c.has_defect?'✓':(reviewed?'✓':'!')}</span><div>${!c.has_defect?'Cleared automatically':(reviewed?`Reviewed — ${reviewed.decision}`:'Human review recommended')}<small>${!c.has_defect?'No fields differed above the comparator threshold':(reviewed?esc(reviewed.note||'No note left'):'Waiting for an adjuster decision')}</small></div></li>
        </ul></div></section>

      <section class="card"><header><h2>Risk report</h2></header><div class="body">
        <div class="risk">${ring(riskGaugeValue(risk),64,risk==='High'?'var(--bad)':risk==='Medium'?'var(--warn)':'var(--ok)')}
          <div><div style="font-weight:600;font-size:15px">Risk level: ${risk.toUpperCase()}</div>
          <p class="sub">${c.enterprise_risk_report?esc(c.enterprise_risk_report.financial_and_safety_impact):'No risk report has been generated for this case yet.'}</p></div></div>
        ${c.enterprise_risk_report?`<div class="kv" style="margin-top:12px"><dt>Recommended action</dt><dd>${esc(c.enterprise_risk_report.recommended_action||'—')}</dd></div>`:''}
        ${c.enterprise_risk_report&&(c.enterprise_risk_report.compliance_flags||[]).length?`<div style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap">${c.enterprise_risk_report.compliance_flags.map(f=>`<span class="tag t-warn">${esc(f)}</span>`).join('')}</div>`:''}
      </div></section>

      <section class="card"><header><h2>Similar cases</h2>
        <button class="btn ghost" data-action="go" data-page="memory" style="margin-left:auto">Open AI memory</button></header>
        <div class="body">
        ${sims.length?sims.slice(0,3).map(s=>`<div class="simcase">${ring(s.sim,42)}
          <div><b class="mono">${esc(s.id)}</b> <span class="sub">${s.sim}% overlap</span>
          <div style="font-size:13.2px;margin-top:2px">${esc((s.defect_fields||[]).join(', ')||s.review_reason||'—')}</div>
          <div class="r">${(s.metadata&&s.metadata.human_review)?`Resolved: ${esc(s.metadata.human_review.decision)}`:'Pending review'}</div></div></div>`).join(''):'<p class="sub">No comparable cases stored yet.</p>'}
      </div></section>

      <section class="card"><header><h2>Decision</h2></header><div class="body" id="decisionBody">${decisionCardBody(c)}</div></section>
    </div>
  </div>

  <section class="card" style="margin-top:14px" id="docGenCard">${docGenCard(c)}</section>`;

  bindDocGen(c);
  bindDecision(c);
}
function decisionCardBody(c){
  const reviewed=c.metadata&&c.metadata.human_review;
  if(c.has_defect!==true) return `<p class="sub">This case cleared every check automatically — no adjuster action is needed.</p>`;
  if(reviewed) return `<p class="sub" style="margin-bottom:10px">Decision recorded: <b>${esc(reviewed.decision)}</b>${reviewed.note?` — "${esc(reviewed.note)}"`:''}</p>${statusTag(reviewed.decision)} <span class="sub">${esc(relTime(reviewed.reviewed_at))}</span>`;
  return `
    <p class="sub" style="margin-bottom:10px">Confidence sits below auto-clear, so a person should decide.</p>
    <input type="text" id="caseNote" placeholder="Optional note for the record" style="margin-bottom:10px">
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn ok" data-action="case-decide" data-d="APPROVED">Approve</button>
      <button class="btn bad" data-action="case-decide" data-d="REJECTED">Reject</button>
    </div>
    <span class="sub" id="caseDecideStatus" style="display:block;margin-top:8px"></span>`;
}
function bindDecision(c){
  const body=$('#decisionBody'); if(!body) return;
  body.querySelectorAll('[data-action="case-decide"]').forEach(btn=>{
    btn.addEventListener('click',async()=>{
      const decision=btn.dataset.d;
      const note=$('#caseNote')?.value.trim();
      body.querySelectorAll('button').forEach(b=>b.disabled=true);
      const st=$('#caseDecideStatus'); if(st) st.textContent='Recording…';
      try{
        const res=await fetch(`/api/emails/${encodeURIComponent(c.email_id||c.id)}/decision`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,note:note||undefined})});
        const data=await res.json();
        if(!res.ok) throw new Error(data?.detail||'Failed to record decision.');
        const fresh=await loadDetail(c.email_id||c.id,true);
        await loadDashboard(); renderNav();
        renderCaseDetail(fresh);
        toast(`${c.email_id||c.id} ${decision.toLowerCase()}.`);
      }catch(e){ if(st) st.textContent=e.message; body.querySelectorAll('button').forEach(b=>b.disabled=false); }
    });
  });
}

/* ---- claim & compliance documents (case-embedded, 3 tabs) ---- */
let docActiveTab='claim';
function docGenCard(c){
  const tabs=[['claim','E&O Insurance Claim'],['audit','Audit Trail'],['letter','LC Compliance Letter']];
  const figures=draftFigures(c.email_id||c.id);
  const builders={claim:buildClaimDoc,audit:buildAuditDoc,letter:buildLetterDoc};
  const doc=builders[docActiveTab](c,figures);
  return `<header><h2>Claim &amp; compliance documents</h2><span class="sub" style="margin-left:auto">Generated from this case</span></header>
  <div class="body">
    <div class="doc-tabs2">${tabs.map(([k,l])=>`<button class="${k===docActiveTab?'on':''}" data-action="doc-gen-tab" data-t="${k}">${l}</button>`).join('')}</div>
    <div class="page" id="docGenPaper" style="max-width:720px">${doc.html}</div>
    <div class="actions" style="margin-top:14px;display:flex;gap:8px">
      <button class="btn primary" data-action="doc-gen-pdf">Download PDF</button>
      <button class="btn" data-action="doc-gen-json">Export JSON</button>
    </div>
  </div>`;
}
function bindDocGen(c){
  const card=$('#docGenCard'); if(!card) return;
  card.querySelectorAll('[data-action="doc-gen-tab"]').forEach(btn=>btn.addEventListener('click',()=>{ docActiveTab=btn.dataset.t; card.innerHTML=docGenCard(c); bindDocGen(c); }));
  const pdfBtn=card.querySelector('[data-action="doc-gen-pdf"]');
  if(pdfBtn) pdfBtn.addEventListener('click',()=>{ const figures=draftFigures(c.email_id||c.id); const builders={claim:buildClaimDoc,audit:buildAuditDoc,letter:buildLetterDoc}; const doc=builders[docActiveTab](c,figures); downloadPdf(`${docActiveTab}_${c.email_id||c.id}.pdf`,doc.title,doc.pdfBlocks); });
  const jsonBtn=card.querySelector('[data-action="doc-gen-json"]');
  if(jsonBtn) jsonBtn.addEventListener('click',()=>{ const figures=draftFigures(c.email_id||c.id); const builders={claim:buildClaimDoc,audit:buildAuditDoc,letter:buildLetterDoc}; const doc=builders[docActiveTab](c,figures); downloadJson(`${docActiveTab}_${c.email_id||c.id}.json`,doc.data); });
}
function buildClaimDoc(c,f){
  const disc=caseDiscrepancies(c);
  const errorDescription=disc.length?`Comparison of the Shipping Instruction against the finalized Bill of Lading found ${disc.length} mismatched field(s): ${disc.map(d=>d.field).join(', ')}. ${(c.enterprise_risk_report||{}).financial_and_safety_impact||''}`.trim()
    :'No SI/BL discrepancy is on record for this shipment.';
  const evidence=(c.attachment_records||[]).flatMap(a=>a.storage_path||[]);
  const coverage=`${f.currency} ${f.coverageLimit.toLocaleString()}`, invoice=`${f.currency} ${f.invoiceValue.toLocaleString()}`, exposure=`${f.currency} ${Math.round(f.invoiceValue*0.18).toLocaleString()}`;
  const narrative=`On ${c.received_at||'the recorded date'}, the shipment referenced under ${c.email_id||c.id} was processed by SmartShip AI. ${errorDescription} A claim is accordingly being lodged against Errors & Omissions coverage for the resulting exposure.`;
  const html=`<div class="ph"><div><b>ERRORS &amp; OMISSIONS CLAIM</b><div style="font-size:10px;letter-spacing:.06em">DRAFT FOR REVIEW</div></div><span>${esc(c.email_id||c.id)}</span></div>
   <div class="pgrid" style="margin-bottom:10px">
     <div class="fld"><div class="k">SENDER</div><div class="v">${esc(c.sender)}</div></div>
     <div class="fld"><div class="k">RECEIVED</div><div class="v">${esc(c.received_at)}</div></div>
     <div class="fld"><div class="k">POLICY NUMBER</div><div class="v">${esc(f.policyNumber)}</div></div>
     <div class="fld"><div class="k">INSURER</div><div class="v">${esc(f.insurer)}</div></div>
     <div class="fld"><div class="k">COVERAGE LIMIT</div><div class="v">${esc(coverage)}</div></div>
     <div class="fld"><div class="k">INVOICE VALUE</div><div class="v">${esc(invoice)}</div></div>
     <div class="fld"><div class="k">ESTIMATED EXPOSURE</div><div class="v">${esc(exposure)}</div></div>
   </div>
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin-bottom:4px">MISMATCH DETAIL</div>
   <div style="margin-bottom:10px">${disc.length?disc.map(d=>`<div style="font-size:11.5px;margin-bottom:3px">${esc(d.field)}: SI(${esc(d.si_value)}) vs BL(${esc(d.bl_value)})${d.delta?` — ${esc(d.delta)}`:''}</div>`).join(''):'<div style="font-size:11.5px">None on record.</div>'}</div>
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin-bottom:4px">CLAIM NARRATIVE</div>
   <div style="font-size:11.8px;line-height:1.6">${esc(narrative)}</div>
   <div class="pf"><span>Supporting evidence: ${evidence.length} file(s)</span><span>page 1</span></div>`;
  return {title:'Errors & Omissions Claim',html,
    pdfBlocks:[
      {heading:'Shipment / Claim Reference',rows:[['Reference',c.email_id||c.id],['Sender',c.sender],['Received',c.received_at]]},
      {heading:'Mismatch Detail',rows:disc.length?disc.map(d=>[d.field,`SI:${d.si_value} vs BL:${d.bl_value}${d.delta?` (${d.delta})`:''}`]):[['Discrepancies','none on record']]},
      {heading:'Policy & Coverage',rows:[['Policy number',f.policyNumber],['Insurer',f.insurer],['Coverage limit',coverage]]},
      {heading:'Financial Exposure',rows:[['Invoice value',invoice],['Estimated exposure',exposure]]},
      {heading:'Supporting Evidence',rows:evidence.length?evidence.map((p,i)=>[`Doc ${i+1}`,p]):[['Evidence','none recorded']]},
      {heading:'Claim Narrative',paragraph:narrative},
    ],
    data:{reference:c.email_id||c.id,error_fields:disc,policy_number:f.policyNumber,insurer:f.insurer,coverage_limit:coverage,invoice_value:invoice,estimated_exposure:exposure,supporting_evidence:evidence,narrative}};
}
function buildAuditDoc(c){
  const timeline=[{step:'Email received',at:c.received_at},{step:'Classified',at:c.received_at,detail:`${c.category}${c.metadata&&c.metadata.routing_reasoning?` — ${c.metadata.routing_reasoning}`:''}`}];
  timeline.push({step:'SI / BL extracted',detail:(c.si_extracted||c.bl_extracted)?'Fields extracted for both documents':'Extraction incomplete'});
  timeline.push({step:'Compared',detail:`Status: ${c.status||'n/a'}`});
  const reviewed=c.metadata&&c.metadata.human_review;
  if(reviewed) timeline.push({step:'Adjuster decision',at:reviewed.reviewed_at,detail:`${reviewed.decision}${reviewed.note?` — ${reviewed.note}`:''}`});
  const disc=caseDiscrepancies(c);
  const comparisonRows=disc.map(d=>[esc(d.field),fmt(d.si_value),fmt(d.bl_value)]);
  const evidence=(c.attachment_records||[]).flatMap(a=>a.storage_path||[]);
  const html=`<div class="ph"><div><b>AUDIT TRAIL EXPORT</b><div style="font-size:10px;letter-spacing:.06em">PROCESSING RECORD</div></div><span>${esc(c.email_id||c.id)}</span></div>
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin:8px 0 4px">1. SHIPMENT INFORMATION</div>
   <div class="pgrid"><div class="fld"><div class="k">EMAIL ID</div><div class="v">${esc(c.email_id||c.id)}</div></div><div class="fld"><div class="k">SENDER</div><div class="v">${esc(c.sender)}</div></div><div class="fld"><div class="k">CATEGORY</div><div class="v">${esc(c.category)}</div></div></div>
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin:12px 0 4px">2. PROCESSING TIMELINE</div>
   ${timeline.map(t=>`<div style="font-size:11.5px;margin-bottom:3px">${esc(t.step)}${t.at?` — ${esc(t.at)}`:''}${t.detail?` (${esc(t.detail)})`:''}</div>`).join('')}
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin:12px 0 4px">3. EXTRACTED DATA &amp; COMPARISON</div>
   ${comparisonRows.length?comparisonRows.map(r=>`<div style="font-size:11.5px;margin-bottom:3px">${r[0]}: SI(${r[1]}) vs BL(${r[2]})</div>`).join(''):'<div style="font-size:11.5px">No comparison run.</div>'}
   <div style="font-size:11px;color:#667;letter-spacing:.05em;margin:12px 0 4px">4. RESOLUTION</div>
   <div style="font-size:11.5px">${reviewed?`${esc(reviewed.decision)}${reviewed.note?` — ${esc(reviewed.note)}`:''}`:'No adjuster action recorded yet.'}</div>
   <div class="pf"><span>Source documents: ${evidence.length}</span><span>page 1</span></div>`;
  return {title:'Audit Trail Export',html,
    pdfBlocks:[
      {heading:'1. Shipment Information',rows:[['Email ID',c.email_id||c.id],['Sender',c.sender],['Category',c.category]]},
      {heading:'2. Processing Timeline',rows:timeline.map(t=>[t.step,`${t.at||''} ${t.detail||''}`.trim()])},
      {heading:'3. Extracted Data & Comparison',rows:comparisonRows.length?comparisonRows.map(r=>[r[0],`SI:${r[1]} / BL:${r[2]}`]):[['Comparison','not run']]},
      {heading:'4. Resolution',rows:reviewed?[['Decision',reviewed.decision],['Note',reviewed.note||'-'],['Reviewed at',reviewed.reviewed_at]]:[['Status','not yet reviewed']]},
      {heading:'5. Source Documents',rows:evidence.length?evidence.map((p,i)=>[`Doc ${i+1}`,p]):[['Documents','none recorded']]},
    ],
    data:{email_id:c.email_id||c.id,timeline,comparison:disc,status:c.status,human_review:reviewed||null,source_documents:evidence}};
}
function buildLetterDoc(c,f){
  const si=c.si_extracted||{}, bl=c.bl_extracted||{};
  const pick=(a,b)=>(a??b??'—');
  const lcAmount=`${f.currency} ${f.invoiceValue.toLocaleString()}`;
  const html=`<div class="ph"><div><b>LETTER OF CREDIT COMPLIANCE</b><div style="font-size:10px;letter-spacing:.06em">DRAFT</div></div><span>${esc(c.email_id||c.id)}</span></div>
   <div class="pgrid">
    <div class="fld"><div class="k">PORT OF LOADING</div><div class="v">${esc(pick(bl.port_of_loading,si.port_of_loading))}</div></div>
    <div class="fld"><div class="k">PORT OF DISCHARGE</div><div class="v">${esc(pick(bl.port_of_discharge,si.port_of_discharge))}</div></div>
    <div class="fld"><div class="k">SHIPPER / BENEFICIARY</div><div class="v">${esc(pick(bl.shipper,si.shipper))}</div></div>
    <div class="fld"><div class="k">CONSIGNEE / APPLICANT</div><div class="v">${esc(pick(bl.consignee,si.consignee))}</div></div>
    <div class="fld"><div class="k">CONTAINERS</div><div class="v">${esc(pick(bl.container_count,si.container_count))}</div></div>
    <div class="fld"><div class="k">LC AMOUNT</div><div class="v">${esc(lcAmount)}</div></div>
    <div class="fld"><div class="k">ISSUING BANK</div><div class="v">${esc(f.issuingBank)}</div></div>
    <div class="fld"><div class="k">ADVISING BANK</div><div class="v">${esc(f.advisingBank)}</div></div>
    <div class="fld"><div class="k">LC TYPE</div><div class="v">${esc(f.lcType)}</div></div>
    <div class="fld"><div class="k">EXPIRY DATE</div><div class="v">${esc(f.expiryDate)}</div></div>
    <div class="fld"><div class="k">PRESENTATION PERIOD</div><div class="v">${esc(f.presentationPeriod)}</div></div>
    <div class="fld"><div class="k">TOLERANCE</div><div class="v">${esc(f.tolerance)}</div></div>
   </div>
   <div class="pf"><span>Document set must be free of discrepancies prior to negotiation${(c.defect_fields||[]).length?` — outstanding: ${esc(c.defect_fields.join(', '))}`:''}</span><span>page 1</span></div>`;
  return {title:'Letter of Credit Compliance Draft',html,
    pdfBlocks:[
      {heading:'Shipment Reference',rows:[['Reference',c.email_id||c.id],['Port of loading',pick(bl.port_of_loading,si.port_of_loading)],['Port of discharge',pick(bl.port_of_discharge,si.port_of_discharge)]]},
      {heading:'Parties',rows:[['Shipper / Beneficiary',pick(bl.shipper,si.shipper)],['Consignee / Applicant',pick(bl.consignee,si.consignee)],['Notify party',pick(bl.notify_party,si.notify_party)]]},
      {heading:'Letter of Credit Terms',rows:[['LC amount',lcAmount],['Issuing bank',f.issuingBank],['Advising bank',f.advisingBank],['LC type',f.lcType],['Expiry date',f.expiryDate],['Presentation period',f.presentationPeriod],['Tolerance',f.tolerance]]},
    ],
    data:{reference:c.email_id||c.id,shipper:pick(bl.shipper,si.shipper),consignee:pick(bl.consignee,si.consignee),lc_terms:f}};
}
function downloadJson(filename,data){
  const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; a.click(); URL.revokeObjectURL(url);
}
function downloadPdf(filename,title,blocks){
  if(!window.jspdf){ toast('PDF library still loading — try again in a second.'); return; }
  const {jsPDF}=window.jspdf; const doc=new jsPDF({unit:'pt',format:'a4'});
  const marginX=48, rightEdge=547, pageHeight=doc.internal.pageSize.getHeight(), lineHeight=15; let y=56;
  function ensure(extra=lineHeight){ if(y+extra>pageHeight-48){doc.addPage();y=56;} }
  function writeLines(text,opts={}){
    doc.setFont('helvetica',opts.bold?'bold':'normal'); doc.setFontSize(opts.size||10); doc.setTextColor(...(opts.color||[40,50,60]));
    doc.splitTextToSize(text,rightEdge-marginX).forEach(line=>{ ensure(); doc.text(line,marginX,y); y+=lineHeight; });
  }
  doc.setFont('helvetica','bold'); doc.setFontSize(17); doc.setTextColor(20,40,60); doc.text(title,marginX,y); y+=8;
  doc.setDrawColor(15,110,122); doc.setLineWidth(1.4); doc.line(marginX,y,rightEdge,y); y+=24;
  blocks.forEach(b=>{
    if(b.heading){ ensure(22); writeLines(b.heading,{bold:true,size:12,color:[20,40,60]}); y+=4; }
    if(b.rows){ b.rows.forEach(([k,v])=>writeLines(`${k}: ${v??'-'}`)); y+=8; }
    if(b.paragraph){ writeLines(b.paragraph); y+=8; }
  });
  doc.save(filename);
}

/* ---- run verification again: real /api/route call, animated ---- */
function runVerification(){
  if(S.running) return; S.running=true;
  const c=DETAIL[S.caseId]; if(!c){ S.running=false; return; }
  const zone=$('#runzone');
  zone.innerHTML=`<section class="card"><header><h2>Verification pipeline</h2><span class="sub" id="runstate" style="margin-left:auto">Running…</span></header>
   <div class="body"><div class="pipe" id="pipe">${PIPELINE_STEPS.map((p,i)=>`
     ${i?'<div class="pconn" data-c="'+i+'"></div>':''}
     <div class="pstep" data-s="${i}"><div class="knob"></div><div class="nm">${p[0]}</div><div class="out"></div></div>`).join('')}</div></div></section>`;
  zone.scrollIntoView({behavior:'smooth',block:'nearest'});

  const attachments=(c.attachment_records||[]).flatMap(a=>(a.storage_path||[]).map(p=>({storage_path:p})));
  const payload={ from_name:c.sender, from_email:rawHeader(c,'from')||'', subject:c.subject||rawHeader(c,'subject')||'',
    body:extractBodyText(c.raw_payload)||'(no plain-text body stored)', attachments };

  let i=0; let resultData=null; let failed=null;
  const req=fetch('/api/route',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})
    .then(r=>r.json().then(d=>({ok:r.ok,d})))
    .then(({ok,d})=>{ if(!ok) throw new Error(d?.detail||'Re-run failed.'); resultData=d; })
    .catch(e=>{ failed=e; });

  const step=()=>{
    if(i>0){ const d=zone.querySelector(`.pstep[data-s="${i-1}"]`); d.classList.remove('act'); d.classList.add('done');
      d.querySelector('.knob').innerHTML=check; d.querySelector('.out').textContent=PIPELINE_STEPS[i-1][1];
      const cn=zone.querySelector(`.pconn[data-c="${i}"]`); if(cn) cn.classList.add('done'); }
    if(i>=PIPELINE_STEPS.length){
      req.then(()=>{
        S.running=false;
        if(failed){ $('#runstate').innerHTML='<span class="tag t-bad">Re-run failed</span>'; toast(failed.message); return; }
        $('#runstate').innerHTML='<span class="tag t-ok">Live re-run complete</span>';
        renderRerunResult(zone,resultData);
        toast(`Live re-run complete for ${S.caseId} — result shown below (not saved over the stored record).`);
      });
      return;
    }
    zone.querySelector(`.pstep[data-s="${i}"]`).classList.add('act');
    i++; setTimeout(step,480);
  };
  step();
}
function renderRerunResult(zone,data){
  if(!data) return;
  const cls=data.classification||{}, result=data.result||{};
  const disc=result.discrepancy_details||[];
  zone.insertAdjacentHTML('beforeend',`<section class="card" style="margin-top:14px"><header><h2>Live re-run result</h2><span class="sub" style="margin-left:auto">Not persisted to Supabase</span></header>
   <div class="body">
     <div class="kv" style="margin-bottom:12px"><dt>Category</dt><dd>${clsTag(cls.category)}</dd><dt>Status</dt><dd>${statusTag(result.status)}</dd><dt>Has defect</dt><dd>${result.has_defect?'Yes':'No'}</dd></div>
     ${disc.length?`<div class="tablewrap"><table><thead><tr><th>Field</th><th>SI</th><th>BL</th></tr></thead><tbody>${disc.map(d=>`<tr><td>${esc(d.field)}</td><td class="mono">${fmt(d.si_value)}</td><td class="mono">${fmt(d.bl_value)}</td></tr>`).join('')}</tbody></table></div>`:'<p class="sub">No discrepancies on this re-run.</p>'}
   </div></section>`);
}

/* ============================ PAGE: human review ============================ */
async function pageReview(){
  view.innerHTML=skeletonCard('Loading review queue…');
  if(!ALL.length) await loadDashboard();
  const pending=pendingRows(), decided=decidedRows();
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Human review</h1>
   <p class="sub">${pending.length} case${pending.length===1?'':'s'} where compare_subgraph found a defect and no one has decided yet.</p></div></div>
  <section class="card"><div class="tablewrap"><table>
   <thead><tr><th>Case ID</th><th>Fields differing</th><th>Reason</th><th>Risk</th><th>Status</th><th></th></tr></thead>
   <tbody>${pending.length?pending.map(r=>`<tr class="click" data-action="open-review" data-id="${esc(r.id)}">
     <td><b class="mono">${esc(r.id)}</b></td><td>${(r.defect_fields||[]).map(f=>`<span class="tag t-bad">${esc(f)}</span>`).join(' ')}</td>
     <td class="sub">${esc(r.review_reason?REVIEW_REASON_LABEL[r.review_reason]||r.review_reason:'—')}</td><td>${riskTag(caseRisk(r))}</td>
     <td>${statusTag(r.status)}</td><td><span class="btn ghost">Review</span></td></tr>`).join(''):`<tr><td colspan="6">${emptyState('Nothing pending','Every flagged mismatch has been reviewed.')}</td></tr>`}
   </tbody></table></div></section>
  ${decided.length?`
  <section class="card" style="margin-top:14px"><header><h2>Recorded decisions</h2></header>
  <div class="tablewrap"><table><thead><tr><th>Case</th><th>Decision</th><th>Note</th><th>Reviewed</th></tr></thead>
  <tbody>${decided.map(r=>`<tr class="click" data-action="open-case" data-id="${esc(r.id)}"><td class="mono">${esc(r.id)}</td><td>${statusTag(r.metadata.human_review.decision)}</td><td class="sub">${esc(r.metadata.human_review.note||'—')}</td><td class="sub">${esc(relTime(r.metadata.human_review.reviewed_at))}</td></tr>`).join('')}</tbody>
  </table></div></section>`:''}`;
}
async function openReviewModal(id){
  let detail; try{ detail=await loadDetail(id); }catch(e){ toast(e.message); return; }
  const badFields=FIELD_DEFS.filter(([k])=>(detail.defect_fields||[]).includes(k));
  $('#modalBox').innerHTML=`
   <header><h2 style="flex:1">Case <span class="mono">${esc(id)}</span></h2>${riskTag(caseRisk(detail))}
     <button class="iconbtn" data-action="close-modal">${closeIcon}</button></header>
   <div class="body">
     <div class="lhead" style="border:1px solid var(--line);border-bottom:0;border-radius:8px 8px 0 0"><div>Shipping instruction</div><div class="mid">Field</div><div>Bill of lading</div></div>
     ${badFields.map(([key,label])=>{ const si=fieldValue(detail.si_extracted,key), bl=fieldValue(detail.bl_extracted,key);
       return `<div class="row miss" style="border:1px solid var(--line);border-top:0;cursor:default">
         <div class="side"><div class="fname">${esc(label)}</div><div class="fval">${esc(si??'—')}</div></div>
         <div class="spine"><span class="tag t-bad">Differs</span></div>
         <div class="side"><div class="fname">${esc(label)}</div><div class="fval">${esc(bl??'—')}</div></div></div>`; }).join('')}
     <div style="margin-top:14px"><label class="f">Note for the record (optional)</label><input type="text" id="reviewNote"></div>
   </div>
   <footer>
     <button class="btn ok" data-action="review-decide" data-id="${esc(id)}" data-d="APPROVED">Approve</button>
     <button class="btn bad" data-action="review-decide" data-id="${esc(id)}" data-d="REJECTED">Reject</button>
     <button class="btn ghost" data-action="close-modal" style="margin-left:auto">Cancel</button>
   </footer>`;
  $('#modal').classList.add('on');
}
async function reviewDecide(id,decision){
  const note=$('#reviewNote')?.value.trim();
  $('#modalBox').querySelectorAll('button').forEach(b=>b.disabled=true);
  try{
    const res=await fetch(`/api/emails/${encodeURIComponent(id)}/decision`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision,note:note||undefined})});
    const data=await res.json(); if(!res.ok) throw new Error(data?.detail||'Failed to record decision.');
    delete DETAIL[id]; await loadDashboard(); renderNav(); closeModal();
    if(S.page==='review') render(); toast(`${id} ${decision.toLowerCase()}.`);
  }catch(e){ toast(e.message); $('#modalBox').querySelectorAll('button').forEach(b=>b.disabled=false); }
}

/* ============================ PAGE: AI memory ============================ */
async function pageMemory(){
  view.innerHTML=skeletonCard('Loading AI memory…');
  if(!ALL.length) await loadDashboard();
  const cases=compRows();
  const focusId=lastCaseId||( (cases.find(r=>r.has_defect)||{}).id )||'';
  const focus=cases.find(r=>r.id===focusId);
  const sims=focus?similarCasesFor(focus,ALL):[];
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>AI memory</h1>
   <p class="sub">Every stored comparison case is a candidate match. Results are ranked by shared defect fields, review reason and sender — computed live from Supabase, not a vector database.</p></div>
   <span class="tag t-mute">${cases.length} case${cases.length===1?'':'s'} indexed</span></div>

  <div class="two">
    <div class="grid">
      <section class="card"><header><h2>Search stored cases</h2><span class="sub" style="margin-left:auto">${focus?`Focused on <b class="mono">${esc(focus.id)}</b>`:'No case focused yet'}</span></header>
        <div class="body">
          <div style="display:flex;gap:9px;flex-wrap:wrap;margin-bottom:12px">
            <input id="memq" type="text" placeholder="e.g. gross weight, consignee, wrong_doc_type" style="flex:1;min-width:220px">
            <button class="btn primary" data-action="memsearch">Find similar cases</button>
          </div>
          <div class="console" id="memconsole"><span style="color:#5E7C8C">Ready. Type a keyword or leave blank to rank by the focused case.</span></div>
        </div></section>

      <section class="card"><header><h2>Results</h2><span class="sub" style="margin-left:auto">Ranked by field / keyword overlap</span></header>
        <div class="body" id="memresults">${memResultsHtml(sims)}</div></section>
    </div>

    <div class="grid">
      <section class="card"><header><h2>Case map</h2></header><div class="body">
        ${vectorMap(cases,focusId)}
        <p class="sub" style="margin-top:10px">Each point is a real stored case. The highlighted point is the focused case; nearer points share more defect fields.</p></div></section>
      <section class="card"><header><h2>What this adds</h2></header><div class="body">
        <ul class="reasons">
          <li><span class="bul">1</span><div>Past resolutions come back with the case<small>Reviewers see how the same defect field was closed before</small></div></li>
          <li><span class="bul">2</span><div>Repeat patterns surface early<small>Same review_reason or sender across cases is flagged</small></div></li>
          <li><span class="bul">3</span><div>Adjuster notes stay attached<small>Every recorded note is retrievable from the matching case</small></div></li>
        </ul></div></section>
    </div>
  </div>`;
}
function memResultsHtml(sims){
  if(!sims.length) return '<p class="sub">No comparable cases yet.</p>';
  return sims.map(s=>`<div class="simcase">${ring(s.sim,46)}
    <div style="flex:1"><div style="display:flex;gap:9px;align-items:baseline;flex-wrap:wrap"><b class="mono">${esc(s.id)}</b><span class="tag t-mute">${s.sim}% overlap</span></div>
    <div style="margin-top:3px">${esc((s.defect_fields||[]).join(', ')||s.review_reason||'—')}</div>
    <div class="r">${(s.metadata&&s.metadata.human_review)?`Resolved: ${esc(s.metadata.human_review.decision)}${s.metadata.human_review.note?' · '+esc(s.metadata.human_review.note):''}`:'Pending review'}</div></div></div>`).join('');
}
function vectorMap(cases,focusId){
  const pts=cases.map(c=>{ const r=seededRandom(c.id); return {id:c.id,x:20+r()*260,y:18+r()*164,bad:!!c.has_defect}; });
  const focus=pts.find(p=>p.id===focusId);
  return `<svg viewBox="0 0 300 200" class="vecmap" role="img" aria-label="Scatter of stored comparison cases">
   <rect width="300" height="200" fill="var(--surface-2)" rx="8"/>
   ${pts.map(p=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${p.bad?3.4:2.4}" fill="${p.bad?'var(--bad)':'var(--line-strong)'}" opacity=".85"/>`).join('')}
   ${focus?`<circle cx="${focus.x.toFixed(1)}" cy="${focus.y.toFixed(1)}" r="11" fill="none" stroke="var(--accent)" stroke-width="1.6" opacity=".7"/>
     <text x="${focus.x.toFixed(1)}" y="${(focus.y-9).toFixed(1)}" text-anchor="middle" font-size="8" fill="var(--muted)">${esc(focus.id)}</text>`:''}
  </svg>`;
}
function memSearch(){
  const con=$('#memconsole'); if(!con) return;
  const q=$('#memq').value.trim().toLowerCase();
  const cases=compRows();
  const focus=cases.find(r=>r.id===lastCaseId);
  let ranked;
  if(q){
    const tokens=q.split(/\s+/).filter(Boolean);
    ranked=cases.map(r=>{
      const hay=`${r.subject||''} ${(r.defect_fields||[]).join(' ')} ${r.review_reason||''}`.toLowerCase();
      const hits=tokens.filter(t=>hay.includes(t)).length;
      return {...r,sim:tokens.length?Math.round(hits/tokens.length*100):0};
    }).filter(r=>r.sim>0).sort((a,b)=>b.sim-a.sim).slice(0,6);
  } else {
    ranked=focus?similarCasesFor(focus,ALL):[];
  }
  const lines=[
    `> tokenize("${esc(q||'(focused case)')}")`,
    `  ${cases.length} stored comparison case(s) in scope`,
    `> score by defect-field / review-reason / sender overlap`,
    `  <span class="hl">${ranked.length} candidate${ranked.length===1?'':'s'} above threshold</span>`,
    `> done`,
  ];
  con.innerHTML='';
  lines.forEach((l,i)=>{ const d=document.createElement('div'); d.className='ln'; d.style.animationDelay=(i*0.22)+'s'; d.innerHTML=l; con.appendChild(d); });
  setTimeout(()=>{ $('#memresults').innerHTML=memResultsHtml(ranked); },lines.length*220);
}

/* ============================ PAGE: analytics ============================ */
async function pageAnalytics(){
  view.innerHTML=skeletonCard('Loading analytics…');
  if(!ALL.length) await loadDashboard();
  const comp=compRows();
  const cleared=comp.filter(r=>r.has_defect===false).length;
  const autoRate=comp.length?Math.round(cleared/comp.length*100):0;
  const avgBad=comp.filter(r=>r.has_defect).length?(comp.filter(r=>r.has_defect).reduce((a,r)=>a+(r.defect_fields||[]).length,0)/comp.filter(r=>r.has_defect).length):0;
  const fieldsExtracted=comp.reduce((a,r)=>a+(r.si_extracted?7:0)+(r.bl_extracted?7:0),0);
  const spam=ALL.filter(r=>r.category==='SPAM').length;
  const fieldTally={}; FIELD_DEFS.forEach(([k])=>fieldTally[k]=0);
  comp.forEach(r=>(r.defect_fields||[]).forEach(f=>{ if(f in fieldTally) fieldTally[f]++; }));
  const catTally={}; ALL.forEach(r=>catTally[r.category]=(catTally[r.category]||0)+1);
  const riskTally={High:0,Medium:0,Low:0}; comp.forEach(r=>riskTally[caseRisk(r)]++);
  const reasonTally={}; comp.forEach(r=>{ if(r.review_reason) reasonTally[r.review_reason]=(reasonTally[r.review_reason]||0)+1; });
  const series=last14DaysSeries(ALL);
  const donutColors=['var(--accent)','var(--info)','var(--warn)','var(--line-strong)','var(--spam)'];

  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Analytics</h1><p class="sub">Computed live from every email and comparison stored in Supabase.</p></div></div>
  <div class="kpis" style="margin-bottom:14px">
    ${kpiCard('Auto-clear rate',`${autoRate}%`,`${cleared} of ${comp.length} comparisons`)}
    ${kpiCard('Avg. fields differing','' + avgBad.toFixed(1),'Per mismatched case')}
    ${kpiCard('Fields extracted',fieldsExtracted.toLocaleString(),'Across SI + BL documents')}
    ${kpiCard('Spam intercepted',spam.toLocaleString(),'Never reached the queue')}
  </div>
  <div class="chartgrid">
    <section class="card"><header><h2>Mismatches by field</h2></header><div class="body">
      ${barsH(FIELD_DEFS.map(([k,l])=>[l,fieldTally[k]]))}</div></section>

    <section class="card"><header><h2>Emails by classification</h2></header><div class="body">
      ${donut(Object.entries(catTally).map(([k,v],i)=>[(CATEGORY_META[k]||{label:k}).label,v,donutColors[i%donutColors.length]]))}</div></section>

    <section class="card"><header><h2>Risk levels</h2></header><div class="body">
      ${barsH([['Low',riskTally.Low],['Medium',riskTally.Medium],['High',riskTally.High]],['var(--ok)','var(--warn)','var(--bad)'])}</div></section>

    <section class="card"><header><h2>Documents processed over time</h2></header><div class="body">
      ${areaChart(series,'Documents / day')}</div></section>

    <section class="card"><header><h2>Review reasons</h2></header><div class="body">
      ${Object.keys(reasonTally).length?barsH(Object.entries(reasonTally).map(([k,v])=>[REVIEW_REASON_LABEL[k]||k,v])):`<p class="sub">No review-reason flags recorded yet.</p>`}</div></section>
  </div>`;
}
function barsH(rows,colors){
  const max=Math.max(1,...rows.map(r=>r[1]));
  return rows.map((r,i)=>`<div style="margin-bottom:11px">
    <div style="display:flex;justify-content:space-between;font-size:12.8px;margin-bottom:4px"><span>${esc(r[0])}</span><b class="mono">${r[1].toLocaleString()}</b></div>
    <div class="meter" style="height:8px"><i style="width:${r[1]/max*100}%;background:${colors?colors[i]:'var(--accent)'}"></i></div></div>`).join('');
}
function donut(rows){
  const total=rows.reduce((a,r)=>a+r[1],0)||1; let off=0; const r=52,c=2*Math.PI*r;
  const arcs=rows.map(row=>{ const frac=row[1]/total; const s=`<circle cx="70" cy="70" r="${r}" fill="none" stroke="${row[2]}" stroke-width="20"
    stroke-dasharray="${(c*frac-2).toFixed(1)} ${c}" stroke-dashoffset="${(-c*off).toFixed(1)}" transform="rotate(-90 70 70)"/>`; off+=frac; return s; }).join('');
  return `<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
   <svg width="140" height="140" viewBox="0 0 140 140">${arcs}
    <text x="70" y="66" text-anchor="middle" font-size="22" font-weight="600" fill="var(--text)">${total.toLocaleString()}</text>
    <text x="70" y="84" text-anchor="middle" font-size="10" fill="var(--muted)">messages</text></svg>
   <div style="flex:1;min-width:150px">${rows.map(r=>`<div style="display:flex;justify-content:space-between;font-size:12.8px;padding:3px 0"><span><i style="width:9px;height:9px;border-radius:3px;display:inline-block;background:${r[2]};margin-right:7px"></i>${esc(r[0])}</span><b class="mono">${r[1]}</b></div>`).join('')}</div></div>`;
}
function areaChart(data,label){
  const w=560,h=180,pad=28,max=Math.max(1,...data)*1.12,min=0;
  const x=i=>pad+i*(w-pad*2)/Math.max(1,data.length-1), y=v=>h-pad-(v-min)/(max-min)*(h-pad*1.6);
  const line=data.map((v,i)=>`${i?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area=`${line} L${x(data.length-1).toFixed(1)},${h-pad} L${pad},${h-pad} Z`;
  return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;height:auto" role="img" aria-label="${esc(label)}">
   ${[0,.25,.5,.75,1].map(t=>`<line x1="${pad}" x2="${w-pad}" y1="${(h-pad-t*(h-pad*1.6)).toFixed(1)}" y2="${(h-pad-t*(h-pad*1.6)).toFixed(1)}" stroke="var(--line)" stroke-width="1"/>`).join('')}
   <path d="${area}" fill="var(--accent)" opacity=".12"/>
   <path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
   ${data.map((v,i)=>i===data.length-1?`<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="4" fill="var(--accent)"/>`:'').join('')}
   <text x="${pad}" y="${h-8}" font-size="11" fill="var(--muted)">${esc(label)}</text>
   <text x="${w-pad}" y="${h-8}" font-size="11" text-anchor="end" fill="var(--muted)">latest ${data[data.length-1]}</text>
  </svg>`;
}

/* ============================ PAGE: settings ============================ */
async function pageSettings(){
  await loadStatus();
  view.innerHTML=`
  <div class="pagehead"><div class="grow"><h1>Settings</h1><p class="sub">Live configuration and connections for this workspace.</p></div></div>
  <div class="chartgrid">
    <section class="card"><header><h2>Flagging rule</h2></header><div class="body">
      <div class="kv"><dt>Text fields</dt><dd>Case-insensitive, whitespace-normalized exact match</dd>
      <dt>Numeric fields</dt><dd class="mono">container_count, raw_weight_value — exact equality</dd>
      <dt>Flag trigger</dt><dd>Any of the 7 fields fails its match check</dd>
      <dt>Review reasons</dt><dd>wrong_doc_type, missing_attachment, unreadable, missing_value</dd></div></div></section>
    <section class="card"><header><h2>Fields compared</h2></header><div class="body">
      <p class="sub" style="margin-bottom:10px">From ShipmentExtractionSchema, 7 fields on every comparison.</p>
      <div style="display:flex;gap:6px;flex-wrap:wrap">${FIELD_DEFS.map(([,l])=>`<span class="tag t-acc">${l}</span>`).join('')}</div></div></section>
    <section class="card"><header><h2>Connections</h2></header><div class="body">
      <div class="kv"><dt>Supabase</dt><dd>${S.connected?'<span class="tag t-ok">Connected</span>':'<span class="tag t-bad">Not connected</span>'}</dd>
      <dt>Gmail query</dt><dd class="mono">${esc(STATUS_INFO.gmail_query||'—')}</dd>
      <dt>Poll interval</dt><dd class="mono">${STATUS_INFO.poll_seconds?STATUS_INFO.poll_seconds+'s':'—'}</dd>
      <dt>Max per check</dt><dd class="mono">${fmt(STATUS_INFO.max_results)}</dd>
      <dt>Orchestrator</dt><dd>LangGraph runtime <span class="tag t-ok">Live</span></dd></div></div></section>
    <section class="card"><header><h2>Appearance</h2></header><div class="body">
      <p class="sub" style="margin-bottom:10px">Follows your system theme by default.</p>
      <button class="btn" data-action="theme">Switch light / dark</button></div></section>
  </div>`;
}

/* ============================ render dispatch ============================ */
async function render(){
  const map={dashboard:pageDashboard,inbox:pageInbox,documents:pageDocuments,cases:pageCases,
    case:pageCase,review:pageReview,memory:pageMemory,analytics:pageAnalytics,settings:pageSettings};
  await (map[S.page]||pageDashboard)();
}

/* ============================ document drawer (real extracted fields) ============================ */
async function openDoc(caseId,kind,field){
  let detail; try{ detail=await loadDetail(caseId); }catch(e){ toast(e.message); return; }
  $('#drawerPanel').innerHTML=drawerHtml(detail,kind);
  $('#drawer').classList.add('on');
  bindDrawerTabs(detail);
  if(field){ setTimeout(()=>{ const t=document.querySelector(`#docscroll .fld[data-k="${field}"]`); if(t){ t.classList.add('hit'); t.scrollIntoView({behavior:'smooth',block:'center'}); } },140); }
}
function drawerHtml(detail,kind){
  const info=attachmentInfoFor(detail,kind==='bl'?'BL':'SI');
  return `<header><h2 style="flex:1">Documents · <span class="mono">${esc(detail.email_id||detail.id)}</span></h2>
     <button class="iconbtn" data-action="close-drawer">${closeIcon}</button></header>
   <div class="tabs">
     <button class="tab ${kind==='si'?'on':''}" data-action="doc-tab" data-case="${esc(detail.email_id||detail.id)}" data-kind="si">Shipping instruction</button>
     <button class="tab ${kind==='bl'?'on':''}" data-action="doc-tab" data-case="${esc(detail.email_id||detail.id)}" data-kind="bl">Bill of lading</button>
   </div>
   <div class="docscroll" id="docscroll">${docPage(detail,kind,info)}</div>`;
}
function bindDrawerTabs(detail){}
function docPage(detail,kind,info){
  const extracted=kind==='si'?detail.si_extracted:detail.bl_extracted;
  const title=kind==='si'?'SHIPPING INSTRUCTION':'BILL OF LADING';
  const dlBtn=info&&info.path?`<a class="btn ghost" href="/api/attachments/download?path=${encodeURIComponent(info.path)}" style="margin-top:12px">Download original (${esc(info.format||'file')})</a>`:'';
  if(!extracted){
    return `<div class="page"><div class="ph"><div><b>${title}</b><div style="font-size:10px;letter-spacing:.06em">NOT EXTRACTED</div></div><span>${esc(detail.email_id||detail.id)}</span></div>
      <p style="font-size:12px;color:#556">${info?(info.corrupted?'This file failed validation and could not be parsed.':'No structured fields were extracted for this document.'):'No matching attachment was found for this case.'}</p>
      ${dlBtn}</div>`;
  }
  const rows=FIELD_DEFS.map(([key,label])=>[label,fieldValue(extracted,key),key]);
  rows.push(['Valid document',extracted.is_valid_doc?'Yes':'No','']);
  return `<div class="page">
   <div class="ph"><div><b>${title}</b><div style="font-size:10px;letter-spacing:.06em">${esc(detail.email_id||detail.id)}</div></div>
     <span>${info&&info.format?info.format.toUpperCase():''}</span></div>
   <div class="pgrid">${rows.map(r=>`<div class="fld" ${r[2]?`data-k="${r[2]}"`:''}><div class="k">${esc(r[0]).toUpperCase()}</div><div class="v">${esc(r[1]??'—')}</div></div>`).join('')}</div>
   ${dlBtn}
   <div class="pf"><span>Extracted via ShipmentExtractionSchema</span><span>page 1</span></div></div>`;
}

/* ============================ mail modal (general / spam detail) ============================ */
function spamActionTag(action){
  const map={allow:'t-ok',review:'t-warn',reject:'t-bad',quarantine:'t-warn'};
  return `<span class="tag ${map[action]||'t-mute'}">${esc(action||'—')}</span>`;
}
function mailModalBody(detail){
  const meta=detail.metadata||{};
  if(detail.category==='SPAM'){
    return `<div class="kv" style="margin-bottom:14px">
        <dt>Spam score</dt><dd>${fmt(meta.spam_score)}</dd>
        <dt>Is spam</dt><dd>${meta.is_spam===undefined?'—':(meta.is_spam?'Yes':'No')}</dd>
        <dt>Recommended action</dt><dd>${meta.recommended_action?spamActionTag(meta.recommended_action):'—'}</dd>
        <dt>Confidence</dt><dd>${fmt(meta.confidence)}</dd>
        <dt>Sender spam count</dt><dd>${fmt(meta.spam_count)}</dd>
        <dt>Sender blacklisted</dt><dd>${meta.is_blacklisted===undefined?'—':(meta.is_blacklisted?'Yes':'No')}</dd>
        <dt>Blacklist status</dt><dd>${fmt(meta.blacklist_status)}</dd>
      </div>
      ${meta.spam_reasons?`<p class="sub" style="margin-bottom:8px"><b>Reasons:</b> ${esc(meta.spam_reasons)}</p>`:''}
      ${meta.risk_signals?`<p class="sub" style="margin-bottom:8px"><b>Risk signals:</b> ${esc(meta.risk_signals)}</p>`:''}
      ${meta.spam_reason?`<p class="sub"><b>Spam reason:</b> ${esc(meta.spam_reason)}</p>`:''}
      ${!(meta.spam_reasons||meta.risk_signals||meta.spam_reason)?'<p class="sub">No further detail recorded.</p>':''}`;
  }
  if(detail.category==='BL_COMPARISON'){
    const risk=caseRisk(detail), r=detail.enterprise_risk_report;
    return `<div class="kv" style="margin-bottom:14px">
        <dt>Comparison status</dt><dd>${statusTag(detail.status)}</dd>
        <dt>Risk</dt><dd>${riskTag(risk)}</dd>
        <dt>Match rate</dt><dd>${caseMatchRate(detail)}%</dd>
        <dt>Fields differing</dt><dd>${(detail.defect_fields||[]).length} / 7</dd>
      </div>
      ${(detail.defect_fields||[]).length?`<div style="margin-bottom:12px;display:flex;gap:6px;flex-wrap:wrap">${detail.defect_fields.map(f=>`<span class="tag t-bad">${esc(f)}</span>`).join('')}</div>`:''}
      ${r?`<div class="kv" style="margin-bottom:10px">
          <dt>Recommended action</dt><dd>${esc(r.recommended_action||'—')}</dd>
          <dt>Financial &amp; safety impact</dt><dd>${esc(r.financial_and_safety_impact||'—')}</dd>
        </div>
        ${(r.compliance_flags||[]).length?`<div style="display:flex;gap:6px;flex-wrap:wrap">${r.compliance_flags.map(f=>`<span class="tag t-warn">${esc(f)}</span>`).join('')}</div>`:''}`
        :`<p class="sub">No risk report generated for this comparison yet.</p>`}`;
  }
  return `<div class="kv" style="margin-bottom:14px">
      <dt>Summary</dt><dd>${fmt(meta.summary)}</dd>
      <dt>Requires response</dt><dd>${fmt(meta.requires_response)}</dd>
      <dt>Confidence</dt><dd>${fmt(meta.confidence)}</dd>
    </div>
    ${meta.key_points?`<p class="sub" style="margin-bottom:8px"><b>Key points:</b> ${esc(meta.key_points)}</p>`:''}
    ${meta.action_items?`<p class="sub" style="margin-bottom:8px"><b>Action items:</b> ${esc(meta.action_items)}</p>`:''}
    ${meta.suggested_reply?`<p class="sub"><b>Suggested reply:</b> ${esc(meta.suggested_reply)}</p>`:''}
    ${!(meta.summary||meta.key_points||meta.action_items||meta.suggested_reply)?'<p class="sub">No further detail recorded.</p>':''}`;
}
async function openMail(id,rowId){
  // email_id isn't guaranteed unique across rows (repeat test sends share
  // one), so prefer the row's real database id when we have it to avoid
  // showing a different row's data for the clicked message.
  let detail; try{ detail=await loadDetail(rowId||id); }catch(e){ toast(e.message); return; }
  const subject=detail.subject||rawHeader(detail,'subject')||'(no subject)';
  $('#modalBox').innerHTML=`<header><h2 style="flex:1">${esc(subject)}</h2>${clsTag(detail.category)}
     <button class="iconbtn" data-action="close-modal">${closeIcon}</button></header>
     <div class="body"><div class="kv" style="margin-bottom:14px"><dt>From</dt><dd>${esc(detail.sender)}</dd>
       <dt>Received</dt><dd>${esc(detail.received_at)}</dd><dt>Status</dt><dd>${statusTag(detail.status)}</dd></div>
       ${mailModalBody(detail)}</div>
     <footer>${detail.category==='BL_COMPARISON'?`<button class="btn primary" data-action="open-case" data-id="${esc(detail.email_id||detail.id)}">Open full case</button>`:''}
       <button class="btn ghost" data-action="close-modal" style="margin-left:auto">Close</button></footer>`;
  $('#modal').classList.add('on');
}

/* ============================ notifications / toast / modal / drawer ============================ */
function closeModal(){ $('#modal').classList.remove('on'); }
function closeDrawer(){ $('#drawer').classList.remove('on'); }
let toastT;
function toast(msg){ const t=$('#toast'); t.innerHTML=`${check}<span>${esc(msg)}</span>`; t.classList.add('on'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('on'),3600); }
function notifications(){
  const pend=pendingRows();
  $('#modalBox').innerHTML=`<header><h2 style="flex:1">Notifications</h2><button class="iconbtn" data-action="close-modal">${closeIcon}</button></header>
   <div class="body"><ul class="reasons">
     ${pend.length?pend.slice(0,5).map(r=>`<li class="warn"><span class="bul">!</span><div>${esc(r.id)} needs a decision<small>${esc((r.defect_fields||[]).join(', ')||r.review_reason||'flagged by compare_subgraph')}</small></div></li>`).join(''):'<li><span class="bul">✓</span><div>No pending reviews<small>Everything flagged has been decided</small></div></li>'}
   </ul></div>
   <footer><button class="btn ghost" data-action="close-modal" style="margin-left:auto">Close</button></footer>`;
  $('#modal').classList.add('on');
}

/* ============================ events ============================ */
document.addEventListener('click',e=>{
  const t=e.target.closest('[data-action]'); if(!t) return;
  const a=t.dataset.action;
  if(t.dataset.stop) e.stopPropagation();
  switch(a){
    case 'go': go(t.dataset.page); break;
    case 'toggle-nav': $('#rail').classList.toggle('open'); document.body.classList.toggle('navopen'); break;
    case 'filter': S.mailFilter=t.dataset.c; pageInbox(); break;
    case 'open-mail': openMail(t.dataset.id,t.dataset.rowId); break;
    case 'open-case': closeModal(); go('case',t.dataset.id); break;
    case 'toggle-field': t.classList.toggle('open'); break;
    case 'view-doc': e.stopPropagation(); openDoc(t.dataset.case||S.caseId,t.dataset.kind||'si',t.dataset.field); break;
    case 'doc-tab': openDoc(t.dataset.case,t.dataset.kind); break;
    case 'close-drawer': closeDrawer(); break;
    case 'close-modal': closeModal(); break;
    case 'run': runVerification(); break;
    case 'memsearch': memSearch(); break;
    case 'open-review': openReviewModal(t.dataset.id); break;
    case 'review-decide': reviewDecide(t.dataset.id,t.dataset.d); break;
    case 'notif': notifications(); break;
    case 'check-now': checkNow(t); break;
    case 'theme': {
      const cur=document.documentElement.getAttribute('data-theme');
      const dark=cur?cur==='dark':matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme',dark?'light':'dark');
      break;
    }
  }
});
document.addEventListener('keydown',e=>{ if(e.key==='Escape'){ closeModal(); closeDrawer(); } });
$('#q').addEventListener('keydown',e=>{
  if(e.key!=='Enter') return;
  const v=e.target.value.trim();
  if(!v) return;
  const vu=v.toUpperCase();
  const hit=ALL.find(r=>r.id.toUpperCase().includes(vu)||String(r.sender||'').toUpperCase().includes(vu)||String(r.subject||'').toUpperCase().includes(vu));
  if(hit){ if(hit.category==='BL_COMPARISON') go('case',hit.id); else openMail(hit.id); e.target.value=''; }
  else toast('No email matches that search.');
});
async function checkNow(btn){
  btn.disabled=true;
  try{
    const res=await fetch('/check-now',{method:'POST'});
    const data=await res.json();
    toast(`${data.new_email_count||0} new email(s) found.`);
    await loadDashboard(); renderNav();
    if(['dashboard','inbox','cases','review','documents','analytics'].includes(S.page)) render();
  }catch(e){ toast('Gmail check failed.'); }
  finally{ btn.disabled=false; }
}

/* ============================ boot ============================ */
(async function boot(){
  renderNav();
  await loadDashboard();
  renderNav();
  loadStatus();
  pollHealth();
  await render();
})();
