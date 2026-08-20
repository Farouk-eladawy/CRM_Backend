# GYG Edit Extractor — run via browser CDP after navigating to option URL
# Correct regex escaping for CallMcpTool JSON: use single backslash before [ in the
# expression string so JS receives \[ 

EXTRACT_JS = r'''
(async () => {
  function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
  function parseEuro(v){const m=String(v).match(/([\d.,]+)/); return m?Math.round(parseFloat(m[1].replace(',',''))*100):0;}
  function catScale(name){
    // pricingCategories[0].pricingScales[1].prices.retailPrice
    const a=name.indexOf('pricingCategories[');
    if(a<0) return null;
    const cStart=a+'pricingCategories['.length;
    const cEnd=name.indexOf(']',cStart);
    const sKey='].pricingScales[';
    const sPos=name.indexOf(sKey,cEnd);
    if(sPos<0) return null;
    const sStart=sPos+sKey.length;
    const sEnd=name.indexOf(']',sStart);
    return {cat:+name.slice(cStart,cEnd), scale:+name.slice(sStart,sEnd)};
  }
  for(let i=0;i<40;i++){
    const t=document.body?.innerText||'';
    if(t.includes('Product Id:')||/Log in to|Enter code/i.test(t)) break;
    await sleep(400);
  }
  document.querySelectorAll('iframe').forEach(f=>{if(f.getBoundingClientRect().width>280)f.style.display='none';});
  if(/Log in to|Enter code/i.test(document.body.innerText||'')) return {needLogin:true,url:location.href};
  const tour=(location.href.match(/tour_id=(\d+)/)||[])[1];
  const option=(location.href.match(/optionId=(\d+)/)||[])[1];
  const title=(document.querySelector('h1')?.innerText||'').trim();

  const avail=[...document.querySelectorAll('button')].find(b=>/^Availability & Pricing$/i.test((b.innerText||'').trim()));
  if(avail){avail.click(); await sleep(1000);}
  const show=[...document.querySelectorAll('button')].find(b=>/^Show schedule$/i.test((b.innerText||'').trim())&&b.offsetParent);
  let edit=null;
  if(show){
    let p=show.parentElement;
    for(let i=0;i<10&&p;i++){
      const eds=[...p.querySelectorAll('button')].filter(b=>/^Edit$/i.test((b.innerText||'').trim())&&b.offsetParent);
      if(eds.length){edit=eds[eds.length-1]; break;}
      p=p.parentElement;
    }
  }
  if(!edit){
    const eds=[...document.querySelectorAll('button')].filter(b=>/^Edit$/i.test((b.innerText||'').trim())&&b.offsetParent);
    edit=eds[eds.length-1];
  }
  if(!edit) return {error:'no edit',tour,option,url:location.href};
  edit.click(); await sleep(1800);

  const out={name:'',departure_times:[],departure_weekdays:[],participants_min:1,participants_max:100,retail_prices:{},pricing_tiers:[],addons:[],validity:'',price_model:'per_category'};
  for(let s=0;s<10;s++){
    await sleep(400);
    const body=document.body.innerText||'';
    const priceInputs=[...document.querySelectorAll('input')].filter(i=>(i.name||'').includes('pricingCategories')&&(i.name||'').includes('retailPrice'));

    if(s===0){
      const nameInput=document.querySelector('input[placeholder*="Summer"], input[placeholder*="Weekends"]');
      if(nameInput&&nameInput.value) out.name=nameInput.value;
      else { const m=body.match(/Schedule name[\s\S]{0,60}?\n([^\n]+)/i); if(m) out.name=m[1].trim(); }
      for(const day of ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']){
        const m=body.match(new RegExp(day+'\\s*[\\s\\S]{0,150}?(\\d{1,2})\\s*:\\s*(\\d{2})','i'));
        if(m){ out.departure_weekdays.push(day.toLowerCase()); out.departure_times.push(String(m[1]).padStart(2,'0')+':'+m[2]+':00'); }
      }
      out.departure_times=[...new Set(out.departure_times)].sort();
    }

    if(priceInputs.length){
      const section=body.match(/Set the price[\s\S]{0,4000}/)?.[0]||body;
      let catOrder=[...section.matchAll(/\n(Infant|Child|Adult|Senior|Participant)\n/g)].map(m=>m[1].toUpperCase());
      if(!catOrder.length) catOrder=[...new Set([...section.matchAll(/\b(Infant|Child|Adult|Senior|Participant)\b/g)].map(m=>m[1].toUpperCase()))];
      if(catOrder.includes('PARTICIPANT')){ catOrder=catOrder.map(c=>c==='PARTICIPANT'?'ADULT':c); out.price_model='per_participant'; }
      const byCat={};
      for(const inp of priceInputs){
        const cs=catScale(inp.name); if(!cs) continue;
        const cat=catOrder[cs.cat]||('CAT'+cs.cat);
        if(!byCat[cat]) byCat[cat]=[];
        byCat[cat][cs.scale]=parseEuro(inp.value);
      }
      const keys=Object.keys(byCat);
      if(keys.length && keys.every(k=>k.startsWith('CAT'))){
        if(keys.length===1){ byCat.ADULT=byCat[keys[0]]; delete byCat[keys[0]]; out.price_model='per_participant'; }
        else {
          const map=['INFANT','CHILD','ADULT','SENIOR'];
          for(const k of [...keys]){ const i=+k.replace('CAT',''); if(map[i]){ byCat[map[i]]=byCat[k]; delete byCat[k]; } }
        }
      }
      const tierCount=Math.max(0,...Object.values(byCat).map(a=>a.filter(x=>x!==undefined).length));
      let labels=Array.from({length:tierCount},(_,i)=>'tier'+(i+1));
      if(tierCount===1) labels=['all'];
      else if(tierCount===5) labels=['1','2','3','4','5+'];
      else if(tierCount===3) labels=['1','2','3+'];
      else if(tierCount===4) labels=['1','2','3','4+'];
      const rangeLabels=[...section.matchAll(/(\d+)\s*to\s*(\d+|\+)/gi)].map(m=>m[1]+(m[2]==='+'?'+':'-'+m[2]));
      if(rangeLabels.length===tierCount) labels=rangeLabels;
      for(let ti=0;ti<tierCount;ti++){
        const rp={}; for(const [c,arr] of Object.entries(byCat)) if(arr[ti]!==undefined) rp[c]=arr[ti];
        out.pricing_tiers.push({participants:labels[ti], retail_prices:rp});
      }
      if(out.pricing_tiers[0]) out.retail_prices={...out.pricing_tiers[0].retail_prices};
      break;
    }

    if(/How many participants/i.test(body)){
      const nums=[...document.querySelectorAll('input[type=text],input:not([type])')].filter(i=>i.offsetParent&&/^\d+$/.test((i.value||'').trim())).map(i=>+i.value);
      if(nums.length>=2){out.participants_min=Math.min(...nums); out.participants_max=Math.max(...nums);}
    }
    const btn=[...document.querySelectorAll('button')].find(b=>/^Save and continue$/i.test((b.innerText||'').trim())&&!b.disabled&&b.offsetParent);
    if(!btn) break;
    btn.click(); await sleep(1300);
  }

  for(let i=0;i<10;i++){
    const back=[...document.querySelectorAll('button')].find(b=>/^Back$/i.test((b.innerText||'').trim())&&b.offsetParent);
    if(!back) break; back.click(); await sleep(400);
  }
  const avail2=[...document.querySelectorAll('button')].find(b=>/^Availability & Pricing$/i.test((b.innerText||'').trim()));
  if(avail2){avail2.click(); await sleep(800);}
  const list=document.body.innerText||'';
  const val=list.match(/Date range:\s*\n?\s*([^\n]+)/i); if(val) out.validity=val[1].trim();
  const part=list.match(/Participants:\s*\n?\s*(\d+)\s*-\s*(\d+)/i); if(part){out.participants_min=+part[1]; out.participants_max=+part[2];}
  let cutoff_hours=0;
  const cutBtn=[...document.querySelectorAll('button')].find(b=>/^Cut-off time$/i.test((b.innerText||'').trim()));
  if(cutBtn){cutBtn.click(); await sleep(700);}
  const cm=(document.body.innerText||'').match(/Cut-off time:\s*\n?\s*(\d+)\s*hours?/i); if(cm) cutoff_hours=+cm[1];
  return {needLogin:false, ok:!!(out.pricing_tiers.length&&out.departure_times.length), gyg_tour_id:tour, option_id:option, product_title:title, cutoff_hours, schedule:out};
})()
'''
