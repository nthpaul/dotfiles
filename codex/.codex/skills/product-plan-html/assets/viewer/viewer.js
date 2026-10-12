(() => {
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const badge = (label, tone = 'violet') => `<span class="badge ${esc(tone)}">${esc(label)}</span>`;
  const prototype = window.PROTOTYPE;
  const meta = PLAN.document || {};
  const surfaces = prototype?.surfaces || [];
  const extendedTables = PLAN.tables.filter(t => t.storage === 'extension').length;
  const newTables = PLAN.tables.length - extendedTables;
  const tabs = [{id:'overview',label:'Overview'},{id:'model',label:'Data model'},{id:'flow',label:'Logic & data flow'},{id:'diagrams',label:'Diagrams'}, ...surfaces];
  let view = tabs.some(t => t.id === location.hash.slice(1)) ? location.hash.slice(1) : 'overview';
  let flowId = PLAN.flows[0]?.id;
  let diagramId = DIAGRAMS[0]?.id;
  const list = items => `<ul class="bullets">${(items || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;

  function overviewView() {
    if (prototype?.overview) return prototype.overview();
    const summary = PLAN.summary || {};
    const metrics = [[newTables,'new tables','model'],[PLAN.flows.length,'complete flows','flow']];
    if (surfaces.length) metrics.push([surfaces.length,'preview surfaces',surfaces[0].id]);
    return `<div class="container"><div class="section-head"><div><h2>${esc(summary.decision || meta.title || 'Product plan')}</h2><p>${esc(summary.nextAction || meta.subtitle)}</p></div>${badge('Architecture proposal')}</div>
      <div class="cards">${metrics.map(([n,label,id]) => `<div class="card"><div class="metric">${n}</div><h3>${esc(label)}</h3>${id === 'model' && extendedTables ? `<p>${extendedTables} existing ${extendedTables === 1 ? 'table' : 'tables'} extended</p>` : ''}<button class="space-top" data-view="${esc(id)}">Explore →</button></div>`).join('')}</div>
      <div class="split space-top"><div class="card"><h3>Reuse</h3>${list(summary.reuse)}</div><div class="card"><h3>Net new</h3>${list(summary.netNew)}</div></div>
      <div class="split space-top"><div class="card"><h3>Architecture choices</h3>${list(PLAN.decisions)}</div><div class="card"><h3>Decisions to settle</h3>${list(PLAN.questions)}</div></div>
      <div class="card space-top"><h3>Build sequence</h3>${list(summary.buildSequence)}</div>
      <div class="card space-top"><h3>Evidence</h3><p>${esc(summary.evidence || 'Proposed behavior. Existing behavior must be checked against the sources below.')}</p><div class="source-list space-top">${(PLAN.sources || []).map(([label,path]) => `<div>${esc(label)} <span class="muted source-link">${esc(path)}</span></div>`).join('')}</div></div></div>`;
  }

  function modelView() {
    const intro = meta.modelIntro || 'Each field shows its physical type and nullability. Calendar dates and instants use separate types.';
    return `<div class="container"><div class="section-head"><div><h2>The full data model</h2><p>Table names, every field, foreign keys, constraints and existing-table changes. Open any table to inspect it.</p></div><a href="data-model.json" download>Download JSON ↗</a></div>
      ${diagramPanel('model')}
      <div class="tint blue" style="margin-bottom:20px"><h3>${esc(meta.modelConventionsTitle || 'Data conventions')}</h3><p>${esc(intro)}</p></div>
      ${PLAN.tables.map((t,i) => `<details class="model-table" ${i === 0 ? 'open' : ''}><summary><div><h3>${esc(t.name)}</h3><p>${esc(t.purpose)}</p>${t.storage === 'extension' ? badge('Existing · proposed extension','green') : ''}</div>${badge(`${t.fields.length} fields`,'blue')}</summary><div class="table-wrap"><table class="field-table"><thead><tr><th>Field</th><th>Type</th><th>How it works</th><th>References</th></tr></thead><tbody>${t.fields.map(f => `<tr><td><code>${esc(f.name)}</code></td><td>${esc(f.type)}</td><td>${esc(f.rule)}</td><td>${esc(f.relation || '—')}</td></tr>`).join('')}</tbody></table></div><div class="model-notes"><p><strong>Relationships</strong> · ${esc(t.relationships || '')}</p>${list(t.constraints)}</div></details>`).join('')}
      <div class="section-head space-top"><h2>Existing tables and services</h2>${badge('Reuse / extend','green')}</div><div class="table-wrap card" style="padding:0"><table><thead><tr><th>Table / service</th><th>Change</th><th>Why</th></tr></thead><tbody>${(PLAN.existing || []).map(t => `<tr><td><strong>${esc(t.name)}</strong></td><td>${esc(t.change)}</td><td>${esc(t.why)}</td></tr>`).join('')}</tbody></table></div>
      ${meta.notStored ? `<div class="card space-top"><h3>What is intentionally not stored</h3><p>${esc(meta.notStored)}</p></div>` : ''}</div>`;
  }

  function flowView() {
    const flow = PLAN.flows.find(f => f.id === flowId);
    return `<div class="container"><div class="section-head"><div><h2>Logic flow, including data flow</h2><p>Follow the input through decisions, database writes and the next visible result.</p></div>${badge('Backend owns state')}</div>
      ${meta.flowContract ? `<div class="flow-contract">${esc(meta.flowContract)}</div>` : ''}
      <div class="flow-tabs">${PLAN.flows.map(f => `<button data-flow="${esc(f.id)}" class="${f.id === flowId ? 'active' : ''}">${esc(f.title)}</button>`).join('')}</div>
      ${flow ? `<div class="section-head"><div><h3>${esc(flow.title)}</h3><p>${esc(flow.summary)}</p></div></div>${diagramPanel(flow.id)}${flow.steps.map((s,i) => `<div class="flow-step"><span class="number">${i+1}</span><div class="card"><h3>${esc(s[0])}</h3><div class="flow-grid">${['Input','Read / decide','Write','Output / next action'].map((label,j) => `<div><div class="eyebrow">${label}</div><p>${esc(s[j+1])}</p></div>`).join('')}</div></div></div>`).join('')}` : '<p>No flows defined.</p>'}
      ${(meta.flowNotes || []).length ? `<div class="split space-top">${meta.flowNotes.map(n => `<div class="tint ${esc(n.tone || '')}"><h3>${esc(n.title)}</h3><p style="margin-top:10px">${esc(n.text)}</p></div>`).join('')}</div>` : ''}</div>`;
  }

  function diagramPanel(id) {
    const d = DIAGRAMS.find(x => x.id === id);
    if (!d) return '';
    return `<section class="diagram-panel" aria-label="${esc(d.title)} diagram"><div class="diagram-header"><div><h3>${esc(d.title)}</h3><p>${esc(d.description)}</p></div><div class="diagram-controls"><button data-diagram-zoom="fit" aria-label="Fit diagram">Fit</button><button data-diagram-zoom="100" aria-label="Diagram at full size">100%</button><button data-diagram-zoom="out" aria-label="Zoom out diagram">−</button><button data-diagram-zoom="in" aria-label="Zoom in diagram">+</button><a href="data:image/svg+xml;charset=utf-8,${encodeURIComponent(d.svg)}" download="${esc(d.id)}.svg">SVG ↗</a><a href="data:text/plain;charset=utf-8,${encodeURIComponent(d.mermaid)}" download="${esc(d.id)}.mmd">Mermaid ↗</a></div></div><div class="diagram-canvas" tabindex="0" aria-label="Scrollable diagram; use zoom controls for detail">${d.svg}</div><div class="diagram-legend"><span>${badge('New table / logic')} ${badge('Existing table / service','green')} ${badge('State / persisted data','blue')} ${badge('Decision','orange')}</span><span>Fit to overview · 100% to read · Scroll to explore</span></div></section>`;
  }

  function diagramsView() {
    return `<div class="container"><div class="section-head"><div><h2>Data model & flow diagrams</h2><p>Table relationships, all fields and foreign keys, system data flow, and the key decisions.</p></div><a href="diagrams.md" download>Diagram source ↗</a></div><div class="flow-tabs">${DIAGRAMS.map(d => `<button data-diagram="${esc(d.id)}" class="${diagramId === d.id ? 'active' : ''}">${esc(d.title)}</button>`).join('')}</div>${diagramPanel(diagramId)}${meta.diagramNote ? `<div class="tint space-top"><h3>Ownership</h3><p style="margin-top:8px">${esc(meta.diagramNote)}</p></div>` : ''}</div>`;
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
  $('.review-tabs').innerHTML = tabs.map((t,i) => `${i === 4 ? '<span class="nav-separator"></span>' : ''}<button data-view="${esc(t.id)}">${esc(t.label)}</button>`).join('');
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
  window.addEventListener('hashchange', () => setView(location.hash.slice(1)));
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
