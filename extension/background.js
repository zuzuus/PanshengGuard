/**
 * Service worker: the only place that talks to the API.
 *
 * The content script runs inside mail.google.com, so a fetch from there would
 * be a cross-origin request from Google's origin and would be blocked. Requests
 * made here carry the extension's own origin, and because the API host is
 * listed in host_permissions, Chrome allows them without a CORS preflight.
 *
 * Keeping the token here also means it is never exposed to page scripts.
 */

const DEFAULTS = {
  apiBase: 'http://127.0.0.1:8001',
  token: '',
};

async function settings() {
  const stored = await chrome.storage.local.get(DEFAULTS);
  return { ...DEFAULTS, ...stored };
}

/**
 * One call to the Laravel API. Never throws - the caller gets a plain object
 * either way, so a dead server shows a readable message in the banner rather
 * than a silent failure.
 */
async function callApi(path, options = {}) {
  const { apiBase, token } = await settings();

  if (!token) {
    return {
      ok: false,
      error: 'no_token',
      message: 'No API token set. Open the extension popup and paste the token from your profile page.',
    };
  }

  let response;
  try {
    response = await fetch(`${apiBase.replace(/\/+$/, '')}/api/extension${path}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    return {
      ok: false,
      error: 'unreachable',
      message: `Could not reach ${apiBase}. Is the Laravel server running?`,
    };
  }

  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    return {
      ok: false,
      error: 'bad_response',
      message: `The server replied with ${response.status} but not JSON.`,
    };
  }

  if (!response.ok) {
    return {
      ok: false,
      error: data.error || 'request_failed',
      // Laravel sends `message` for both our own errors and validation ones.
      message: data.message || `Request failed with status ${response.status}.`,
      status: response.status,
    };
  }

  return data;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'ping') {
    callApi('/ping').then(sendResponse);
    return true; // keep the channel open for the async reply
  }

  if (message?.type === 'analyze') {
    callApi('/analyze', {
      method: 'POST',
      body: JSON.stringify({
        email_text: message.emailText,
        check_urls: message.checkUrls === true,
      }),
    }).then(sendResponse);
    return true;
  }

  return false;
});
