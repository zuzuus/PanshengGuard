/**
 * PanshengGuard — scanner visualisation.
 *
 * FRONTEND ONLY. Nothing in this file talks to the server, changes what is
 * submitted, or produces analysis data:
 *
 *  - Intake scanner (home page): the form still performs the same ordinary
 *    POST to /analyze. While that real request is in flight, the scanner shows
 *    the user's own text with a moving scan line and a progress checklist.
 *    The last step stays open until the server's answer arrives.
 *
 *  - Result scanner (result + full report): replays the analysis using ONLY
 *    the data the server already rendered into the page — the matched
 *    technique terms, the VirusTotal summary and the 1–10 score. Phrase
 *    highlighting uses the same matching rule as the browser extension.
 *
 * Animation adapts to the reader: prefers-reduced-motion jumps straight to
 * the final state, and a Skip control is always available during replay.
 */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var TECHNIQUE_LABEL = {
        urgency: 'URGENCY',
        authority: 'FALSE AUTHORITY',
        fear: 'FEAR',
        scarcity: 'SCARCITY'
    };

    var BANDS = [
        { max: 2,  cls: 'band-low' },
        { max: 4,  cls: 'band-moderate' },
        { max: 6,  cls: 'band-high' },
        { max: 8,  cls: 'band-vhigh' },
        { max: 10, cls: 'band-critical' }
    ];

    function bandClass(score) {
        for (var i = 0; i < BANDS.length; i++) {
            if (score <= BANDS[i].max) return BANDS[i].cls;
        }
        return 'band-critical';
    }

    function setBand(el, score) {
        BANDS.forEach(function (b) { el.classList.remove(b.cls); });
        el.classList.add(bandClass(score));
    }

    function escapeRegex(text) {
        return String(text).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }

    /* ------------------------------------------------------------------
     * Highlighting — identical rule to the extension's content.js:
     * a term must start a word but may run on at the end ("expire" marks
     * all of "expires"), longest terms first so phrases stay whole.
     * ------------------------------------------------------------------ */
    function highlight(root, techniques) {
        var marks = [];
        if (!root || !techniques || typeof techniques !== 'object') return marks;

        Object.keys(techniques).forEach(function (technique) {
            var terms = techniques[technique];
            if (!Array.isArray(terms) || !terms.length) return;

            var pattern = terms.slice()
                .sort(function (a, b) { return b.length - a.length; })
                .map(escapeRegex)
                .join('|');
            if (!pattern) return;

            var regex = new RegExp('\\b(?:' + pattern + ')\\w*', 'gi');
            var label = TECHNIQUE_LABEL[technique] || technique.toUpperCase();

            var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
                acceptNode: function (node) {
                    if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                    if (node.parentElement && node.parentElement.closest('mark.hl')) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            });

            var nodes = [];
            var n;
            while ((n = walker.nextNode())) nodes.push(n);

            nodes.forEach(function (textNode) {
                var text = textNode.nodeValue;
                regex.lastIndex = 0;
                if (!regex.test(text)) return;
                regex.lastIndex = 0;

                var frag = document.createDocumentFragment();
                var last = 0;
                var m;
                while ((m = regex.exec(text)) !== null) {
                    if (m[0].length === 0) { regex.lastIndex += 1; continue; }
                    if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));

                    var mark = document.createElement('mark');
                    mark.className = 'hl tq-' + technique;
                    mark.setAttribute('data-label', label);
                    mark.title = label.charAt(0) + label.slice(1).toLowerCase() + ' — flagged by PanshengGuard';
                    mark.textContent = m[0];
                    frag.appendChild(mark);
                    marks.push(mark);

                    last = m.index + m[0].length;
                }
                if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
                textNode.parentNode.replaceChild(frag, textNode);
            });
        });

        // Document order, so the scan line lights them top to bottom.
        marks.sort(function (a, b) {
            return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
        });
        return marks;
    }

    /* ------------------------------------------------------------------
     * Small timeline helper so "Skip" can cancel everything at once.
     * ------------------------------------------------------------------ */
    function Timeline() {
        this.timers = [];
        this.frames = [];
        this.cancelled = false;
    }
    Timeline.prototype.wait = function (ms) {
        var self = this;
        return new Promise(function (resolve) {
            if (self.cancelled) return;
            self.timers.push(setTimeout(function () { if (!self.cancelled) resolve(); }, ms));
        });
    };
    Timeline.prototype.frame = function (fn) {
        if (this.cancelled) return;
        this.frames.push(requestAnimationFrame(fn));
    };
    Timeline.prototype.cancel = function () {
        this.cancelled = true;
        this.timers.forEach(clearTimeout);
        this.frames.forEach(cancelAnimationFrame);
    };

    function stageSet(stageEl, state) {
        if (!stageEl) return;
        stageEl.classList.remove('is-active', 'is-done');
        if (state) stageEl.classList.add('is-' + state);
    }

    function setStatus(scanner, mode, text) {
        var pill = scanner.querySelector('[data-scan-status]');
        var label = scanner.querySelector('[data-scan-status-text]');
        if (pill) {
            pill.classList.remove('is-live', 'is-done', 'is-error');
            if (mode) pill.classList.add('is-' + mode);
        }
        if (label) label.textContent = text;
    }

    function setTitle(scanner, text) {
        var t = scanner.querySelector('[data-scan-title]');
        if (t) t.textContent = text;
    }

    /* ==================================================================
     * Intake scanner (home page)
     * ================================================================== */
    function initIntake(scanner) {
        var form = scanner.querySelector('#scanForm');
        var textarea = scanner.querySelector('textarea[name="email_text"]');
        if (!form || !textarea) return;

        var counter = scanner.querySelector('[data-char-count]');
        var preview = scanner.querySelector('[data-preview]');
        var doc = scanner.querySelector('[data-email-doc]');
        var submit = scanner.querySelector('[data-submit]');
        var submitLabel = scanner.querySelector('[data-submit-label]');
        var stages = {};
        scanner.querySelectorAll('[data-live-stages] [data-stage]').forEach(function (el) {
            stages[el.getAttribute('data-stage')] = el;
        });
        var intelDesc = scanner.querySelector('[data-intel-desc]');
        var originalSubmit = submit ? submit.innerHTML : '';
        var timeline = null;

        function updateCount() {
            if (!counter) return;
            var n = textarea.value.length;
            counter.textContent = n.toLocaleString() + (n === 1 ? ' character' : ' characters');
        }
        textarea.addEventListener('input', updateCount);
        updateCount();

        function setState(state) {
            scanner.classList.remove('is-idle', 'is-analyzing', 'is-error');
            scanner.classList.add('is-' + state);
        }

        // Sample email: fills the box only. The user still presses Analyze,
        // and the real service produces the real result.
        var sampleBtn = scanner.querySelector('[data-sample]');
        if (sampleBtn) {
            sampleBtn.addEventListener('click', function () {
                textarea.value = [
                    'Urgent Account Verification Required',
                    '',
                    'From: Security Department <security@example.com>',
                    '',
                    'Dear Customer,',
                    '',
                    'Your account requires immediate verification. Our Security Department has detected unauthorized activity on your account.',
                    '',
                    'Please verify your account before the deadline. If you do not verify immediately, your account will be suspended and you will lose access to your funds.',
                    '',
                    'This is your final warning. You have 24 hours to confirm your password and TAC number using the secure link below:',
                    'http://secure-verify-account.example.com/login',
                    '',
                    'Security Department',
                    'Account Services'
                ].join('\n');
                updateCount();
                textarea.focus();
                textarea.setSelectionRange(0, 0);
                textarea.scrollTop = 0;
            });
        }

        // "Analyze email" in the hero scrolls here; put the cursor in the box.
        document.querySelectorAll('[data-focus-scanner]').forEach(function (link) {
            link.addEventListener('click', function () {
                setTimeout(function () { textarea.focus({ preventScroll: true }); }, reduceMotion ? 0 : 550);
            });
        });

        var editBtn = scanner.querySelector('[data-edit-email]');
        if (editBtn) {
            editBtn.addEventListener('click', function () {
                setState('idle');
                setTitle(scanner, 'Analyze an email');
                setStatus(scanner, '', 'Ready');
                textarea.focus();
            });
        }

        // The real submission. Default behaviour is NOT prevented: the browser
        // posts the form exactly as before; this only changes what is shown.
        form.addEventListener('submit', function (e) {
            if (form.dataset.submitting === '1') { e.preventDefault(); return; }
            if (!textarea.value.trim()) return; // let the server's validation speak
            form.dataset.submitting = '1';

            if (preview) preview.textContent = textarea.value.trim();
            setState('analyzing');
            setTitle(scanner, 'Analyzing email');
            setStatus(scanner, 'live', 'Analyzing');

            if (submit) {
                submit.disabled = true;
                submit.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span><span>Analyzing…</span>';
            }

            if (doc) doc.style.setProperty('--sweep-h', doc.clientHeight + 'px');

            Object.keys(stages).forEach(function (k) { stageSet(stages[k], null); });

            timeline = new Timeline();
            var tl = timeline;
            stageSet(stages.content, 'active');
            tl.wait(700).then(function () {
                stageSet(stages.content, 'done');
                stageSet(stages.phrases, 'active');
                setTitle(scanner, 'Checking email content');
                return tl.wait(1000);
            }).then(function () {
                stageSet(stages.phrases, 'done');
                stageSet(stages.intel, 'active');
                setTitle(scanner, 'Detecting suspicious phrases');
                return tl.wait(1800);
            }).then(function () {
                setTitle(scanner, 'Checking threat intelligence');
                return tl.wait(4000);
            }).then(function () {
                // Honest about long waits: VirusTotal lookups can take a while.
                if (intelDesc) intelDesc.textContent = 'Still working — link checks can take several seconds.';
            });
        });

        // Coming back with the browser's Back button restores a frozen page.
        window.addEventListener('pageshow', function (e) {
            if (!e.persisted) return;
            if (timeline) timeline.cancel();
            form.dataset.submitting = '';
            setState('idle');
            setTitle(scanner, 'Analyze an email');
            setStatus(scanner, '', 'Ready');
            if (submit) { submit.disabled = false; submit.innerHTML = originalSubmit; }
            if (intelDesc) intelDesc.textContent = 'Waiting for the analysis service.';
        });

        // An error came back from the server: put focus on the recovery action.
        if (scanner.classList.contains('is-error')) {
            var retry = scanner.querySelector('[data-when~="error"] .btn-primary');
            if (retry) setTimeout(function () { retry.focus({ preventScroll: true }); }, 100);
        }
    }

    /* ==================================================================
     * Result scanner (result page + full report)
     * ================================================================== */
    function initResult(scanner) {
        var textEl = scanner.querySelector('[data-email-text]');
        var techniques = {};
        try { techniques = JSON.parse((textEl && textEl.getAttribute('data-techniques')) || '{}'); } catch (e) { techniques = {}; }
        if (Array.isArray(techniques)) techniques = {};

        var marks = highlight(textEl, techniques);

        var countEl = scanner.querySelector('[data-phrase-count]');
        if (countEl && marks.length) countEl.textContent = plural(marks.length, 'phrase', 'phrases') + ' highlighted';

        // Two CVSS-style scores (0.0–10.0), rendered by the server from the
        // API's probability and sophistication. The animation only counts up
        // to those exact values.
        var metrics = Array.prototype.map.call(scanner.querySelectorAll('[data-cvss]'), function (el) {
            return {
                el: el,
                target: parseFloat(el.getAttribute('data-cvss')) || 0,
                value: el.querySelector('[data-cvss-value]'),
                sev: el.querySelector('[data-cvss-sev]'),
                cells: Array.prototype.slice.call(el.querySelectorAll('[data-meter] span')),
                primary: el.hasAttribute('data-primary')
            };
        });

        function severity(v) {
            if (v <= 0) return ['band-low', 'None'];
            if (v < 4) return ['band-low', 'Low'];
            if (v < 7) return ['band-moderate', 'Medium'];
            if (v < 9) return ['band-high', 'High'];
            return ['band-critical', 'Critical'];
        }
        function setBandClass(el, cls) {
            BANDS.forEach(function (b) { el.classList.remove(b.cls); });
            el.classList.add(cls);
        }

        // t runs 0 → 1; every metric is painted at that fraction of its value.
        function paintScore(t) {
            metrics.forEach(function (m) {
                var v = Math.round(m.target * t * 10) / 10;
                if (m.value) m.value.textContent = v.toFixed(1);
                m.cells.forEach(function (c, i) {
                    c.style.setProperty('--f', Math.max(0, Math.min(1, v - i)).toFixed(2));
                });
                var sv = severity(v);
                setBandClass(m.el, sv[0]);
                if (m.sev) m.sev.textContent = sv[1];
                if (m.primary) setBandClass(scanner, sv[0]);
            });
        }

        var animate = scanner.getAttribute('data-animate') === '1' && !reduceMotion;

        if (!animate) {
            // Stored report: a short count-up so the numbers still read as
            // generated rather than printed.
            if (!reduceMotion && metrics.length) {
                var start = null;
                var count = function (ts) {
                    if (start === null) start = ts;
                    var p = Math.min(1, (ts - start) / 700);
                    paintScore(1 - Math.pow(1 - p, 3));
                    if (p < 1) requestAnimationFrame(count);
                };
                paintScore(0);
                requestAnimationFrame(count);
            }
            return;
        }

        replay(scanner, textEl, marks, paintScore);
    }

    function replay(scanner, textEl, marks, paintScore) {
        var tl = new Timeline();
        var doc = scanner.querySelector('[data-email-doc]');
        var line = scanner.querySelector('.scanline');
        var progress = scanner.querySelector('[data-assess-progress]');
        var skip = scanner.querySelector('[data-skip]');
        var phraseDesc = scanner.querySelector('[data-phrase-desc]');
        var originalPhraseDesc = phraseDesc ? phraseDesc.textContent : '';
        var stages = {};
        scanner.querySelectorAll('[data-stage]').forEach(function (el) {
            stages[el.getAttribute('data-stage')] = el;
        });
        var reveals = {
            manipulation: Array.prototype.slice.call(scanner.querySelectorAll('[data-stage="manipulation"] [data-reveal]')),
            intel: Array.prototype.slice.call(scanner.querySelectorAll('[data-stage="intel"] [data-reveal]'))
        };
        var finished = false;

        // ---- set the starting frame ------------------------------------
        scanner.classList.remove('is-result');
        scanner.classList.add('is-replaying');
        setStatus(scanner, 'live', 'Analyzing');
        setTitle(scanner, 'Analyzing email');
        if (skip) skip.hidden = false;

        Object.keys(stages).forEach(function (k) { stageSet(stages[k], null); });
        stageSet(stages.content, 'done');
        reveals.manipulation.concat(reveals.intel).forEach(function (el) { el.classList.add('is-hidden'); });
        marks.forEach(function (m) { m.classList.add('is-pending'); });
        if (phraseDesc) phraseDesc.textContent = 'Reading the message…';

        function finish(animated) {
            if (finished) return;
            finished = true;
            tl.cancel();

            Object.keys(stages).forEach(function (k) { stageSet(stages[k], 'done'); });
            reveals.manipulation.concat(reveals.intel).forEach(function (el) { el.classList.remove('is-hidden'); });
            marks.forEach(function (m) { m.classList.remove('is-pending'); if (!animated) m.classList.remove('is-lit'); });
            if (phraseDesc) phraseDesc.textContent = originalPhraseDesc;
            if (line) { line.style.transition = 'opacity .4s'; line.style.opacity = '0'; }
            paintScore(1);

            // Collapse the progress list so the assessment takes its place.
            if (progress && animated) {
                progress.style.maxHeight = progress.scrollHeight + 'px';
                void progress.offsetHeight;
                progress.style.maxHeight = '0px';
            }

            scanner.classList.remove('is-replaying', 'is-scoring');
            scanner.classList.add('is-result');
            setTitle(scanner, 'Threat assessment');
            setStatus(scanner, 'done', 'Complete');
            if (skip) skip.hidden = true;
        }

        if (skip) skip.addEventListener('click', function () { finish(false); });

        // ---- 1. scan line passes over the email -------------------------
        function sweep() {
            return new Promise(function (resolve) {
                if (!doc || !line) { resolve(); return; }
                doc.scrollTop = 0;
                var height = Math.min(doc.scrollHeight, doc.clientHeight);
                var docTop = doc.getBoundingClientRect().top;
                var targets = marks.map(function (m) {
                    return { el: m, y: m.getBoundingClientRect().top - docTop + 6, lit: false };
                });
                var duration = Math.max(1600, Math.min(2400, 1400 + marks.length * 60));
                var start = null;
                var found = 0;

                line.style.opacity = '1';

                function step(ts) {
                    if (start === null) start = ts;
                    var t = Math.min(1, (ts - start) / duration);
                    var eased = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                    var y = eased * height;
                    line.style.transform = 'translateY(' + (y - 64) + 'px)';

                    targets.forEach(function (target) {
                        if (!target.lit && target.y <= y) {
                            target.lit = true;
                            found += 1;
                            target.el.classList.remove('is-pending');
                            target.el.classList.add('is-lit');
                            setTimeout(function () { target.el.classList.remove('is-lit'); }, 1000);
                            if (phraseDesc) phraseDesc.textContent = plural(found, 'phrase', 'phrases') + ' found';
                        }
                    });

                    if (t < 1) {
                        tl.frame(step);
                    } else {
                        // Anything below the visible area is marked without the pop.
                        targets.forEach(function (target) {
                            if (!target.lit) { target.lit = true; found += 1; target.el.classList.remove('is-pending'); }
                        });
                        if (phraseDesc) {
                            phraseDesc.textContent = found ? plural(found, 'phrase', 'phrases') + ' flagged' : 'No flagged wording found.';
                        }
                        line.style.transition = 'opacity .5s';
                        line.style.opacity = '0';
                        resolve();
                    }
                }
                tl.frame(step);
            });
        }

        function revealEach(list, gap) {
            return list.reduce(function (p, el) {
                return p.then(function () {
                    el.classList.remove('is-hidden');
                    return tl.wait(gap);
                });
            }, Promise.resolve());
        }

        tl.wait(250).then(function () {
            setTitle(scanner, 'Scanning');
            stageSet(stages.phrases, 'active');
            return sweep();
        }).then(function () {
            stageSet(stages.phrases, 'done');
            stageSet(stages.manipulation, 'active');
            setTitle(scanner, 'Identifying signals');
            return tl.wait(250);
        }).then(function () {
            return revealEach(reveals.manipulation, 220);
        }).then(function () {
            stageSet(stages.manipulation, 'done');
            stageSet(stages.intel, 'active');
            setTitle(scanner, 'Threat intelligence');
            return tl.wait(250);
        }).then(function () {
            return revealEach(reveals.intel, 180);
        }).then(function () {
            return tl.wait(250);
        }).then(function () {
            stageSet(stages.intel, 'done');
            stageSet(stages.score, 'active');
            setTitle(scanner, 'Assessing threat');
            scanner.classList.add('is-scoring');
            paintScore(0);
            return tl.wait(200);
        }).then(function () {
            // ---- score generation: 0.0 → value, decelerating ------------
            return new Promise(function (resolve) {
                var start = null;
                function step(ts) {
                    if (start === null) start = ts;
                    var p = Math.min(1, (ts - start) / 1100);
                    paintScore(1 - Math.pow(1 - p, 3));
                    if (p < 1) tl.frame(step); else resolve();
                }
                tl.frame(step);
            });
        }).then(function () {
            stageSet(stages.score, 'done');
            return tl.wait(350);
        }).then(function () {
            finish(true);
        });
    }

    /* ------------------------------------------------------------------ */
    function boot() {
        document.querySelectorAll('[data-scanner="intake"]').forEach(initIntake);
        document.querySelectorAll('[data-scanner="result"]').forEach(initResult);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
