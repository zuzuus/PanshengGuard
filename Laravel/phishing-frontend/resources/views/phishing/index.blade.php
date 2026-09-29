@extends('layouts.site')

@section('title', 'PanshengGuard — Phishing Email Detector')

@section('content')

    <div class="intake-head">
        <div class="scan-line"></div>
        <div class="eyebrow">Evidence Intake</div>
        <h1>Paste the email. We'll examine it.</h1>
        <p class="section-lead">
            Drop in a suspicious email's subject and body. We'll check it against a trained classifier,
            scan its links against VirusTotal, and flag the manipulation tactics it's using &mdash;
            all explained in plain language, with what to do next.
        </p>
    </div>

    <div class="card card-feature">
        <form action="{{ route('analyze') }}" method="POST">
            @csrf
            <textarea
                name="email_text"
                rows="10"
                placeholder="Paste subject + body here..."
                required
            >{{ old('email_text') }}</textarea>

            @error('email_text')
                <div class="alert alert-error" style="margin-top: var(--space-3);">
                    <x-icon name="alert-circle" />
                    <span>{{ $message }}</span>
                </div>
            @enderror

            <div class="form-footer">
                <label>
                    <input type="checkbox" name="check_urls" value="1" checked>
                    Check URLs with VirusTotal
                </label>

                <button type="submit" class="btn" data-loading-text="Analysing…">
                    <x-icon name="search" />
                    Analyse Email
                </button>
            </div>
        </form>
    </div>

    <div class="section-heading">
        <div class="eyebrow">The Process</div>
        <h2>How it works</h2>
    </div>

    <div class="feature-grid">
        @foreach ([
            ['icon' => 'sparkles', 'step' => 'Step 01', 'title' => 'Clean',          'body' => 'The text is stripped down to its core wording, ready for analysis.'],
            ['icon' => 'cpu',      'step' => 'Step 02', 'title' => 'Classify',       'body' => "A trained model estimates the probability it's phishing."],
            ['icon' => 'mask',     'step' => 'Step 03', 'title' => 'Detect Tactics', 'body' => 'Urgency, fear, authority, and scarcity language get flagged.'],
            ['icon' => 'link',     'step' => 'Step 04', 'title' => 'Scan Links',     'body' => "Any URLs are checked against VirusTotal's threat database."],
        ] as $feature)
            <div class="card">
                <span class="feature-icon"><x-icon :name="$feature['icon']" /></span>
                <span class="feature-step">{{ $feature['step'] }}</span>
                <span class="feature-title">{{ $feature['title'] }}</span>
                <p class="feature-body">{{ $feature['body'] }}</p>
            </div>
        @endforeach
    </div>

    <div class="card card-quote">
        <div class="card-header">
            <span class="card-icon"><x-icon name="lightbulb" /></span>
            <h3>Why this exists</h3>
        </div>
        <p class="text-muted">
            Phishing works by rushing you past careful thinking. This tool exists to slow that down &mdash;
            giving you a second opinion, in plain language, before you click anything.
        </p>
    </div>

@endsection
