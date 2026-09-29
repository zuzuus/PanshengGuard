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

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
</head>
<body>

    <div class="error-shell">
        <a href="{{ url('/') }}" class="navbar-brand auth-brand">
            <span class="seal"><x-icon name="shield-check" /></span>
            <span>PanshengGuard</span>
        </a>

        <div class="card auth-card error-card">
            <div class="error-code">@yield('code')</div>
            <div class="error-stamp">@yield('stamp', 'Case Closed')</div>

            <h1 class="error-title">@yield('title', 'Something went wrong')</h1>

            <p class="error-message">@yield('message')</p>

            <div class="error-actions">
                <a href="{{ url('/') }}" class="btn">
                    <x-icon name="home" />
                    Back to the scanner
                </a>
                @yield('extra-action')
            </div>
        </div>
    </div>

</body>
</html>
