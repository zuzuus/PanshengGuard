/**
 * Popup: settings, a connection test, and a paste box.
 *
 * The paste box is the deliberate fallback. Gmail's class names are not a
 * public API, so if Google changes them the in-page button stops appearing -
 * and the extension would be useless at exactly the wrong moment. This path
 * touches no Gmail DOM at all, so it keeps working regardless.
 */

const el = (id) => document.getElementById(id);

/* ---- presentation helpers (UI only) ----------------------------------- */

// CVSS-style scores, identical to the website report: phishing probability
// (%) / 10 and sophistication_score (0-100) / 10, one decimal, with the CVSS
// v3 bands None 0.0 · Low 0.1-3.9 · Medium 4.0-6.9 · High 7.0-8.9 ·
// Critical 9.0-10.0. Display conversion only.
const SEVERITY = [
  { test: (v) => v <= 0, cls: 'band-low',      name: 'None' },
  { test: (v) => v < 4,  cls: 'band-low',      name: 'Low' },
  { test: (v) => v < 7,  cls: 'band-moderate', name: 'Medium' },
  { test: (v) => v < 9,  cls: 'band-high',     name: 'High' },
  { test: () => true,    cls: 'band-critical', name: 'Critical' },
];
const BAND_CLASSES = ['band-low', 'band-moderate', 'band-high', 'band-vhigh', 'band-critical'];

const TECHNIQUE_LABEL = {
  urgency: 'Urgency',
  authority: 'False Authority',
  fear: 'Fear',
  scarcity: 'Scarcity',
};

function cvssFromPercent(percent) {
  const value = Number(percent);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(10, Math.round(value) / 10));
}

function severityFor(v) {
  return SEVERITY.find((s) => s.test(v));
}

function node(tag, className, text) {
  const n = document.createElement(tag);
  if (className) n.className = className;
  if (text !== undefined) n.textContent = text;
  return n;
}

let loadingTimers = [];
function clearLoading() {
  loadingTimers.forEach(clearTimeout);
  loadingTimers = [];
}

function renderLoading() {
  clearLoading();
  const box = el('verdict');
  box.textContent = '';
  const card = node('div', 'card loading');
  card.appendChild(node('div', 'k', 'PanshengGuard'));
  card.appendChild(node('div', 'loading-title', 'Analyzing this email…'));
  const bar = node('div', 'scanbar');
  bar.appendChild(node('span'));
  card.appendChild(bar);
  const list = node('ul', 'steps');
  const steps = ['Email content', 'Suspicious phrases', 'Threat intelligence'].map((label) => {
    const li = node('li', 'step');
    li.appendChild(node('i'));
    li.appendChild(node('span', '', label));
    list.appendChild(li);
    return li;
  });
  card.appendChild(list);
  box.appendChild(card);

  steps[0].className = 'step active';
  loadingTimers.push(setTimeout(() => { steps[0].className = 'step done'; steps[1].className = 'step active'; }, 600));
  loadingTimers.push(setTimeout(() => { steps[1].className = 'step done'; steps[2].className = 'step active'; }, 1400));
}

function renderError(message) {
  clearLoading();
  const box = el('verdict');
  box.textContent = '';
  const card = node('div', 'card error');
  card.appendChild(node('div', 'k', 'PanshengGuard'));
  card.appendChild(node('div', 'error-title', 'Could not check this email'));
  card.appendChild(node('div', 'error-msg', message));
  const actions = node('div', 'actions');
  const retry = node('button', 'btn btn-primary', 'Try again');
  retry.addEventListener('click', scan);
  actions.appendChild(retry);
  card.appendChild(actions);
  box.appendChild(card);
}

// Built node by node so nothing returned over the network is parsed as HTML.
function renderVerdict(data) {
  clearLoading();
  const box = el('verdict');
  box.textContent = '';

  const probScore = cvssFromPercent(data.probability);          // API sends a percentage
  const sophScore = cvssFromPercent(data.sophistication_score); // 0-100

  const card = node('div', `card ${severityFor(probScore).cls}`);

  const metric = (label, raw, target) => {
    const block = node('div', 'metric');
    block.appendChild(node('div', 'k', label));
    const line = node('div', 'score');
    const value = node('span', 'score-value', '0.0');
    line.appendChild(value);
    line.appendChild(node('span', 'score-max', '/ 10'));
    block.appendChild(line);
    const sev = node('div', 'band-name', '');
    block.appendChild(sev);
    const meter = node('div', 'meter');
    const cells = [];
    for (let i = 0; i < 10; i += 1) { const c = node('span'); meter.appendChild(c); cells.push(c); }
    block.appendChild(meter);
    block.appendChild(node('div', 'raw', raw));
    return { block, value, sev, cells, target };
  };
  const metrics = [
    metric('Phishing probability', 'How likely it is phishing', probScore),
    metric('Sophistication', 'How convincing it is', sophScore),
  ];
  const row = node('div', 'metrics');
  metrics.forEach((m) => row.appendChild(m.block));
  card.appendChild(row);

  // Detected techniques (the extension endpoint already drops empty ones).
  const detected = Object.keys(data.techniques || {}).filter((t) => Array.isArray(data.techniques[t]) && data.techniques[t].length);
  const det = node('div', 'section');
  det.appendChild(node('div', 'k', 'Detected'));
  const chips = node('div', 'chips');
  if (detected.length) {
    detected.forEach((t, i) => {
      const chip = node('span', `chip tq-${t}`, TECHNIQUE_LABEL[t] || t);
      chip.style.animationDelay = `${250 + i * 130}ms`;
      chips.appendChild(chip);
    });
  } else {
    chips.appendChild(node('span', 'chip none', 'No manipulation techniques'));
  }
  det.appendChild(chips);
  det.appendChild(node('div', 'meta', `Model: ${data.label === 'PHISHING' ? 'Phishing' : 'Legitimate'}`));
  card.appendChild(det);

  if (Array.isArray(data.signals) && data.signals.length) {
    const why = node('div', 'section');
    why.appendChild(node('div', 'k', 'Why'));
    const list = node('ul', 'signals');
    data.signals.forEach((signal) => list.appendChild(node('li', '', signal)));
    why.appendChild(list);
    card.appendChild(why);
  }

  const actions = node('div', 'actions');
  if (data.detail_url) {
    const link = node('a', 'btn btn-primary', 'View full report');
    link.href = data.detail_url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    actions.appendChild(link);
  }
  const again = node('button', 'btn', 'Scan again');
  again.addEventListener('click', () => {
    box.textContent = '';
    el('paste').focus();
    el('paste').select();
  });
  actions.appendChild(again);
  card.appendChild(actions);

  box.appendChild(card);

  // Both scores count up from 0.0 so they read as generated, not printed.
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const paint = (t) => metrics.forEach((m) => {
    const v = Math.round(m.target * t * 10) / 10;
    m.value.textContent = v.toFixed(1);
    m.cells.forEach((c, i) => c.style.setProperty('--f', Math.max(0, Math.min(1, v - i)).toFixed(2)));
    const sev = severityFor(v);
    m.sev.textContent = sev.name;
    BAND_CLASSES.forEach((c) => m.block.classList.remove(c));
    m.block.classList.add(sev.cls);
  });
  if (reduce) { paint(1); return; }
  const start = performance.now();
  const step = () => {
    const p = Math.min(1, (performance.now() - start) / 900);
    paint(1 - Math.pow(1 - p, 3));
    if (p < 1) requestAnimationFrame(step);
  };
  paint(0);
  setTimeout(() => requestAnimationFrame(step), 150);
}

function setStatus(text, kind = '') {
  const node = el('status');
  node.textContent = text;
  node.className = `status ${kind}`;
}

async function load() {
  const { apiBase, token } = await chrome.storage.local.get({
    apiBase: 'http://127.0.0.1:8001',
    token: '',
  });
  el('apiBase').value = apiBase;
  el('token').value = token;

  if (token) {
    test();
  } else {
    el('settings').open = true;
    setStatus('No token saved. Generate one on your profile page and paste it in Connection settings.');
  }
}

async function save() {
  await chrome.storage.local.set({
    apiBase: el('apiBase').value.trim() || 'http://127.0.0.1:8001',
    token: el('token').value.trim(),
  });
  setStatus('Saved.', 'ok');
}

function test() {
  setStatus('Checking…');
  chrome.runtime.sendMessage({ type: 'ping' }, (data) => {
    if (data?.ok) {
      setStatus(`Connected as ${data.user.name} (${data.user.email}).`, 'ok');
    } else {
      setStatus(data?.message || 'Could not reach the server.', 'bad');
    }
  });
}

function scan() {
  const text = el('paste').value.trim();
  if (!text) {
    setStatus('Paste an email first.', 'bad');
    return;
  }

  el('scan').disabled = true;
  el('scan').textContent = 'Analyzing…';
  setStatus('Analyzing…');
  renderLoading();

  chrome.runtime.sendMessage({ type: 'analyze', emailText: text, checkUrls: false }, (data) => {
    el('scan').disabled = false;
    el('scan').textContent = 'Analyze email';

    if (!data?.ok) {
      setStatus(data?.message || 'Analysis failed.', 'bad');
      renderError(data?.message || 'Analysis failed.');
      return;
    }

    setStatus('Analysis complete.', 'ok');
    renderVerdict(data);
  });
}

el('save').addEventListener('click', save);
el('test').addEventListener('click', async () => { await save(); test(); });
el('scan').addEventListener('click', scan);

load();
