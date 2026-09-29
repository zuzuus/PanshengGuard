<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'Phishing Detector')</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
    @stack('styles')
</head>
<body>

    <nav class="navbar">
        <a href="{{ route('home') }}" class="navbar-brand">
            <span class="seal"><x-icon name="shield-check" /></span>
            <span>PanshengGuard</span>
        </a>

        <button type="button" class="navbar-toggle" id="navToggle" aria-label="Toggle menu" aria-expanded="false" aria-controls="navLinks">
            <x-icon name="menu" />
        </button>

        <ul class="navbar-links" id="navLinks">
            <li><a href="{{ route('home') }}" class="{{ request()->routeIs('home') ? 'active' : '' }}">Home</a></li>
            <li><a href="{{ Route::has('history') ? route('history') : '#' }}" class="{{ request()->routeIs('history*') ? 'active' : '' }}">History</a></li>
            <li><a href="{{ Route::has('dashboard') ? route('dashboard') : '#' }}" class="{{ request()->routeIs('dashboard') ? 'active' : '' }}">Dashboard</a></li>
            <li><a href="{{ Route::has('about') ? route('about') : '#' }}">About</a></li>

            @auth
                <li><a href="{{ Route::has('profile.edit') ? route('profile.edit') : '#' }}">{{ Auth::user()->name }}</a></li>
                <li>
                    <form method="POST" action="{{ route('logout') }}" class="navbar-form">
                        @csrf
                        <button type="submit" class="btn-login">Log out</button>
                    </form>
                </li>
            @else
                <li><a href="{{ Route::has('login') ? route('login') : '#' }}" class="btn-login">Log in</a></li>
            @endauth
        </ul>
    </nav>

    <div class="page-container">
        {{-- Flash messages live here so every page gets them in the same place.
             Previously only the landing page rendered session('error'), so a
             redirect from anywhere else lost its message silently. --}}
        @if (session('success'))
            <div class="alert alert-success">
                <x-icon name="check-circle" />
                <span>{{ session('success') }}</span>
            </div>
        @endif

        @if (session('error'))
            <div class="alert alert-error">
                <x-icon name="alert-circle" />
                <span>{{ session('error') }}</span>
            </div>
        @endif

        @yield('content')
    </div>

    <footer class="footer">
        <div class="footer-mark">
            <x-icon name="shield" />
            <span>PanshengGuard</span>
        </div>
        <p>
            Final Year Project, {{ date('Y') }}<br>
            <a href="{{ Route::has('about') ? route('about') : '#' }}">About</a> &middot; Built to help you spot deception before it costs you.
        </p>
    </footer>

    <script>
        document.getElementById('navToggle')?.addEventListener('click', function () {
            const open = document.getElementById('navLinks').classList.toggle('open');
            this.setAttribute('aria-expanded', open ? 'true' : 'false');
        });

        // Show a loading state on any form submit button so slow API calls feel
        // responsive. The button keeps its own wording — a login form should not
        // announce "Analysing…" — unless it opts in via data-loading-text.
        document.querySelectorAll('form').forEach(function (form) {
            form.addEventListener('submit', function () {
                const btn = form.querySelector('button[type="submit"]');
                if (!btn || btn.disabled) return;

                const busyText = btn.dataset.loadingText || btn.textContent.trim();
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<span class="btn-spinner"></span>' + busyText;
                btn.disabled = true;
            });
        });
    </script>

    @stack('scripts')
</body>
</html>