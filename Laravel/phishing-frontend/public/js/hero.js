/**
 * PanshengGuard — home page cursor interactions (visual only).
 *
 *  1. Threat lens: a faint field of example phishing wording sits behind the
 *     hero. A lens follows the cursor and reveals the manipulation inside it:
 *     phrases light up in their technique colour with a label, and a small
 *     readout names what the lens is currently over. When the cursor is not
 *     in the hero (or on touch screens), the lens drifts slowly on its own.
 *  2. Grid spotlight: the background grid brightens around the cursor.
 *  3. Magnetic buttons: the hero buttons lean slightly toward the cursor.
 *  4. Scanner spotlight: a soft light follows the cursor across the scanner.
 *
 * Decoration only — the wording in the field is illustrative, never analysis,
 * and nothing here touches the form or the server. Respects
 * prefers-reduced-motion (static lens, no movement).
 */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var finePointer = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    var LABELS = { u: 'URGENCY', a: 'FALSE AUTHORITY', f: 'FEAR', s: 'SCARCITY' };
    var CLASSES = { u: 'tq-urgency', a: 'tq-authority', f: 'tq-fear', s: 'tq-scarcity' };

    // Illustrative phishing wording. {x:text} marks a phrase of technique x.
    var LINES = [
        'Your account requires {u:immediate} verification. Please {a:verify} your identity before the {u:deadline}.',
        'Unusual sign-in detected on your online banking. Your access will be {f:suspended} within {u:24 hours}.',
        'Message from the {a:Security Team}: confirm your password and TAC to restore full access.',
        '{s:Final warning}: this is your {s:last chance} to claim the pending refund {u:today}.',
        'Failure to respond will result in {f:permanent restriction} of your account services.',
        'Dear Customer, your parcel is on hold. Pay the customs fee {u:now} to release it.',
        'Our {a:head office} has {f:flagged} {f:unauthorized} activity. Act {u:immediately}.',
        '{s:Limited} time only: an {s:exclusive} cashback reward that {s:expires soon}.',
        'The {a:compliance} department requires you to update your details {u:right away}.',
        'You will {f:lose access} to your funds unless you sign in through the secure link.'
    ];

    /* ------------------------------------------------------------------ */
    function buildLine(source, reveal) {
        var frag = document.createDocumentFragment();
        var re = /\{([uafs]):([^}]+)\}/g;
        var last = 0;
        var m;
        while ((m = re.exec(source)) !== null) {
            if (m.index > last) frag.appendChild(document.createTextNode(source.slice(last, m.index)));
            var span = document.createElement('span');
            span.textContent = m[2];
            if (reveal) {
                span.className = 'fm ' + CLASSES[m[1]];
                span.setAttribute('data-label', LABELS[m[1]]);
                span.setAttribute('data-t', m[1]);
            }
            frag.appendChild(span);
            last = m.index + m[0].length;
        }
        if (last < source.length) frag.appendChild(document.createTextNode(source.slice(last)));
        return frag;
    }

    function fillField(base, reveal, rows) {
        base.textContent = '';
        reveal.textContent = '';
        for (var i = 0; i < rows; i++) {
            // Each row strings several sentences together so it runs edge to edge.
            var text = [LINES[i % LINES.length], LINES[(i + 3) % LINES.length], LINES[(i + 6) % LINES.length]].join('   ·   ');
            var offset = ((i * 137) % 260) * -1 + 'px';
            [[base, false], [reveal, true]].forEach(function (pair) {
                var row = document.createElement('div');
                row.className = 'field-row';
                row.style.marginLeft = offset;
                row.appendChild(buildLine(text, pair[1]));
                pair[0].appendChild(row);
            });
        }
    }

    /* ==================================================================
     * 1 + 2. Threat lens and grid spotlight
     * ================================================================== */
    function initLens(hero) {
        var field = hero.querySelector('[data-hero-field]');
        var base = hero.querySelector('[data-field-base]');
        var reveal = hero.querySelector('[data-field-reveal]');
        var lens = hero.querySelector('[data-lens]');
        var readout = hero.querySelector('[data-lens-readout]');
        if (!field || !base || !reveal || !lens) return;

        var radius = 0;
        var marks = [];
        var w = 0, h = 0;

        function layout() {
            var rect = field.getBoundingClientRect();
            w = rect.width;
            h = rect.height;
            radius = w < 640 ? 78 : 112;
            field.style.setProperty('--lens-r', radius + 'px');
            lens.style.width = lens.style.height = (radius * 2) + 'px';

            var rowH = 46;
            fillField(base, reveal, Math.ceil(h / rowH) + 1);

            // Cache phrase centres (field coordinates) for the readout.
            marks = Array.prototype.map.call(reveal.querySelectorAll('.fm'), function (el) {
                var r = el.getBoundingClientRect();
                return { t: el.getAttribute('data-t'), x: r.left - rect.left + r.width / 2, y: r.top - rect.top + r.height / 2 };
            });
        }

        // Position state: current (x, y) eases toward target (tx, ty).
        var x = 0, y = 0, tx = 0, ty = 0;
        var pointerInside = false;
        var lastPointer = 0;
        var start = performance.now();
        var frame = 0;
        var running = false;
        var lastReadout = '';

        function autoTarget(t) {
            // A slow figure-of-eight around the headline.
            var s = (t - start) / 1000;
            var narrow = w < 640;
            tx = w * 0.5 + Math.sin(s * 0.45) * w * (narrow ? 0.3 : 0.34);
            ty = h * (narrow ? 0.34 : 0.46) + Math.sin(s * 0.9) * h * (narrow ? 0.16 : 0.24);
        }

        function apply() {
            field.style.setProperty('--lx', x.toFixed(1) + 'px');
            field.style.setProperty('--ly', y.toFixed(1) + 'px');
            hero.style.setProperty('--gx', x.toFixed(1) + 'px');
            hero.style.setProperty('--gy', y.toFixed(1) + 'px');
            lens.style.transform = 'translate3d(' + (x - radius).toFixed(1) + 'px,' + (y - radius).toFixed(1) + 'px,0)';
        }

        function updateReadout() {
            var found = {};
            var count = 0;
            var r2 = (radius * 0.82) * (radius * 0.82);
            for (var i = 0; i < marks.length; i++) {
                var dx = marks[i].x - x, dy = marks[i].y - y;
                if (dx * dx + dy * dy < r2) { found[marks[i].t] = true; count++; }
            }
            var names = Object.keys(found).map(function (k) { return LABELS[k]; });
            var text = count
                ? count + (count === 1 ? ' signal · ' : ' signals · ') + names.join(' · ')
                : 'Scanning';
            if (text !== lastReadout) {
                readout.textContent = text;
                lens.classList.toggle('has-signal', count > 0);
                lastReadout = text;
            }
        }

        function tick(t) {
            if (!running) return;
            // Hand back to the automatic drift a moment after the cursor leaves.
            if (!pointerInside || t - lastPointer > 4000) autoTarget(t);
            var ease = pointerInside ? 0.16 : 0.05;
            x += (tx - x) * ease;
            y += (ty - y) * ease;
            apply();
            if ((frame++ % 5) === 0) updateReadout();
            requestAnimationFrame(tick);
        }

        function startLoop() {
            if (running || reduceMotion) return;
            running = true;
            requestAnimationFrame(tick);
        }
        function stopLoop() { running = false; }

        hero.addEventListener('pointermove', function (e) {
            var rect = field.getBoundingClientRect();
            tx = e.clientX - rect.left;
            ty = e.clientY - rect.top;
            pointerInside = true;
            lastPointer = performance.now();
            hero.classList.add('is-pointer');
        });
        hero.addEventListener('pointerleave', function () {
            pointerInside = false;
            hero.classList.remove('is-pointer');
        });

        var resizeTimer = null;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () { layout(); if (reduceMotion) placeStatic(); }, 150);
        });

        function placeStatic() {
            x = tx = w * 0.78;
            y = ty = h * 0.3;
            apply();
            updateReadout();
        }

        layout();
        x = tx = w * 0.5;
        y = ty = h * 0.45;
        autoTarget(performance.now());
        x = tx; y = ty;
        apply();
        field.classList.add('is-ready');

        if (reduceMotion) { placeStatic(); return; }

        // Only animate while the hero is on screen and the tab is visible.
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entries) {
                entries[0].isIntersecting && !document.hidden ? startLoop() : stopLoop();
            }).observe(hero);
        } else {
            startLoop();
        }
        document.addEventListener('visibilitychange', function () {
            document.hidden ? stopLoop() : startLoop();
        });
    }

    /* ==================================================================
     * 3. Magnetic buttons
     * ================================================================== */
    function initMagnetic(btn) {
        if (reduceMotion || !finePointer) return;
        var zone = 40;
        document.addEventListener('pointermove', function (e) {
            var r = btn.getBoundingClientRect();
            var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
            var dx = e.clientX - cx, dy = e.clientY - cy;
            var inside = Math.abs(dx) < r.width / 2 + zone && Math.abs(dy) < r.height / 2 + zone;
            btn.style.transform = inside
                ? 'translate(' + (dx * 0.16).toFixed(1) + 'px,' + (dy * 0.28).toFixed(1) + 'px)'
                : '';
        }, { passive: true });
    }

    /* ==================================================================
     * 4. Scanner spotlight
     * ================================================================== */
    function initSpotlight(el) {
        if (reduceMotion || !finePointer) return;
        el.addEventListener('pointermove', function (e) {
            var r = el.getBoundingClientRect();
            el.style.setProperty('--sx', (e.clientX - r.left) + 'px');
            el.style.setProperty('--sy', (e.clientY - r.top) + 'px');
        });
    }

    function boot() {
        document.querySelectorAll('[data-hero]').forEach(initLens);
        document.querySelectorAll('[data-magnetic]').forEach(initMagnetic);
        document.querySelectorAll('[data-spotlight]').forEach(initSpotlight);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
