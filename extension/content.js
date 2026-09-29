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
 * How loud each verdict should be.
 *
 * A single banner size for every outcome trains people to stop reading it. A
 * clean result should be a quiet strip; a critical one should be hard to scroll
 * past. `compact` collapses the reasoning behind a summary line for the two
 * lower tiers, where the detail is rarely what the reader needs.
 */
const SEVERITY = {
  'Critical Risk': { cls: 'pg-critical', compact: false, icon: '✖' },
  'High Risk':     { cls: 'pg-high',     compact: false, icon: '⚠' },
  'Moderate Risk': { cls: 'pg-moderate', compact: true,  icon: '⚠' },
  'Low Risk':      { cls: 'pg-low',      compact: true,  icon: '✓' },
};

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

function renderError(banner, message) {
  banner.className = 'pg-banner pg-error';
  banner.textContent = '';

  const head = document.createElement('div');
  head.className = 'pg-head';
  const title = document.createElement('span');
  title.className = 'pg-verdict';
  title.textContent = 'Could not check this email';
  head.appendChild(title);
  banner.appendChild(head);

  const body = document.createElement('div');
  body.className = 'pg-message';
  body.textContent = message;
  banner.appendChild(body);
}

function renderResult(banner, bodyEl, data) {
  if (!data || !data.ok) {
    clearHighlights(bodyEl);
    renderError(banner, (data && data.message) || 'The extension background worker did not reply.');
    return;
  }

  const severity = SEVERITY[data.risk] || SEVERITY['Moderate Risk'];
  const { count, used } = highlightTechniques(bodyEl, data.techniques);

  banner.className = `pg-banner ${severity.cls}${severity.compact ? ' pg-compact' : ''}`;
  banner.textContent = '';

  // --- headline ---
  const head = document.createElement('div');
  head.className = 'pg-head';

  const icon = document.createElement('span');
  icon.className = 'pg-icon';
  icon.textContent = severity.icon;
  head.appendChild(icon);

  const verdict = document.createElement('span');
  verdict.className = 'pg-verdict';
  verdict.textContent = data.label;
  head.appendChild(verdict);

  const badge = document.createElement('span');
  badge.className = 'pg-badge';
  badge.textContent = data.risk;
  head.appendChild(badge);

  const score = document.createElement('span');
  score.className = 'pg-score';
  score.textContent = `${data.probability}% phishing probability`;
  head.appendChild(score);

  banner.appendChild(head);

  // --- what got marked up, and in which colour ---
  if (count > 0) {
    const legend = document.createElement('div');
    legend.className = 'pg-legend';

    const intro = document.createElement('span');
    intro.className = 'pg-legend-intro';
    intro.textContent = `${count} phrase${count === 1 ? '' : 's'} highlighted below:`;
    legend.appendChild(intro);

    used.forEach((technique) => {
      const chip = document.createElement('span');
      chip.className = `pg-chip ${TECHNIQUE_CLASS[technique]}`;
      chip.textContent = TECHNIQUE_LABEL[technique] || technique;
      legend.appendChild(chip);
    });

    banner.appendChild(legend);
  }

  // --- structural signals ---
  const signals = Array.isArray(data.signals) ? data.signals : [];

  if (signals.length) {
    // Compact tiers hide the reasoning behind a summary line; the loud tiers
    // show it outright, because that is when the reader actually needs it.
    const host = severity.compact ? document.createElement('details') : document.createElement('div');

    if (severity.compact) {
      const summary = document.createElement('summary');
      summary.textContent = `${signals.length} thing${signals.length === 1 ? '' : 's'} worth knowing`;
      host.appendChild(summary);
    }

    const list = document.createElement('ul');
    list.className = 'pg-signals';
    signals.forEach((signal) => {
      const item = document.createElement('li');
      item.textContent = signal;
      list.appendChild(item);
    });
    host.appendChild(list);
    banner.appendChild(host);
  } else {
    const none = document.createElement('p');
    none.className = 'pg-none';
    none.textContent = 'No structural red flags fired on this message.';
    banner.appendChild(none);
  }

  // --- link back to the full report ---
  if (data.detail_url) {
    const link = document.createElement('a');
    link.className = 'pg-link';
    link.href = data.detail_url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View the full report';
    banner.appendChild(link);
  }
}

/* ------------------------------------------------------------------ *
 * Wiring
 * ------------------------------------------------------------------ */

function attach(bodyEl) {
  if (bodyEl.dataset.pgAttached === '1') return;
  bodyEl.dataset.pgAttached = '1';

  const container = closestMatch(bodyEl, SELECTORS.message) || bodyEl.parentElement;
  if (!container) return;

  const banner = document.createElement('div');
  banner.className = 'pg-banner pg-idle';
  banner.textContent = 'Not checked yet.';

  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'pg-button';
  button.textContent = 'Scan with PanshengGuard';

  // Manual rather than automatic on purpose: scanning every message as it
  // opens would send the contents of the whole mailbox to the server, and
  // would burn the per-user rate limit within seconds of scrolling.
  button.addEventListener('click', () => {
    button.disabled = true;
    button.textContent = 'Scanning…';
    clearHighlights(bodyEl);
    banner.className = 'pg-banner pg-idle';
    banner.textContent = 'Checking this email…';

    chrome.runtime.sendMessage(
      { type: 'analyze', emailText: extractEmail(bodyEl), checkUrls: false },
      (data) => {
        button.disabled = false;
        button.textContent = 'Scan again';
        renderResult(banner, bodyEl, data);
      }
    );
  });

  container.prepend(banner);
  container.prepend(button);
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
