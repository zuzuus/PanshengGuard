@if (session('status') === 'profile-updated')
    <div class="alert alert-success" style="margin-bottom: 20px;"><x-icon name="check-circle" /><span>Profile updated successfully.</span></div>
@endif

<form method="POST" action="{{ route('profile.update') }}">
    @csrf
    @method('patch')

    <div class="field">
        <label for="name">Name</label>
        <input id="name" name="name" type="text" value="{{ old('name', $user->name) }}" required autocomplete="name">
        @error('name')
            <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
        @enderror
    </div>

    <div class="field">
        <label for="email">Email</label>
        <input id="email" name="email" type="email" value="{{ old('email', $user->email) }}" required autocomplete="username">
        @error('email')
            <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
        @enderror
    </div>

    @if ($user instanceof \Illuminate\Contracts\Auth\MustVerifyEmail && ! $user->hasVerifiedEmail())
        <p class="field-hint" style="margin-top: 12px;">
            Your email address is unverified.
            <button form="send-verification" class="text-btn" style="display: inline; color: var(--accent);">
                Re-send the verification email.
            </button>
        </p>

        @if (session('status') === 'verification-link-sent')
            <div class="alert alert-success" style="margin-top: 8px;">
                <x-icon name="check-circle" /><span>A new verification link has been sent to your email address.</span>
            </div>
        @endif
    @endif

    <div style="margin-top: 24px;">
        <button type="submit" class="btn btn-primary">Save changes</button>
    </div>
</form>

@if ($user instanceof \Illuminate\Contracts\Auth\MustVerifyEmail && ! $user->hasVerifiedEmail())
    <form id="send-verification" method="POST" action="{{ route('verification.send') }}">
        @csrf
    </form>
@endif
