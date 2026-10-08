<script>
    // Theme toggle - visual preference only, stored in this browser.
    document.querySelectorAll('[data-theme-toggle]').forEach(function (button) {
        button.addEventListener('click', function () {
            var root = document.documentElement;
            var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            root.setAttribute('data-theme', next);
            try { localStorage.setItem('pg-theme', next); } catch (e) {}
            document.dispatchEvent(new CustomEvent('pg:themechange', { detail: { theme: next } }));
        });
    });
</script>
