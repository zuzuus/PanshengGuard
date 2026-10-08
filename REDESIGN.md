# PanshengGuard UI redesign

Only frontend files changed. These are untouched: FastAPI, the ML model, scoring, preprocessing, VirusTotal, Laravel controllers, routes, models, migrations, config, `background.js`, `manifest.json`, the ports, and the request/response formats.

## Threat score (1–10)
The backend returns `sophistication_score` (0–100). The UI shows it as `ceil(score / 10)`, with a minimum of 1:
1–2 Low · 3–4 Moderate · 5–6 High · 7–8 Very High · 9–10 Critical.
The backend's own `risk` label still appears in the report under *Model details*.

## Laravel (no build step: plain CSS/JS in /public)
- `public/css/app.css`: the design system, with light and dark themes
- `public/js/ui.js`: theme toggle, mobile menu, reveal-on-scroll, button busy state
- `public/js/scanner.js`: scanner animation, phrase highlighting, score reveal
- `resources/views/**`: every page restyled, plus new components (`risk-badge`, `score-tile`, `brand-mark`), partials (`scan-list`, `theme-head`, `ui-script`) and `vendor/pagination/tailwind.blade.php`

## How the scanner works
1. **Home:** the form does the same POST to `/analyze` as before. While that request runs, the scanner shows your text with a moving scan line and a checklist. The last step stays open until the server answers.
2. **Result:** the page replays the scan using only the returned data. Phrases are highlighted as the line passes, then the techniques and the threat-intelligence summary appear, and the score counts up to the real value. The replay lasts about 5 seconds. It has a **Skip** button and is skipped entirely when the browser's reduced-motion setting is on.
3. **Errors:** a failed request (for example, the service is unreachable) shows "Could not check this email" with the backend's message and a **Try again** button.

## Chrome extension
- `content.css`, `popup.html`, `popup.css`: restyled
- `content.js`, `popup.js`: only the rendering functions were replaced. The selectors, `extractEmail`, the `chrome.runtime.sendMessage` calls, settings/storage and the observer wiring are unchanged.

## Run (unchanged)
    cd Piton && python -m uvicorn main:app --reload --port 8000
    cd Laravel/phishing-frontend && php artisan serve --port=8001
Reload the unpacked extension in `chrome://extensions` to pick up the new UI.
