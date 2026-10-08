<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield('title', 'PanshengGuard')</title>
    <meta name="description" content="PanshengGuard analyses suspicious emails and explains the signals behind potential phishing threats.">

    @include('partials.theme-head')

    @stack('styles')
</head>
<body>

    <nav class="nav" aria-label="Main">
        <div class="container nav-inner">
            <a href="{{ route('home') }}" class="brand" aria-label="PanshengGuard home">
                <span class="brand-mark"><x-brand-mark /></span>
                <span>PanshengGuard</span>
            </a>

            <ul class="nav-links" id="navLinks">
                <li><a href="{{ route('home') }}" class="{{ request()->routeIs('home', 'analyze') ? 'active' : '' }}">Scan</a></li>
                <li><a href="{{ Route::has('dashboard') ? route('dashboard') : '#' }}" class="{{ request()->routeIs('dashboard') ? 'active' : '' }}">Dashboard</a></li>
                <li><a href="{{ Route::has('history') ? route('history') : '#' }}" class="{{ request()->routeIs('history*') ? 'active' : '' }}">History</a></li>
                <li><a href="{{ Route::has('about') ? route('about') : '#' }}" class="{{ request()->routeIs('about') ? 'active' : '' }}">About</a></li>
            </ul>

            <div class="nav-actions">
                <button type="button" class="icon-btn theme-toggle" data-theme-toggle aria-label="Switch colour theme" title="Switch theme">
                    <x-icon name="moon" class="icon-moon" />
                    <x-icon name="sun" class="icon-sun" />
                </button>

                @auth
                    <a href="{{ Route::has('profile.edit') ? route('profile.edit') : '#' }}" class="nav-user" title="Your profile">
                        <span class="avatar">{{ \Illuminate\Support\Str::upper(\Illuminate\Support\Str::substr(Auth::user()->name, 0, 1)) }}</span>
                        <span class="nav-user-name">{{ Auth::user()->name }}</span>
                    </a>
                    <form method="POST" action="{{ route('logout') }}" class="nav-form">
                        @csrf
                        <button type="submit" class="icon-btn" aria-label="Log out" title="Log out">
                            <x-icon name="log-out" />
                        </button>
                    </form>
                @else
                    <a href="{{ Route::has('login') ? route('login') : '#' }}" class="btn btn-secondary btn-sm">Log in</a>
                @endauth

                <button type="button" class="icon-btn nav-toggle" id="navToggle" aria-label="Toggle menu" aria-expanded="false" aria-controls="navLinks">
                    <x-icon name="menu" />
                </button>
            </div>
        </div>
    </nav>

    <main>
        {{-- Flash messages live here so every page gets them in the same place.
             A page can render its own error presentation instead (the scanner
             does) by defining the "inline-error" section. --}}
        @if (session('success') || (session('error') && ! View::hasSection('inline-error')))
            <div class="container flash-stack">
                @if (session('success'))
                    <div class="alert alert-success" role="status">
                        <x-icon name="check-circle" />
                        <span>{{ session('success') }}</span>
                    </div>
                @endif

                @if (session('error') && ! View::hasSection('inline-error'))
                    <div class="alert alert-error" role="alert">
                        <x-icon name="alert-circle" />
                        <span>{{ session('error') }}</span>
                    </div>
                @endif
            </div>
        @endif

        @yield('content')
    </main>

    <footer class="footer">
        <div class="container">
            <div class="footer-inner">
                <div>
                    <a href="{{ route('home') }}" class="brand">
                        <span class="brand-mark"><x-brand-mark /></span>
                        <span>PanshengGuard</span>
                    </a>
                    <p>Email threat analysis that explains its reasoning &mdash; so you can see the threat before you click.</p>
                </div>
                <div>
                    <h4>Product</h4>
                    <ul>
                        <li><a href="{{ route('home') }}#scanner">Analyze an email</a></li>
                        <li><a href="{{ Route::has('dashboard') ? route('dashboard') : '#' }}">Dashboard</a></li>
                        <li><a href="{{ Route::has('history') ? route('history') : '#' }}">Analysis history</a></li>
                    </ul>
                </div>
                <div>
                    <h4>Project</h4>
                    <ul>
                        <li><a href="{{ Route::has('about') ? route('about') : '#' }}">About PanshengGuard</a></li>
                        @auth
                            <li><a href="{{ Route::has('profile.edit') ? route('profile.edit') : '#' }}">Browser extension</a></li>
                        @else
                            <li><a href="{{ Route::has('register') ? route('register') : '#' }}">Create an account</a></li>
                        @endauth
                    </ul>
                </div>
            </div>
            <div class="footer-base">
                <span>&copy; {{ date('Y') }} PanshengGuard &middot; Final Year Project</span>
                <span>Built to help you spot deception before it costs you.</span>
            </div>
        </div>
    </footer>

    @include('partials.ui-script')

    @stack('scripts')
</body>
</html>
