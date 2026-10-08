/**
 * Runs inside Gmail. Finds the open message, adds a scan button to it, marks up
 * the words that triggered the verdict, and draws the result banner in place.
 *
 * Gmail renders everything client-side and reuses DOM nodes as you move between
 * messages, so there is no page load to hook. This watches for the message body
 * appearing and attaches once per message.
 *
 * The selectors below are Gmail's obfuscated class names. They have been stable
 * for years but are not a public API, and Google can change them without notice
 * - hence SELECTORS holding several candidates for each thing, and the paste box
 * in the popup as a fallback that does not depend on the DOM at all.
 */

const SELECTORS = {
  // Message body. a3s is the long-standing class on the rendered mail body.
  body: ['div.a3s.aiL', 'div.a3s', 'div[data-message-id] div.ii'],
  // Subject line of the open conversation.
  subject: ['h2.hP', 'div.ha h2', '[data-thread-perm-id] h2'],
  // The container a whole message sits in, used as the anchor for the banner.
  message: ['div.adn.ads', 'div[data-message-id]', 'div.gs'],
};

/**
 * Score presentation — CVSS-style, matching the website report.
 *
 * Two scores, both straight from the API and shown on one decimal out of 10:
 *   phishing probability  = probability (%) / 10
 *   sophistication score  = sophistication_score (0-100) / 10
 * with the CVSS v3 severity bands: None 0.0 · Low 0.1-3.9 · Medium 4.0-6.9 ·
 * High 7.0-8.9 · Critical 9.0-10.0. Display conversion only; scoring is
 * untouched.
 *
 * Banner weight still follows severity (of the phishing probability): Low or
 * None is a quiet card with the reasoning tucked behind a summary line.
 */
const SEVERITY = [
  { test: (v) => v <= 0, cls: 'pg-band-low',      name: 'None',     compact: true  },
  { test: (v) => v < 4,  cls: 'pg-band-low',      name: 'Low',      compact: true  },
  { test: (v) => v < 7,  cls: 'pg-band-moderate', name: 'Medium',   compact: false },
  { test: (v) => v < 9,  cls: 'pg-band-high',     name: 'High',     compact: false },
  { test: () => true,    cls: 'pg-band-critical', name: 'Critical', compact: false },
];
const BAND_CLASSES = ['pg-band-low', 'pg-band-moderate', 'pg-band-high', 'pg-band-vhigh', 'pg-band-critical'];

function cvssFromPercent(percent) {
  const value = Number(percent);
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(10, Math.round(value) / 10));
}

function severityFor(v) {
  return SEVERITY.find((s) => s.test(v));
}

const SVG_NS = 'http://www.w3.org/2000/svg';

/** PanshengGuard mark, built as DOM nodes (no innerHTML inside Gmail). */
function brandMark() {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  [
    'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z',
    'M8 12h8',
  ].forEach((d) => {
    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d', d);
    svg.appendChild(path);
  });
  return svg;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const TECHNIQUE_CLASS = {
  urgency: 'pg-hl-urgency',
  authority: 'pg-hl-authority',
  fear: 'pg-hl-fear',
  scarcity: 'pg-hl-scarcity',
};

const TECHNIQUE_LABEL = {
  urgency: 'Urgency',
  authority: 'False authority',
  fear: 'Fear',
  scarcity: 'Scarcity',
};

function firstMatch(root, candidates) {
  for (const selector of candidates) {
    const el = root.querySelector(selector);
    if (el) return el;
  }
  return null;
}

function closestMatch(el, candidates) {
  for (const selector of candidates) {
    const found = el.closest(selector);
    if (found) return found;
  }
  return null;
}

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Pull the text the detector needs: subject line plus body, the same shape a
 * user would paste into the website.
 */
function extractEmail(bodyEl) {
  const subjectEl = firstMatch(document, SELECTORS.subject);
  const subject = subjectEl ? subjectEl.innerText.trim() : '';
  const body = bodyEl.innerText.trim();
  return subject ? `${subject}\n\n${body}` : body;
}

/* ------------------------------------------------------------------ *
 * Highlighting
 * ------------------------------------------------------------------ */

function clearHighlights(root) {
  root.querySelectorAll('mark.pg-hl').forEach((mark) => {
    const parent = mark.parentNode;
    if (!parent) return;
    parent.replaceChild(document.createTextNode(mark.textContent), mark);
    parent.normalize();
  });
}

/**
 * Wrap every whole-word occurrence of `regex` in the message body.
 *
 * Only text nodes are touched, and the replacement keeps the surrounding text
 * intact, so Gmail's own structure and event handlers are left alone. Nodes
 * already inside a highlight, or inside our own banner, are skipped so a second
 * scan cannot nest marks inside marks.
 */
function markMatches(root, regex, cssClass, label) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (parent.closest('mark.pg-hl, .pg-banner, .pg-button, script, style')) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const targets = [];
  let node;
  while ((node = walker.nextNode())) targets.push(node);

  let count = 0;

  for (const textNode of targets) {
    const text = textNode.nodeValue;
    regex.lastIndex = 0;
    if (!regex.test(text)) continue;

    regex.lastIndex = 0;
    const fragment = document.createDocumentFragment();
    let last = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match[0].length === 0) { regex.lastIndex += 1; continue; }

      if (match.index > last) {
        fragment.appendChild(document.createTextNode(text.slice(last, match.index)));
      }

      const mark = document.createElement('mark');
      mark.className = `pg-hl ${cssClass}`;
      mark.title = `${label} — flagged by PanshengGuard`;
      mark.textContent = match[0];
      fragment.appendChild(mark);

      last = match.index + match[0].length;
      count += 1;
    }

    if (last < text.length) {
      fragment.appendChild(document.createTextNode(text.slice(last)));
    }

    textNode.parentNode.replaceChild(fragment, textNode);
  }

  return count;
}

/**
 * Mark up the words that produced the verdict.
 *
 * The rule matches the scoring service exactly: a keyword has to start a word,
 * but may run on at the end. So "expire" marks the whole of "expires", while
 * "bank" does not match inside "Maybank" and "now" does not match inside
 * "know".
 *
 * Keeping the two in step matters - when they disagreed, the banner would name
 * a technique with nothing highlighted underneath it, which reads as a broken
 * feature rather than a correct refusal.
 */
function highlightTechniques(root, techniques) {
  clearHighlights(root);
  if (!techniques || typeof techniques !== 'object') return { count: 0, used: [] };

  let count = 0;
  const used = [];

  for (const [technique, terms] of Object.entries(techniques)) {
    const cssClass = TECHNIQUE_CLASS[technique];
    if (!cssClass || !Array.isArray(terms) || terms.length === 0) continue;

    // Longest first, so "24 hours" wins over "hours" and the phrase is marked
    // as one unit rather than being broken in half.
    const pattern = [...terms]
      .sort((a, b) => b.length - a.length)
      .map(escapeRegex)
      .join('|');

    if (!pattern) continue;

    // \w* on the end so the whole inflected word is highlighted - "expires"
    // is marked in full rather than leaving a stray "s" outside the box.
    const regex = new RegExp(`\\b(?:${pattern})\\w*`, 'gi');
    const marked = markMatches(root, regex, cssClass, TECHNIQUE_LABEL[technique] || technique);

    if (marked > 0) {
      count += marked;
      used.push(technique);
    }
  }

  return { count, used };
}

/* ------------------------------------------------------------------ *
 * Banner
 * ------------------------------------------------------------------ */

function stopTimers(banner) {
  (banner._pgTimers || []).forEach(clearTimeout);
  banner._pgTimers = [];
}

function bannerTop(statusText) {
  const top = el('div', 'pg-top');
  const brand = el('span', 'pg-brand');
  const mark = el('span', 'pg-mark');
  mark.appendChild(brandMark());
  brand.appendChild(mark);
  brand.appendChild(el('span', 'pg-brand-name', 'PanshengGuard'));
  top.appendChild(brand);
  top.appendChild(el('span', 'pg-status', statusText));
  return top;
}

/**
 * Loading state, shown while the real request is in flight. The steps only
 * advance visually; the last one stays open until the answer arrives.
 */
function renderLoading(banner) {
  stopTimers(banner);
  banner.className = 'pg-banner pg-loading';
  banner.textContent = '';

  banner.appendChild(bannerTop('Analyzing'));
  banner.appendChild(el('div', 'pg-loading-title', 'Analyzing this email…'));

  const bar = el('div', 'pg-scanbar');
  bar.appendChild(el('span', 'pg-scanbar-line'));
  banner.appendChild(bar);

  const list = el('ul', 'pg-steps');
  const steps = ['Email content', 'Suspicious phrases', 'Threat intelligence'].map((label) => {
    const item = el('li', 'pg-step');
    item.appendChild(el('span', 'pg-step-dot'));
    item.appendChild(el('span', 'pg-step-label', label));
    list.appendChild(item);
    return item;
  });
  banner.appendChild(list);

  const set = (item, state) => { item.className = `pg-step ${state ? `is-${state}` : ''}`; };
  set(steps[0], 'active');
  banner._pgTimers = [
    setTimeout(() => { set(steps[0], 'done'); set(steps[1], 'active'); }, 600),
    setTimeout(() => { set(steps[1], 'done'); set(steps[2], 'active'); }, 1400),
  ];
}

function renderError(banner, message) {
  stopTimers(banner);
  banner.className = 'pg-banner pg-error';
  banner.textContent = '';

  banner.appendChild(bannerTop('Not checked'));

  const title = el('div', 'pg-error-title', 'Could not check this email');
  banner.appendChild(title);

  banner.appendChild(el('div', 'pg-message', message));

  const actions = el('div', 'pg-actions');
  const retry = el('button', 'pg-btn pg-btn-primary', 'Try again');
  retry.type = 'button';
  retry.addEventListener('click', () => { if (banner._pgScanButton) banner._pgScanButton.click(); });
  actions.appendChild(retry);
  banner.appendChild(actions);
}

/**
 * One CVSS-style score block: kicker, "7.6 / 10", severity and a 10-segment
 * bar that fills continuously (6.1 = six segments and a tenth).
 */
function scoreBlock(label, sub) {
  const block = el('div', 'pg-metric');
  block.appendChild(el('div', 'pg-kicker', label));
  const line = el('div', 'pg-score');
  const value = el('span', 'pg-score-value', '0.0');
  line.appendChild(value);
  line.appendChild(el('span', 'pg-score-max', '/ 10'));
  block.appendChild(line);
  const sev = el('div', 'pg-band', '');
  block.appendChild(sev);
  const meter = el('div', 'pg-meter');
  const cells = [];
  for (let i = 0; i < 10; i += 1) {
    const cell = el('span');
    meter.appendChild(cell);
    cells.push(cell);
  }
  block.appendChild(meter);
  block.appendChild(el('div', 'pg-raw', sub));
  return { block, value, sev, cells };
}

/** Count both scores up from 0.0 so they read as generated, not printed. */
function animateScores(banner, metrics) {
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const paint = (t) => {
    metrics.forEach((m) => {
      const v = Math.round(m.target * t * 10) / 10;
      m.value.textContent = v.toFixed(1);
      m.cells.forEach((cell, i) => cell.style.setProperty('--f', Math.max(0, Math.min(1, v - i)).toFixed(2)));
      const sev = severityFor(v);
      m.sev.textContent = sev.name;
      BAND_CLASSES.forEach((c) => m.block.classList.remove(c));
      m.block.classList.add(sev.cls);
    });
  };
  if (reduce) { paint(1); return; }

  const start = performance.now();
  const step = () => {
    const p = Math.min(1, (performance.now() - start) / 900);
    paint(1 - Math.pow(1 - p, 3));
    if (p < 1) banner._pgTimers.push(setTimeout(step, 16));
  };
  paint(0);
  banner._pgTimers.push(setTimeout(step, 120));
}

function renderResult(banner, bodyEl, data) {
  stopTimers(banner);

  if (!data || !data.ok) {
    clearHighlights(bodyEl);
    renderError(banner, (data && data.message) || 'The extension background worker did not reply.');
    return;
  }

  const probScore = cvssFromPercent(data.probability);          // API sends a percentage
  const sophScore = cvssFromPercent(data.sophistication_score); // 0-100
  const band = severityFor(probScore);
  const { count, used } = highlightTechniques(bodyEl, data.techniques);

  // Light the highlighted phrases one after another, top to bottom.
  bodyEl.querySelectorAll('mark.pg-hl').forEach((mark, i) => {
    mark.style.animationDelay = `${Math.min(i, 12) * 90}ms`;
    mark.classList.add('pg-hl-reveal');
  });

  banner.className = `pg-banner ${band.cls}${band.compact ? ' pg-compact' : ''}`;
  banner.textContent = '';

  banner.appendChild(bannerTop('Threat assessment'));

  // --- score + detected ---
  const main = el('div', 'pg-main');

  const scores = el('div', 'pg-scores');
  const prob = scoreBlock('Phishing probability', 'How likely it is phishing');
  const soph = scoreBlock('Sophistication', 'How convincing the tactics are');
  scores.appendChild(prob.block);
  scores.appendChild(soph.block);
  main.appendChild(scores);

  const detectCol = el('div', 'pg-detect-col');
  detectCol.appendChild(el('div', 'pg-kicker', 'Detected'));
  const chips = el('div', 'pg-chips');
  const techniquesFound = used.length
    ? used
    : Object.keys(data.techniques || {}).filter((t) => TECHNIQUE_CLASS[t]);
  if (techniquesFound.length) {
    techniquesFound.forEach((technique, i) => {
      const chip = el('span', `pg-chip ${TECHNIQUE_CLASS[technique]}`, TECHNIQUE_LABEL[technique] || technique);
      chip.style.animationDelay = `${300 + i * 140}ms`;
      chips.appendChild(chip);
    });
  } else {
    chips.appendChild(el('span', 'pg-chip pg-chip-none', 'No manipulation techniques'));
  }
  detectCol.appendChild(chips);

  const meta = el('div', 'pg-meta');
  meta.textContent = count > 0
    ? `${count} phrase${count === 1 ? '' : 's'} highlighted in the message · Model: ${data.label === 'PHISHING' ? 'Phishing' : 'Legitimate'}`
    : `Model: ${data.label === 'PHISHING' ? 'Phishing' : 'Legitimate'}`;
  detectCol.appendChild(meta);
  main.appendChild(detectCol);

  banner.appendChild(main);

  // --- structural signals ---
  const signals = Array.isArray(data.signals) ? data.signals : [];
  if (signals.length) {
    // Quiet bands hide the reasoning behind a summary line; the loud bands
    // show it outright, because that is when the reader needs it.
    const host = band.compact ? document.createElement('details') : el('div', 'pg-signals-wrap');
    if (band.compact) {
      host.appendChild(el('summary', '', `${signals.length} thing${signals.length === 1 ? '' : 's'} worth knowing`));
    } else {
      host.appendChild(el('div', 'pg-kicker', 'Why'));
    }
    const list = el('ul', 'pg-signals');
    signals.forEach((signal) => list.appendChild(el('li', '', signal)));
    host.appendChild(list);
    banner.appendChild(host);
  } else {
    banner.appendChild(el('p', 'pg-none', 'No structural red flags fired on this message.'));
  }

  // --- actions ---
  const actions = el('div', 'pg-actions');
  if (data.detail_url) {
    const link = el('a', 'pg-btn pg-btn-primary', 'View full report');
    link.href = data.detail_url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    actions.appendChild(link);
  }
  const again = el('button', 'pg-btn', 'Scan again');
  again.type = 'button';
  again.addEventListener('click', () => { if (banner._pgScanButton) banner._pgScanButton.click(); });
  actions.appendChild(again);
  banner.appendChild(actions);

  animateScores(banner, [
    { ...prob, target: probScore },
    { ...soph, target: sophScore },
  ]);
}

/* ------------------------------------------------------------------ *
 * Wiring
 * ------------------------------------------------------------------ */

/** False once the extension has been reloaded under this open tab. */
function extensionAlive() {
  try {
    return Boolean(chrome.runtime && chrome.runtime.id);
  } catch (err) {
    return false;
  }
}

function showReloadNotice(banner, button) {
  stopTimers(banner);
  button.disabled = false;
  button.textContent = 'Scan with PanshengGuard';
  renderError(banner, 'PanshengGuard was updated or reloaded. Refresh this Gmail tab (F5), then scan again.');
}

function attach(bodyEl) {
  if (bodyEl.dataset.pgAttached === '1') return;
  bodyEl.dataset.pgAttached = '1';

  const container = closestMatch(bodyEl, SELECTORS.message) || bodyEl.parentElement;
  if (!container) return;

  const banner = document.createElement('div');
  banner.className = 'pg-banner pg-idle';
  banner.textContent = 'Not checked yet. Scan this email to see its threat score.';

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'pg-button';
  button.textContent = 'Scan with PanshengGuard';
  banner._pgScanButton = button; // lets "Scan again" / "Try again" reuse this button

  // Manual rather than automatic on purpose: scanning every message as it
  // opens would send the contents of the whole mailbox to the server, and
  // would burn the per-user rate limit within seconds of scrolling.
  button.addEventListener('click', () => {
    // After the extension is reloaded or updated in chrome://extensions, the
    // copy of this script already running in an open Gmail tab is cut off
    // from it ("Extension context invalidated"). Say so plainly instead of
    // throwing; refreshing the tab loads the new version.
    if (!extensionAlive()) {
      showReloadNotice(banner, button);
      return;
    }

    button.disabled = true;
    button.textContent = 'Scanning…';
    clearHighlights(bodyEl);
    renderLoading(banner);

    try {
      chrome.runtime.sendMessage(
        { type: 'analyze', emailText: extractEmail(bodyEl), checkUrls: false },
        (data) => {
          button.disabled = false;
          button.textContent = 'Scan again';
          renderResult(banner, bodyEl, data);
        }
      );
    } catch (err) {
      showReloadNotice(banner, button);
    }
  });

  // Insert directly above the message body. Gmail's message container is a
  // multi-column flex row (avatar | content); prepending to it squeezed the
  // banner into a sliver beside the avatar. The body's own parent is the
  // content column, so the banner gets the full reading width.
  const host = bodyEl.parentElement || container;
  if (host === container) {
    container.prepend(banner);
    container.prepend(button);
  } else {
    host.insertBefore(button, bodyEl);
    host.insertBefore(banner, bodyEl);
  }
}

/**
 * Gmail swaps message bodies in and out without a navigation event, so watch
 * the DOM rather than running once at load.
 */
const observer = new MutationObserver(() => {
  const bodyEl = firstMatch(document, SELECTORS.body);
  if (bodyEl) attach(bodyEl);
});

observer.observe(document.body, { childList: true, subtree: true });

// In case a message is already open when the script loads.
const existing = firstMatch(document, SELECTORS.body);
if (existing) attach(existing);
