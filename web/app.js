const API = '';
let currentProjectId = null;

function $(s){ return document.querySelector(s); }
function $$(s){ return Array.from(document.querySelectorAll(s)); }

function toast(msg){
  const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
  setTimeout(()=> t.style.display = 'none', 3000);
}

async function get(path){ const r = await fetch(API + path); return r.ok ? r.json() : {error: r.status}; }
async function post(path, body){
  const opts = {method:'POST', headers:{}};
  if(body) { opts.headers['Content-Type']='application/json'; opts.body=JSON.stringify(body); }
  const r = await fetch(API + path, opts);
  return r.ok ? r.json() : {error: r.status};
}

// Tabs
$$('nav a').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    $$('nav a').forEach(x => x.classList.remove('active'));
    a.classList.add('active');
    $$('.tab').forEach(t => t.classList.remove('active'));
    $('#tab-' + a.dataset.tab).classList.add('active');
    refreshTab(a.dataset.tab);
  });
});

function refreshTab(tab){
  if(tab==='command') loadCommand();
  if(tab==='projects') loadProjects();
  if(tab==='revenue') loadRevenue();
  if(tab==='models') loadModels();
  if(tab==='programs') loadPrograms();
  if(tab==='system') loadSystem();
  if(tab==='agents') loadAgents();
  if(tab==='comfy') loadComfy();
  if(tab==='files') loadFiles();
  if(tab==='context') loadContext();
  if(tab==='graveyard') loadGraveyard();
}

function pctClass(pct){
  if(pct >= 90) return 'complete';
  if(pct >= 60) return 'high';
  if(pct >= 30) return 'mid';
  return 'low';
}

async function loadCommand(){
  const sum = await get('/api/summary');
  const sys = await get('/api/system');
  const agents = await get('/api/agents');
  const projects = await get('/api/projects?sort=today_score');

  const top = sum.top_project || (projects[0] || {});
  $('#cc-top-action').innerHTML = `<h2>Top Action Today</h2><div class="kpi">${top.name || '—'}</div><div class="sub">${top.next_action || 'No action defined'}</div><div class="sub">ETA: ${top.next_action_eta_hours || '—'}h | Agent: ${top.assigned_agent || '—'}</div>`;

  const active = projects.find(p => p.status==='Active') || top;
  $('#cc-battlefield').innerHTML = `<h2>Active Battlefield</h2><div class="kpi">${active.name || '—'}</div><div class="sub">${active.blocker ? 'BLOCKED: '+active.blocker : 'No blockers'}</div>`;

  const blocked = projects.filter(p => p.blocker);
  $('#cc-blockers').innerHTML = `<h2>Blockers (${blocked.length})</h2>` + blocked.slice(0,3).map(b => `<div class="sub">• ${b.name}: ${b.blocker}</div>`).join('');

  const s = sys;
  $('#cc-health').innerHTML = `<h2>System Health</h2><div class="sub">CPU: ${s.cpu_pct ?? '—'}%</div><div class="sub">RAM: ${s.ram_used_gb ?? '—'}/${s.ram_total_gb ?? '—'} GB</div>`;

  $('#cc-gpu0').innerHTML = `<h2>GPU 0</h2><div class="sub">${s.gpu0_name || 'N/A'}</div><div class="sub">Util: ${s.gpu0_util_pct ?? '—'}%</div><div class="sub">VRAM: ${s.gpu0_vram_used_gb ?? '—'}/${s.gpu0_vram_total_gb ?? '—'} GB</div>`;
  $('#cc-gpu1').innerHTML = `<h2>GPU 1</h2><div class="sub">${s.gpu1_name || 'N/A'}</div><div class="sub">Util: ${s.gpu1_util_pct ?? '—'}%</div><div class="sub">VRAM: ${s.gpu1_vram_used_gb ?? '—'}/${s.gpu1_vram_total_gb ?? '—'} GB</div>`;

  const live = (agents || []).filter(a => a.status==='LIVE').length;
  $('#cc-agents').innerHTML = `<h2>Active Agents</h2><div class="kpi">${live}</div><div class="sub">of ${agents.length} tracked</div>`;

  const svcs = JSON.parse(s.running_services_json || '[]');
  $('#cc-services').innerHTML = `<h2>Running Services (${svcs.length})</h2>` + svcs.slice(0,8).map(x => `<div class="sub">${x.matched}: PID ${x.pid} ${x.name}</div>`).join('');

  $('#lastScan').textContent = 'Scan: ' + (sum.latest_scan ? sum.latest_scan.finished_at : '—');
  $('#lastMonitor').textContent = 'Monitor: ' + (sum.latest_monitor ? sum.latest_monitor.timestamp : '—');
}

async function loadProjects(){
  const status = $('#projStatus').value;
  const sort = $('#projSort').value;
  let url = '/api/projects?sort=' + encodeURIComponent(sort);
  if(status) url += '&status=' + encodeURIComponent(status);
  const data = await get(url);
  const q = $('#projSearch').value.toLowerCase();
  const filtered = data.filter(p => !q || (p.name||'').toLowerCase().includes(q) || (p.notes||'').toLowerCase().includes(q));

  $('#projectsGrid').innerHTML = filtered.map(p => `
    <div class="card" style="cursor:pointer;" onclick="openProjectWorkflow(${p.id})">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <strong style="font-size:1.05rem;color:var(--cream);">${p.name}</strong>
        <span class="status-pill ${p.status.toLowerCase().replace(/\s+/g,'-')}">${p.status}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${pctClass(p.completion_pct)}" style="width:${p.completion_pct}%"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:.8rem;color:var(--text-dim);margin-top:4px;">
        <span>${p.completion_pct}% complete</span>
        <span>Score: ${p.today_score}</span>
      </div>
      <div class="sub" style="margin-top:10px;">
        Verified: $${(p.market_value_verified||0).toLocaleString()} |
        Replacement: $${(p.replacement_cost_value||0).toLocaleString()}
      </div>
      <div class="sub">Next: ${p.next_action || '—'} (${p.next_action_eta_hours}h)</div>
      <div class="sub">Agent: ${p.assigned_agent || '—'} | Blocker: ${p.blocker || 'None'}</div>
      <div style="margin-top:10px;text-align:right;">
        <span style="font-size:.75rem;color:var(--teal-muted);">Click to open workflow →</span>
      </div>
    </div>
  `).join('');
}
$('#projSearch').addEventListener('input', ()=> loadProjects());
$('#projStatus').addEventListener('change', ()=> loadProjects());
$('#projSort').addEventListener('change', ()=> loadProjects());

async function openProjectWorkflow(projectId){
  currentProjectId = projectId;
  const data = await get(`/api/project/${projectId}/workflow`);
  if(data.error) { toast('Error loading workflow'); return; }

  const p = data.project;
  $('#modalTitle').textContent = p.name;
  $('#modalCompletion').textContent = p.completion_pct + '%';
  $('#modalScore').textContent = 'Score: ' + p.today_score;
  $('#modalProgressBar').style.width = p.completion_pct + '%';
  $('#modalProgressBar').className = 'progress-fill ' + pctClass(p.completion_pct);

  $('#modalMeta').innerHTML = `
    <span>${p.category}</span>
    <span>${p.status}</span>
    <span>Agent: ${p.assigned_agent || '—'}</span>
    <span>ETA: ${p.next_action_eta_hours}h</span>
  `;

  $('#modalValuations').innerHTML = `
    <div class="valuation-card verified">
      <div class="val-label">Verified Market</div>
      <div class="val-amount">$${(p.market_value_verified||0).toLocaleString()}</div>
    </div>
    <div class="valuation-card replacement">
      <div class="val-label">Replacement Cost</div>
      <div class="val-amount">$${(p.replacement_cost_value||0).toLocaleString()}</div>
    </div>
    <div class="valuation-card strategic">
      <div class="val-label">Strategic Upside</div>
      <div class="val-amount">$${(p.strategic_upside_value||0).toLocaleString()}</div>
    </div>
  `;

  $('#modalChecklist').innerHTML = data.checklist.map(c => `
    <li class="${c.is_done ? 'done' : ''}">
      <input type="checkbox" ${c.is_done ? 'checked' : ''}
        onchange="toggleChecklist(${projectId}, ${c.step_number}, this.checked)">
      <div class="check-text">${c.description}</div>
      <div class="check-eta">${c.eta_hours}h · ${c.money_path}</div>
    </li>
  `).join('');

  const next = data.next_uncheck;
  $('#modalMonetization').innerHTML = `
    <div class="sub"><strong>Next monetization action:</strong> ${p.next_action || 'Define next step'}</div>
    <div class="sub" style="margin-top:6px;"><strong>Proof needed:</strong> ${p.valuation_confidence < 50 ? 'Revenue evidence, demo, or user validation' : 'Scale evidence'}</div>
    <div class="sub" style="margin-top:6px;"><strong>To reach 100%:</strong> ${data.total_eta} hours of work remaining${next ? '. Next: ' + next.description : ''}</div>
  `;

  $('#modalResources').innerHTML = `
    <div class="sub"><strong>Assigned agent:</strong> ${p.assigned_agent || 'Unassigned'}</div>
    <div class="sub" style="margin-top:6px;"><strong>Related files:</strong> ${data.files.length} found</div>
    <div class="sub" style="margin-top:6px;"><strong>Confidence:</strong> ${p.valuation_confidence}% — ${p.valuation_method}</div>
  `;

  $('#projectModal').classList.add('active');
}

async function toggleChecklist(projectId, stepNumber, checked){
  const res = await post(`/api/project/${projectId}/checklist/${stepNumber}?is_done=${checked ? 1 : 0}`);
  if(res.error) { toast('Save failed'); return; }
  // Refresh modal and project list
  openProjectWorkflow(projectId);
  loadProjects();
  toast('Progress saved');
}

$('#modalClose').addEventListener('click', () => {
  $('#projectModal').classList.remove('active');
  currentProjectId = null;
});

$('#btnSaveProgress').addEventListener('click', () => {
  toast('Progress auto-saved on each checkbox');
});

$('#btnMarkComplete').addEventListener('click', async () => {
  if(!currentProjectId) return;
  await post('/api/project/update?project_id=' + currentProjectId + '&status=Complete&completion_pct=100');
  toast('Marked complete');
  $('#projectModal').classList.remove('active');
  loadProjects();
});

async function loadRevenue(){
  const data = await get('/api/revenue-today');
  $('#revenueContent').innerHTML = `<pre style="white-space:pre-wrap;font-family:inherit;color:var(--text-main);">${data.content}</pre>`;
}

async function loadModels(){
  const data = await get('/api/models');
  $('#modelsGrid').innerHTML = data.slice(0,300).map(m => `
    <div class="card">
      <strong style="color:var(--cream);">${m.name}</strong>
      <div class="sub">${m.model_type} | ${m.architecture}</div>
      <div class="sub">Size: ${(m.size_bytes/1e9).toFixed(2)} GB | Source: ${m.source}</div>
      <div class="sub">License: ${m.commercial_license_status} ${m.duplicate_group ? '| DUP' : ''}</div>
    </div>
  `).join('');
}

async function loadPrograms(){
  const data = await get('/api/programs');
  $('#programsGrid').innerHTML = data.map(p => `
    <div class="card">
      <strong style="color:var(--cream);">${p.name}</strong>
      <div class="sub">${p.category} | ${p.version || '—'}</div>
      <div class="sub">Role: ${p.role_in_stack || '—'} | Status: ${p.status}</div>
    </div>
  `).join('');
}

async function loadSystem(){
  const s = await get('/api/system');
  $('#sys-cpu').innerHTML = `<h2>CPU</h2><div class="kpi">${s.cpu_pct ?? '—'}%</div>`;
  $('#sys-ram').innerHTML = `<h2>RAM</h2><div class="kpi">${s.ram_used_gb ?? '—'}</div><div class="sub">of ${s.ram_total_gb ?? '—'} GB</div>`;
  $('#sys-gpu0').innerHTML = `<h2>GPU 0</h2><div class="sub">${s.gpu0_name || 'N/A'}</div><div class="sub">Util: ${s.gpu0_util_pct ?? '—'}%</div><div class="sub">VRAM: ${s.gpu0_vram_used_gb ?? '—'}/${s.gpu0_vram_total_gb ?? '—'} GB</div>`;
  $('#sys-gpu1').innerHTML = `<h2>GPU 1</h2><div class="sub">${s.gpu1_name || 'N/A'}</div><div class="sub">Util: ${s.gpu1_util_pct ?? '—'}%</div><div class="sub">VRAM: ${s.gpu1_vram_used_gb ?? '—'}/${s.gpu1_vram_total_gb ?? '—'} GB</div>`;

  const disks = JSON.parse(s.disk_json || '[]');
  $('#sys-disks').innerHTML = `<h2>Disks</h2>` + disks.map(d => `<div class="sub">${d.device} ${d.mountpoint}: ${d.used_gb} / ${d.total_gb} GB (${d.percent}%)</div>`).join('');

  const ports = JSON.parse(s.open_ports_json || '[]');
  $('#sys-ports').innerHTML = `<h2>Open Ports (${ports.length})</h2>` + ports.slice(0,20).map(p => `<div class="sub">Port ${p.port} PID ${p.pid} ${p.status}</div>`).join('');
}

async function loadAgents(){
  const data = await get('/api/agents');
  $('#agentsGrid').innerHTML = data.map(a => `
    <div class="card agent-card ${a.status.toLowerCase()}">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong style="color:var(--cream);">${a.name}</strong>
        <span class="status-pill ${a.status.toLowerCase()}">${a.status}</span>
      </div>
      <div class="sub">Framework: ${a.framework}</div>
      <div class="sub">PID: ${a.process_id || '—'} | Port: ${a.port || '—'}</div>
      <div class="sub">Model: ${a.model_used || '—'} | GPU: ${a.gpu_id || '—'}</div>
      <div class="sub">Task: ${a.current_task || '—'}</div>
    </div>
  `).join('');
}

async function loadComfy(){
  const data = await get('/api/comfy');
  $('#comfyGrid').innerHTML = data.map(c => `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong style="color:var(--cream);">${c.name}</strong>
        <span class="status-pill ${c.status.toLowerCase().replace(/\s+/g,'-')}">${c.status}</span>
      </div>
      <div class="sub">Videos: ${c.completed_video_count} / ${c.target_video_count}</div>
      <div class="sub">Failed: ${c.failed_count}</div>
      <div class="sub">Next: ${c.next_render_action || '—'}</div>
    </div>
  `).join('');
}

async function loadFiles(){
  const q = $('#fileSearch').value;
  const st = $('#fileStatus').value;
  let url = '/api/files?';
  if(q) url += 'q=' + encodeURIComponent(q) + '&';
  if(st) url += 'status=' + encodeURIComponent(st) + '&';
  const data = await get(url);
  const tbody = $('#filesTable tbody');
  tbody.innerHTML = data.slice(0,500).map(f => `
    <tr>
      <td title="${f.path}">${f.filename}</td>
      <td>${f.project_id || '—'}</td>
      <td><span class="status-pill ${f.status.toLowerCase().replace(/\s+/g,'-')}">${f.status}</span></td>
      <td>${f.modified_at ? f.modified_at.slice(0,16).replace('T',' ') : '—'}</td>
      <td>${f.reusable ? 'Yes' : 'No'}</td>
      <td>${f.secret_detected ? '<span class="status-pill down">SECRET</span>' : '—'}</td>
    </tr>
  `).join('');
}
$('#fileSearch').addEventListener('input', ()=> loadFiles());
$('#fileStatus').addEventListener('change', ()=> loadFiles());

async function loadContext(){
  const data = await get('/api/context-card');
  $('#contextText').value = data.content;
}
$('#btnCopyContext').addEventListener('click', ()=> {
  $('#contextText').select();
  document.execCommand('copy');
  toast('Context card copied');
});

async function loadGraveyard(){
  const data = await get('/api/projects?status=Graveyard');
  $('#graveyardGrid').innerHTML = data.map(p => `
    <div class="card">
      <strong style="color:var(--cream);">${p.name}</strong>
      <div class="sub">${p.notes || 'No notes'}</div>
      <div class="sub">Do not resurrect without revenue proof.</div>
    </div>
  `).join('');
}

$('#btnScan').addEventListener('click', async ()=>{
  toast('Scan started…');
  await post('/api/scan');
  toast('Scan complete');
  refreshTab('command');
});
$('#btnMonitor').addEventListener('click', async ()=>{
  toast('Monitor refresh…');
  await post('/api/monitor');
  toast('Monitor refreshed');
  refreshTab('command');
});

// Close modal on overlay click
$('#projectModal').addEventListener('click', (e)=>{
  if(e.target === $('#projectModal')){
    $('#projectModal').classList.remove('active');
    currentProjectId = null;
  }
});

// Auto refresh
setInterval(()=> refreshTab('command'), 5000);
setInterval(()=> {
  const tab = $$('nav a.active')[0]?.dataset.tab;
  if(tab && tab !== 'command') refreshTab(tab);
}, 60000);

// Initial load
refreshTab('command');
