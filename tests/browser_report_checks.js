// Inject into a scratch copy of the generated HTML for a real-browser smoke test.
(function () {
  const checks=[];
  const assert=(ok,label)=>{if(!ok)throw new Error(label);checks.push(label);};
  const select=(id,value)=>{const e=document.getElementById(id);e.value=value;e.dispatchEvent(new Event('change',{bubbles:true}));};
  const cell=i=>document.querySelectorAll('#price-grid .price-cell')[i];
  const result=document.createElement('pre');result.id='browser-check-results';
  try {
    assert(document.querySelectorAll('#storm-cards article').length===4,'four storm profiles');
    assert(document.querySelectorAll('#coverage-chart .bar-row').length===4,'four readable coverage bars');
    assert(cell(1).textContent.includes('+0.70')&&cell(1).textContent.includes('5 paired bonds'),'default strict Beryl price result');
    select('price-days','1');
    assert(cell(1).textContent.includes('+0.03')&&cell(1).textContent.includes('33 paired bonds'),'date-support sensitivity updates');
    if(document.getElementById('price-chart'))assert(document.getElementById('price-chart').textContent.includes('+0.03'),'status price chart follows support control');
    select('price-side','sell');
    assert(cell(1).textContent.includes('+0.00'),'customer side updates');
    select('price-storm','milton');select('price-days','2');select('price-restriction','no_other_catalog_landfall');
    assert([...document.querySelectorAll('#price-grid .price-cell')].every(e=>e.textContent.includes('0 paired bonds')),'competing-landfall exclusion updates');
    select('price-storm','idalia');select('price-restriction','all_strict');
    assert(cell(3).textContent.includes('+0.10')&&cell(3).textContent.includes('5 paired bonds'),'storm-specific results update');
    select('price-sample','reviewed_target_scope');
    assert([...document.querySelectorAll('#price-grid strong')].every(e=>e.textContent==='—'),'small cells remain suppressed');
    select('forecast-storm','ian');
    assert(document.querySelector('#forecast-chart svg').getAttribute('aria-label').includes('Ian'),'forecast chart changes storm');
    const toggle=document.querySelector('button[data-table]');
    if(toggle){
      const panel=document.getElementById(toggle.dataset.table);
      toggle.click();assert(!panel.hidden&&toggle.getAttribute('aria-expanded')==='true','status data-table toggle opens');
      toggle.click();assert(panel.hidden&&toggle.getAttribute('aria-expanded')==='false','status data-table toggle closes');
      assert(document.querySelectorAll('#forecast-table tbody tr').length===38,'forecast table follows storm selector');
    }
    document.querySelector('[data-age="1"]').click();
    assert(document.querySelector('[data-age="1"]').getAttribute('aria-pressed')==='true','market-age control updates');
    assert(document.querySelector('#timing-table').textContent.includes('Beryl'),'timing table populated');
    assert(document.querySelectorAll('img').length===0,'no image dependencies');
    assert(document.documentElement.scrollHeight>window.innerHeight*3,'long scrollable report');
    assert(document.documentElement.scrollWidth<=window.innerWidth,'no page-wide horizontal overflow');
    select('price-storm','beryl');select('price-side','buy');select('price-sample','all_identity_eligible');
    result.textContent=JSON.stringify({passed:true,checks});
  } catch (error) {
    result.textContent=JSON.stringify({passed:false,error:error.message,checks});
  }
  document.body.appendChild(result);
  document.documentElement.style.scrollBehavior='auto';
  window.scrollTo(0,document.getElementById('prices').offsetTop-80);
}());
