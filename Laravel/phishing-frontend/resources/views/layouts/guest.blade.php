<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">

    <title>{{ config('app.name', 'PanshengGuard') }}</title>

    @include('partials.theme-head')
</head>
<body>

    <div class="auth-shell">
        <aside class="auth-side">
            <a href="{{ route('home') }}" class="brand">
                <span class="brand-mark"><x-brand-mark /></span>
                <span>PanshengGuard</span>
            </a>

            <div>
                <div class="eyebrow" style="margin-bottom: 20px;">Email threat analysis</div>
                <div class="auth-side-title" style="font-family: var(--font-display);">See the threat <span class="muted">before you click.</span></div>
                <p class="lead" style="margin-top: 24px; max-width: 420px;">
                    Save every analysis, follow your threat trends over time, and connect the Gmail extension.
                </p>
            </div>

            <div class="auth-side-foot">&copy; {{ date('Y') }} PanshengGuard &middot; Final Year Project</div>
        </aside>

        <main class="auth-main">
            <a href="{{ route('home') }}" class="brand auth-brand-mobile">
                <span class="brand-mark"><x-brand-mark /></span>
                <span>PanshengGuard</span>
            </a>
            <div class="auth-top">
                <button type="button" class="icon-btn theme-toggle" data-theme-toggle aria-label="Switch colour theme">
                    <x-icon name="moon" class="icon-moon" />
                    <x-icon name="sun" class="icon-sun" />
                </button>
            </div>

            {{-- Flash messages, e.g. "You've used your free scan" when a guest
                 is redirected here from the scanner. --}}
            @if (session('error') || session('success'))
                <div class="auth-flash">
                    @if (session('error'))
                        <div class="alert alert-error" role="alert"><x-icon name="alert-circle" /><span>{{ session('error') }}</span></div>
                    @endif
                    @if (session('success'))
                        <div class="alert alert-success" role="status"><x-icon name="check-circle" /><span>{{ session('success') }}</span></div>
                    @endif
                </div>
            @endif

            <div class="auth-card fade-up">
                {{ $slot }}
            </div>

            <p class="auth-footnote">
                <a href="{{ route('home') }}" class="auth-back">
                    <x-icon name="arrow-left" />
                    Back to the scanner
                </a>
            </p>
        </main>
    </div>

    @include('partials.ui-script')
</body>
</html>
