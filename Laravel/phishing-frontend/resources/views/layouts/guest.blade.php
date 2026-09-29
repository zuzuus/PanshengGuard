<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">

    <title>{{ config('app.name', 'PanshengGuard') }}</title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="{{ asset('css/app.css') }}">
</head>
<body>

    <div class="auth-shell">
        <a href="{{ route('home') }}" class="navbar-brand auth-brand">
            <span class="seal"><x-icon name="shield-check" /></span>
            <span>PanshengGuard</span>
        </a>

        <div class="card auth-card">
            {{ $slot }}
        </div>

        <p class="auth-footnote">
            <a href="{{ route('home') }}" class="auth-back">
                <x-icon name="arrow-left" />
                Back to home
            </a>
        </p>
    </div>

</body>
</html>
