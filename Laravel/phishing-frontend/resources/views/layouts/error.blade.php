{{--
    Standalone shell for error pages.

    Deliberately does NOT extend layouts.site: that layout reads Auth::user()
    for the navbar, and an error page has to render even when the thing that
    broke is the session or the database. Nothing here touches auth, Eloquent,
    or named routes - url('/') resolves without the route table.
--}}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Something went wrong') — PanshengGuard</title>

    <script>
        (function () {
            var t = null;
            try { t = localStorage.getItem('pg-theme'); } catch (e) {}
            if (t !== 'light' && t !== 'dark') t = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', t);
        })();
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}?v=4">
</head>
<body>

    <div class="error-shell">
        <a href="{{ url('/') }}" class="brand">
            <span class="brand-mark"><x-brand-mark /></span>
            <span>PanshengGuard</span>
        </a>

        <div class="error-code">@yield('code')</div>
        <div class="eyebrow eyebrow-plain">@yield('stamp', 'Error')</div>

        <h1>@yield('title', 'Something went wrong')</h1>

        <p class="lead">@yield('message')</p>

        <div class="btn-row">
            <a href="{{ url('/') }}" class="btn btn-primary">
                <x-icon name="scan" />
                Back to the scanner
            </a>
            @yield('extra-action')
        </div>
    </div>

</body>
</html>
