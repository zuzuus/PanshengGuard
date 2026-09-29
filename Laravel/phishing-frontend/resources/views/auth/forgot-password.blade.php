<x-guest-layout>
    <div class="eyebrow">Account Recovery</div>
    <h1>Forgot Password</h1>
    <p class="auth-subtitle">
        {{ __('No problem. Tell us your email and we\'ll send a password reset link.') }}
    </p>

    <x-auth-session-status class="auth-field" :status="session('status')" />

    <form method="POST" action="{{ route('password.email') }}">
        @csrf

        <div class="auth-field">
            <x-input-label for="email" :value="__('Email')" />
            <x-text-input id="email" type="email" name="email" :value="old('email')" required autofocus />
            <x-input-error :messages="$errors->get('email')" />
        </div>

        <div class="auth-actions" style="justify-content: flex-end;">
            <x-primary-button>{{ __('Email Password Reset Link') }}</x-primary-button>
        </div>
    </form>
</x-guest-layout>
