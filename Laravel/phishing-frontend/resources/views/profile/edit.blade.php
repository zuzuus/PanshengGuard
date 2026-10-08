@extends('layouts.site')

@section('title', 'Account — PanshengGuard')

@section('content')

<div class="container">
    <header class="page-head">
        <div class="eyebrow">Account</div>
        <h1>Settings</h1>
        <p class="lead">Manage your account details, password, and the Gmail extension connection.</p>
    </header>

    <div class="page-body">
        <section class="settings-section">
            <div class="aside">
                <h2>Profile information</h2>
                <p>Update your account&rsquo;s name and email address.</p>
            </div>
            <div class="body">
                @include('profile.partials.update-profile-information-form')
            </div>
        </section>

        <section class="settings-section">
            <div class="aside">
                <h2>Password</h2>
                <p>
                    @if (Auth::user()->password)
                        Use a long, random password to keep your account secure.
                    @else
                        You signed in with Google, so there&rsquo;s no password to manage here.
                    @endif
                </p>
            </div>
            <div class="body">
                @if (Auth::user()->password)
                    @include('profile.partials.update-password-form')
                @else
                    <div class="empty-line neutral"><x-icon name="lock" /> Managed by your Google account.</div>
                @endif
            </div>
        </section>

        <section class="settings-section" id="extension">
            <div class="aside">
                <h2>Browser extension</h2>
                <p>
                    The Gmail extension signs in with a token instead of a password, because it calls from
                    outside the site and cannot use your session. Generate one here and paste it into the
                    extension&rsquo;s settings.
                </p>
            </div>
            <div class="body">
                @if (session('api_token_plain'))
                    <div class="token-reveal">
                        <div class="label-text">Your new token &mdash; copy it now</div>
                        <code class="token-value">{{ session('api_token_plain') }}</code>
                        <p class="token-note">
                            Only a hash of this is stored, so it cannot be shown again. If you lose it,
                            generate a new one &mdash; that also revokes this one.
                        </p>
                    </div>
                @endif

                <div class="token-status {{ Auth::user()->hasApiToken() ? 'is-active' : '' }}">
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

                <div class="btn-row">
                    <form method="POST" action="{{ route('profile.token.generate') }}">
                        @csrf
                        <button type="submit" class="btn btn-primary" data-loading-text="Generating…">
                            <x-icon name="key" />
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
        </section>

        <section class="settings-section is-danger">
            <div class="aside">
                <h2>Delete account</h2>
                <p>Once your account is deleted, all of its data is permanently deleted, including your analysis history.</p>
            </div>
            <div class="body">
                @include('profile.partials.delete-user-form')
            </div>
        </section>
    </div>
</div>

@endsection
