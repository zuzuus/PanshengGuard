<x-guest-layout>
    <div class="eyebrow">One More Step</div>
    <h1>Verify Email</h1>
    <p class="auth-subtitle">
        {{ __('Thanks for signing up! Before getting started, could you verify your email address by clicking the link we just emailed you? If you didn\'t get it, we can send another.') }}
    </p>

    @if (session('status') == 'verification-link-sent')
        <div class="alert alert-success">
            {{ __('A new verification link has been sent to the email address you provided during registration.') }}
        </div>
    @endif

    <div class="auth-actions">
        <form method="POST" action="{{ route('verification.send') }}">
            @csrf
            <x-primary-button>{{ __('Resend Verification Email') }}</x-primary-button>
        </form>

        <form method="POST" action="{{ route('logout') }}">
            @csrf
            <button type="submit" class="auth-link" style="background:none; border:none; cursor:pointer; font-family:inherit;">
                {{ __('Log Out') }}
            </button>
        </form>
    </div>
</x-guest-layout>
