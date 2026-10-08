<x-guest-layout>
    <div class="eyebrow">Welcome back</div>
    <h1>Log in</h1>
    <p class="auth-subtitle">Sign in to analyze emails and review your analysis history.</p>

    <x-auth-session-status class="auth-field" :status="session('status')" />

    <form method="POST" action="{{ route('login') }}">
        @csrf

        <div class="auth-field">
            <x-input-label for="email" :value="__('Email')" />
            <x-text-input id="email" type="email" name="email" :value="old('email')" required autofocus autocomplete="username" />
            <x-input-error :messages="$errors->get('email')" />
        </div>

        <div class="auth-field">
            <x-input-label for="password" :value="__('Password')" />
            <x-text-input id="password" type="password" name="password" required autocomplete="current-password" />
            <x-input-error :messages="$errors->get('password')" />
        </div>

        <label class="check auth-remember">
            <input id="remember_me" type="checkbox" name="remember">
            {{ __('Remember me') }}
        </label>

        <div class="auth-actions">
            @if (Route::has('password.request'))
                <a class="auth-link" href="{{ route('password.request') }}">{{ __('Forgot your password?') }}</a>
            @endif
            <x-primary-button>{{ __('Log in') }}</x-primary-button>
        </div>
    </form>

    <div class="auth-divider">OR</div>

    <a href="{{ route('auth.google') }}" class="btn-google">
        <svg width="18" height="18" viewBox="0 0 48 48">
            <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.9 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21 21-9.4 21-21c0-1.4-.1-2.7-.4-3.5z"/>
            <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.5 15.9 18.9 13 24 13c3.1 0 5.8 1.1 8 3l6-6C34.5 5.1 29.5 3 24 3 16.3 3 9.7 7.3 6.3 14.7z"/>
            <path fill="#4CAF50" d="M24 45c5.3 0 10.1-1.8 13.9-5l-6.4-5.4C29.4 36 26.8 37 24 37c-5.2 0-9.6-3.1-11.3-7.6l-6.5 5C9.6 40.5 16.3 45 24 45z"/>
            <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.6l6.4 5.4C41.4 35.9 44 30.3 44 24c0-1.4-.1-2.7-.4-3.5z"/>
        </svg>
        Continue with Google
    </a>

    <p class="auth-footnote">
        New here? <a href="{{ route('register') }}" class="auth-link">Create an account</a>
    </p>
</x-guest-layout>
