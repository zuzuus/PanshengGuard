@if (session('status') === 'profile-updated')
    <div class="alert alert-success">Profile updated successfully.</div>
@endif

<form method="POST" action="{{ route('profile.update') }}">
    @csrf
    @method('patch')

    <label for="name">Name</label>
    <input id="name" name="name" type="text" value="{{ old('name', $user->name) }}" required autofocus autocomplete="name">
    @error('name')
        <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
    @enderror

    <div style="margin-top:16px;">
        <label for="email">Email</label>
        <input id="email" name="email" type="email" value="{{ old('email', $user->email) }}" required autocomplete="username">
        @error('email')
            <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
        @enderror
    </div>

    @if ($user instanceof \Illuminate\Contracts\Auth\MustVerifyEmail && ! $user->hasVerifiedEmail())
        <p style="color: var(--slate); font-size:0.85rem; margin-top:10px;">
            Your email address is unverified.
            <button form="send-verification" style="background:none; border:none; color: var(--brass); cursor:pointer; text-decoration:underline; padding:0; font-size:0.85rem;">
                Click here to re-send the verification email.
            </button>
        </p>

        @if (session('status') === 'verification-link-sent')
            <div class="alert alert-success" style="margin-top:8px;">
                A new verification link has been sent to your email address.
            </div>
        @endif
    @endif

    <div style="margin-top:20px;">
        <button type="submit" class="btn">Save</button>
    </div>
</form>

@if ($user instanceof \Illuminate\Contracts\Auth\MustVerifyEmail && ! $user->hasVerifiedEmail())
    <form id="send-verification" method="POST" action="{{ route('verification.send') }}">
        @csrf
    </form>
@endif