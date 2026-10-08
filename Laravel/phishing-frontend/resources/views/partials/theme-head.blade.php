{{-- Shared <head> assets for every layout: theme bootstrap, fonts, stylesheet.
     The theme is resolved before first paint so a dark-mode user never sees a
     white flash: saved choice first, then the operating-system preference. --}}
<script>
    (function () {
        var theme = null;
        try { theme = localStorage.getItem('pg-theme'); } catch (e) {}
        if (theme !== 'light' && theme !== 'dark') {
            theme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        document.documentElement.setAttribute('data-theme', theme);
        document.documentElement.classList.add('js');
    })();
</script>
<meta name="color-scheme" content="light dark">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<link rel="stylesheet" href="{{ asset('css/app.css') }}?v=4">
