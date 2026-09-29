@extends('layouts.site')

@section('title', 'Your Profile — PanshengGuard')

@section('content')

    <div class="eyebrow">Account</div>
    <h1>Your Profile</h1>
    <p class="section-lead">
        Manage your account details, password, and account settings.
    </p>

    <div class="card">
        <h3>Profile Information</h3>
        <p style="color: var(--slate); font-size:0.9rem; margin-bottom:16px;">
            Update your account's name and email address.
        </p>
        @include('profile.partials.update-profile-information-form')
    </div>

    @if (Auth::user()->password)
    <div class="card">
        <h3>Update Password</h3>
        <p style="color: var(--slate); font-size:0.9rem; margin-bottom:16px;">
            Ensure your account is using a long, random password to stay secure.
        </p>
        @include('profile.partials.update-password-form')
    </div>
    @else
    <div class="card">
        <h3>Password</h3>
        <p style="color: var(--slate); font-size:0.9rem;">
            You signed in with Google, so there's no password to manage here.
        </p>
    </div>
    @endif

    <div class="card">
        <div class="card-header">
            <span class="card-icon"><x-icon name="terminal" /></span>
            <h3>Browser Extension</h3>
        </div>

        <p class="text-muted">
            The Gmail extension signs in with a token instead of a password, because
            it calls from outside the site and cannot use your session. Generate one
            here and paste it into the extension's settings.
        </p>

        @if (session('api_token_plain'))
            <div class="token-reveal">
                <div class="label">Your new token &mdash; copy it now</div>
                <code class="token-value">{{ session('api_token_plain') }}</code>
                <p class="token-note">
                    Only a hash of this is stored, so it cannot be shown again. If you
                    lose it, generate a new one &mdash; that also revokes this one.
                </p>
            </div>
        @endif

        <div class="token-status">
            @if (Auth::user()->hasApiToken())
                <x-icon name="check-circle" />
                <span>
                    Token active, created
                    {{ optional(Auth::user()->api_token_created_at)->diffForHumans() ?? 'recently' }}.
                </span>
            @else
                <x-icon name="alert-circle" />
                <span>No token yet &mdash; the extension cannot connect until you generate one.</span>
            @endif
        </div>

        <div class="token-actions">
            <form method="POST" action="{{ route('profile.token.generate') }}">
                @csrf
                <button type="submit" class="btn btn-secondary" data-loading-text="Generating…">
                    <x-icon name="terminal" />
                    {{ Auth::user()->hasApiToken() ? 'Regenerate token' : 'Generate token' }}
                </button>
            </form>

            @if (Auth::user()->hasApiToken())
                <form method="POST"
                      action="{{ route('profile.token.revoke') }}"
                      onsubmit="return confirm('Revoke this token? The extension will stop working until you generate a new one.');">
                    @csrf
                    @method('DELETE')
                    <button type="submit" class="btn btn-danger">Revoke</button>
                </form>
            @endif
        </div>
    </div>

    <div class="card" style="border-color: rgba(193, 68, 14, 0.3);">
        <h3 style="color: #FF8A5C;">Delete Account</h3>
        <p style="color: var(--slate); font-size:0.9rem; margin-bottom:16px;">
            Once your account is deleted, all of its resources and data will be permanently deleted, including your scan history.
        </p>
        @include('profile.partials.delete-user-form')
    </div>

@endsection