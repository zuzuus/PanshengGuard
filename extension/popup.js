/**
 * Popup: settings, a connection test, and a paste box.
 *
 * The paste box is the deliberate fallback. Gmail's class names are not a
 * public API, so if Google changes them the in-page button stops appearing -
 * and the extension would be useless at exactly the wrong moment. This path
 * touches no Gmail DOM at all, so it keeps working regardless.
 */

const el = (id) => document.getElementById(id);

const RISK_COLOURS = {
  'Low Risk': '#5BC489',
  'Moderate Risk': '#F0C040',
  'High Risk': '#FF8A5C',
  'Critical Risk': '#E8512B',
};

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
    setStatus('No token saved. Generate one on your profile page and paste it above.');
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
  setStatus('Analysing…');
  el('verdict').style.display = 'none';

  chrome.runtime.sendMessage({ type: 'analyze', emailText: text, checkUrls: false }, (data) => {
    el('scan').disabled = false;

    if (!data?.ok) {
      setStatus(data?.message || 'Analysis failed.', 'bad');
      return;
    }

    setStatus('Done.', 'ok');

    const box = el('verdict');
    box.style.borderLeftColor = RISK_COLOURS[data.risk] || '#939CAD';
    box.style.display = 'block';

    // Built node by node so nothing returned over the network is parsed as HTML.
    box.textContent = '';

    const heading = document.createElement('h2');
    heading.textContent = `${data.label} — ${data.risk}`;
    heading.style.color = RISK_COLOURS[data.risk] || '#F5F1E8';
    box.appendChild(heading);

    const score = document.createElement('div');
    score.textContent = `${data.probability}% phishing probability`;
    score.style.color = '#939CAD';
    score.style.fontSize = '12px';
    box.appendChild(score);

    if (Array.isArray(data.signals) && data.signals.length) {
      const list = document.createElement('ul');
      data.signals.forEach((signal) => {
        const item = document.createElement('li');
        item.textContent = signal;
        list.appendChild(item);
      });
      box.appendChild(list);
    }

    if (data.detail_url) {
      const link = document.createElement('a');
      link.href = data.detail_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'View the full report';
      box.appendChild(document.createElement('br'));
      box.appendChild(link);
    }
  });
}

el('save').addEventListener('click', save);
el('test').addEventListener('click', async () => { await save(); test(); });
el('scan').addEventListener('click', scan);

load();
