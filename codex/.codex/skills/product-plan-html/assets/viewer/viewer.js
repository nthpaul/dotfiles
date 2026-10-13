(() => {
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const badge = (label, tone = 'violet') => `<span class="badge ${esc(tone)}">${esc(label)}</span>`;
  const prototype = window.PROTOTYPE;
  const meta = PLAN.document || {};
  const tables = PLAN.tables || [];
  const flows = PLAN.flows || [];
  const existing = PLAN.existing || [];
  const surfaces = prototype?.surfaces || [];
  const extendedTables = tables.filter(t => t.storage === 'extension').length;
  const newTables = tables.length - extendedTables;
  const hasModel = tables.length || meta.modelIntro || meta.notStored;
  const documentTabs = [{id:'overview',label:'Overview'}];
  if (hasModel) documentTabs.push({id:'model',label:'Data model'});
  if (flows.length || meta.flowContract || meta.flowNotes?.length) documentTabs.push({id:'flow',label:'Logic & data flow'});
  if (DIAGRAMS.length) documentTabs.push({id:'diagrams',label:'Diagrams'});
  const tabs = [...documentTabs, ...surfaces];
  let view = tabs.some(t => t.id === location.hash.slice(1)) ? location.hash.slice(1) : tabs[0].id;
  let flowId = flows[0]?.id;
  let diagramId = DIAGRAMS[0]?.id;
  const list = items => `<ul class="bullets">${(items || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
  const paragraph = value => value ? `<p>${esc(value)}</p>` : '';
  const listCard = (title, items) => items?.length ? `<div class="card"><h3>${esc(title)}</h3>${list(items)}</div>` : '';

  function existingView() {
    if (!existing.length) return '';
    const columns = [['name','Table / service'],['change','Change'],['why','Why']].filter(([key]) => existing.some(item => item[key]));
    return `<div class="section-head space-top"><h2>Existing tables and services</h2>${badge('Reuse / extend','green')}</div><div class="table-wrap card" style="padding:0"><table><thead><tr>${columns.map(([,label]) => `<th>${esc(label)}</th>`).join('')}</tr></thead><tbody>${existing.map(item => `<tr>${columns.map(([key]) => `<td>${esc(item[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  function overviewView() {
    if (prototype?.overview) return prototype.overview();
    const summary = PLAN.summary || {};
    const metrics = [];
    if (newTables) metrics.push([newTables,'new tables','model']);
    if (extendedTables) metrics.push([extendedTables,'existing tables extended','model']);
    if (flows.length) metrics.push([flows.length,'flows','flow']);
    if (surfaces.length) metrics.push([surfaces.length,'preview surfaces',surfaces[0].id]);
    const cards = [listCard('Reuse',summary.reuse),listCard('Net new',summary.netNew),listCard('Architecture choices',PLAN.decisions),listCard('Decisions to settle',PLAN.questions),listCard('Build sequence',summary.buildSequence)].filter(Boolean);
    const sources = PLAN.sources || [];
    return `<div class="container"><div class="section-head"><div><h2>${esc(summary.decision || meta.title || 'Product plan')}</h2>${paragraph(summary.nextAction || meta.subtitle)}</div></div>
      ${metrics.length ? `<div class="cards">${metrics.map(([n,label,id]) => `<div class="card"><div class="metric">${n}</div><h3>${esc(label)}</h3><button class="space-top" data-view="${esc(id)}">Explore →</button></div>`).join('')}</div>` : ''}
      ${cards.length ? `<div class="cards space-top">${cards.join('')}</div>` : ''}
      ${!hasModel ? existingView() : ''}
      ${summary.evidence || sources.length ? `<div class="card space-top"><h3>${summary.evidence ? 'Evidence' : 'Sources'}</h3>${paragraph(summary.evidence)}${sources.length ? `<div class="source-list space-top">${sources.map(([label,path]) => `<div>${esc(label)} <span class="muted source-link">${esc(path)}</span></div>`).join('')}</div>` : ''}</div>` : ''}</div>`;
  }

  function modelView() {
    return `<div class="container"><div class="section-head"><h2>Data model</h2>${tables.length ? '<a href="data-model.json" download>Download JSON ↗</a>' : ''}</div>
      ${diagramPanel('model')}
      ${meta.modelIntro ? `<div class="tint blue" style="margin-bottom:20px">${meta.modelConventionsTitle ? `<h3>${esc(meta.modelConventionsTitle)}</h3>` : ''}${paragraph(meta.modelIntro)}</div>` : ''}
      ${tables.map((t,i) => {
        const columns = [['name','Field'],['type','Type'],['rule','How it works'],['relation','References']].filter(([key]) => t.fields.some(f => f[key]));
        return `<details class="model-table" ${i === 0 ? 'open' : ''}><summary><div><h3>${esc(t.name)}</h3>${paragraph(t.purpose)}${t.storage === 'extension' ? badge('Existing · proposed extension','green') : ''}</div>${badge(`${t.fields.length} fields`,'blue')}</summary><div class="table-wrap"><table class="field-table"><thead><tr>${columns.map(([,label]) => `<th>${esc(label)}</th>`).join('')}</tr></thead><tbody>${t.fields.map(f => `<tr>${columns.map(([key]) => `<td>${key === 'name' ? `<code>${esc(f[key])}</code>` : esc(f[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${t.relationships || t.constraints?.length ? `<div class="model-notes">${t.relationships ? `<p><strong>Relationships</strong> · ${esc(t.relationships)}</p>` : ''}${t.constraints?.length ? list(t.constraints) : ''}</div>` : ''}</details>`;
      }).join('')}
      ${existingView()}
      ${meta.notStored ? `<div class="card space-top"><h3>What is intentionally not stored</h3><p>${esc(meta.notStored)}</p></div>` : ''}</div>`;
  }

  function flowView() {
    const flow = flows.find(f => f.id === flowId);
    const columns = (flow?.columns || ['Step','Input','Read / decide','Write','Output / next action']).map((label,index) => ({label,index})).filter(c => c.index && flow?.steps.some(s => s[c.index]?.trim()));
    return `<div class="container"><div class="section-head"><h2>Logic & data flow</h2>${flow?.owner ? badge(flow.owner) : ''}</div>
      ${meta.flowContract ? `<div class="flow-contract">${esc(meta.flowContract)}</div>` : ''}
      ${flows.length > 1 ? `<div class="flow-tabs">${flows.map(f => `<button data-flow="${esc(f.id)}" class="${f.id === flowId ? 'active' : ''}">${esc(f.title)}</button>`).join('')}</div>` : ''}
      ${flow ? `<div class="section-head"><div><h3>${esc(flow.title)}</h3>${paragraph(flow.summary)}</div></div>${diagramPanel(flow.id)}${flow.steps.map((s,i) => `<div class="flow-step"><span class="number">${i+1}</span><div class="card"><h3>${esc(s[0])}</h3>${columns.length ? `<div class="flow-grid" style="--flow-columns:${columns.length}">${columns.map(c => `<div><div class="eyebrow">${esc(c.label)}</div><p>${esc(s[c.index])}</p></div>`).join('')}</div>` : ''}</div></div>`).join('')}` : ''}
      ${(meta.flowNotes || []).length ? `<div class="split space-top">${meta.flowNotes.map(n => `<div class="tint ${esc(n.tone || '')}"><h3>${esc(n.title)}</h3><p style="margin-top:10px">${esc(n.text)}</p></div>`).join('')}</div>` : ''}</div>`;
  }

  function diagramPanel(id) {
    const d = DIAGRAMS.find(x => x.id === id);
    if (!d) return '';
    return `<section class="diagram-panel" aria-label="${esc(d.title)} diagram"><div class="diagram-header"><div><h3>${esc(d.title)}</h3>${paragraph(d.description)}</div><div class="diagram-controls"><button data-diagram-zoom="fit" aria-label="Fit diagram">Fit</button><button data-diagram-zoom="100" aria-label="Diagram at full size">100%</button><button data-diagram-zoom="out" aria-label="Zoom out diagram">−</button><button data-diagram-zoom="in" aria-label="Zoom in diagram">+</button><a href="data:image/svg+xml;charset=utf-8,${encodeURIComponent(d.svg)}" download="${esc(d.id)}.svg">SVG ↗</a><a href="data:text/plain;charset=utf-8,${encodeURIComponent(d.mermaid)}" download="${esc(d.id)}.mmd">Mermaid ↗</a></div></div><div class="diagram-canvas" tabindex="0" aria-label="Scrollable diagram; use zoom controls for detail">${d.svg}</div><div class="diagram-legend"><span>Fit to overview · 100% to read · Scroll to explore</span></div></section>`;
  }

  function diagramsView() {
    return `<div class="container"><div class="section-head"><h2>Diagrams</h2><a href="diagrams.md" download>Diagram source ↗</a></div>${DIAGRAMS.length > 1 ? `<div class="flow-tabs">${DIAGRAMS.map(d => `<button data-diagram="${esc(d.id)}" class="${diagramId === d.id ? 'active' : ''}">${esc(d.title)}</button>`).join('')}</div>` : ''}${diagramPanel(diagramId)}${meta.diagramNote ? `<div class="tint space-top"><p>${esc(meta.diagramNote)}</p></div>` : ''}</div>`;
  }

  function render() {
    $('.review-tabs').querySelectorAll('button').forEach(b => {
      b.classList.toggle('active', b.dataset.view === view);
      b.setAttribute('aria-current', b.dataset.view === view ? 'page' : 'false');
    });
    $('#scenario-bar').hidden = !surfaces.some(s => s.id === view) || !prototype?.scenarios?.length;
    $('[data-action="reset"]').hidden = !prototype?.reset;
    const status = prototype?.status?.();
    $('#scenario-status').innerHTML = status ? badge(status.label, status.tone) : '';
    const renderers = {overview:overviewView,model:modelView,flow:flowView,diagrams:diagramsView};
    $('#app').innerHTML = Object.hasOwn(renderers, view) ? renderers[view]() : prototype.render(view);
  }

  function setView(next) {
    if (!tabs.some(t => t.id === next)) return;
    view = next;
    history.replaceState(null, '', '#' + view);
    render();
    window.scrollTo({top:0,behavior:'instant'});
  }

  window.PlanDocument = {render,setView};
  $('.review-tabs').innerHTML = tabs.map((t,i) => `${i === documentTabs.length ? '<span class="nav-separator"></span>' : ''}<button data-view="${esc(t.id)}">${esc(t.label)}</button>`).join('');
  $('#scenario').innerHTML = (prototype?.scenarios || []).map(s => `<option value="${esc(s.id)}">${esc(s.label)}</option>`).join('');
  if (prototype?.initialScenario) $('#scenario').value = prototype.initialScenario;

  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (button.dataset.view) return setView(button.dataset.view);
    if (button.dataset.flow) {flowId = button.dataset.flow; return render();}
    if (button.dataset.diagram) {diagramId = button.dataset.diagram; return render();}
    if (button.dataset.action === 'reset') return prototype?.reset?.();
    if (button.dataset.diagramZoom) {
      const canvas = button.closest('.diagram-panel').querySelector('.diagram-canvas');
      const svg = canvas.querySelector('svg');
      const natural = Number(svg.getAttribute('viewBox').split(/\s+/)[2]);
      const mode = button.dataset.diagramZoom;
      if (mode === 'fit') {svg.style.width='100%';delete svg.dataset.zoom;canvas.scrollTo(0,0);return;}
      const current = Number(svg.dataset.zoom) || canvas.clientWidth / natural;
      const next = mode === '100' ? 1 : Math.min(3, Math.max(.15, current * (mode === 'in' ? 1.3 : 1/1.3)));
      svg.dataset.zoom = next;
      svg.style.width = natural * next + 'px';
    }
  });
  $('#scenario').addEventListener('change', event => prototype.selectScenario(event.target.value));
  window.addEventListener('hashchange', () => setView(tabs.some(t => t.id === location.hash.slice(1)) ? location.hash.slice(1) : tabs[0].id));
  const modes = ['system','light','dark'];
  let mode = 'system';
  $('#theme-toggle').addEventListener('click', () => {
    mode = modes[(modes.indexOf(mode) + 1) % modes.length];
    if (mode === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = mode;
    $('#theme-toggle').textContent = `Theme: ${mode}`;
  });
  prototype?.init?.();
  render();
})();
