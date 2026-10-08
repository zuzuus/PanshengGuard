/**
 * PanshengGuard — shared UI behaviour (no dependencies).
 *
 *  - theme toggle (light / dark, remembered per browser)
 *  - mobile navigation
 *  - reveal-on-scroll for marketing sections
 *  - busy state on form submit buttons
 *
 * Purely presentational: nothing here talks to the server.
 */
(function () {
    'use strict';

    var root = document.documentElement;

    /* ---- Theme ------------------------------------------------------- */
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try { localStorage.setItem('pg-theme', next); } catch (e) {}
            document.dispatchEvent(new CustomEvent('pg:themechange', { detail: next }));
        });
    });

    /* ---- Mobile navigation ------------------------------------------- */
    var toggle = document.getElementById('navToggle');
    var links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', function () {
            var open = links.classList.toggle('open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && links.classList.contains('open')) {
                links.classList.remove('open');
                toggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    /* ---- Reveal on scroll -------------------------------------------- */
    var reveals = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window && reveals.length) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('in');
                    io.unobserve(entry.target);
                }
            });
        }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
        reveals.forEach(function (el) { io.observe(el); });
    } else {
        reveals.forEach(function (el) { el.classList.add('in'); });
    }

    /* ---- Busy state on submit ------------------------------------------
       Same behaviour as before the redesign: a submit button shows a spinner
       and its own wording (or data-loading-text). Forms that manage their own
       state (the scanner) opt out with data-no-busy. */
    document.querySelectorAll('form:not([data-no-busy])').forEach(function (form) {
        form.addEventListener('submit', function () {
            var btn = form.querySelector('button[type="submit"]');
            if (!btn || btn.disabled) return;
            var busy = btn.dataset.loadingText || btn.textContent.trim();
            btn.dataset.originalText = btn.innerHTML;
            btn.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>' + busy;
            btn.disabled = true;
        });
    });

    // Restore buttons if the page comes back from the back/forward cache.
    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) return;
        document.querySelectorAll('button[data-original-text]').forEach(function (btn) {
            btn.innerHTML = btn.dataset.originalText;
            btn.disabled = false;
        });
    });
})();
