@extends('layouts.site')

@section('title', 'About — PanshengGuard')

@section('content')

    <div class="eyebrow">The Case File on Us</div>
    <h1>About PanshengGuard</h1>
    <p class="section-lead">
        A final year project built to help everyday people spot phishing emails before they cost them something.
    </p>

    <div class="card">
        <div class="card-header">
            <span class="card-icon"><x-icon name="search" /></span>
            <h3>What this does</h3>
        </div>
        <p>
            PanshengGuard reads a pasted email and checks it two ways: a machine learning model trained
            to recognise phishing patterns in the wording, and a rule-based scan for classic manipulation
            tactics &mdash; urgency, false authority, fear, and scarcity. Any links in the email are also
            checked against VirusTotal's threat database. The result is a plain-language verdict, not just
            a raw score, so you actually know what to do next.
        </p>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="card-icon"><x-icon name="layers" /></span>
            <h3>How it works</h3>
        </div>
        <p>The email you paste goes through four steps:</p>
        <ol class="step-list">
            <li><strong>Cleaning</strong> &mdash; the text is stripped of noise and reduced to its core wording.</li>
            <li><strong>Classification</strong> &mdash; a trained model estimates the probability the email is phishing.</li>
            <li><strong>Technique detection</strong> &mdash; the wording is scanned for manipulation tactics and blended into a sophistication score.</li>
            <li><strong>Link scanning</strong> &mdash; any URLs found are checked against VirusTotal's engines.</li>
        </ol>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="card-icon"><x-icon name="lightbulb" /></span>
            <h3>Why it exists</h3>
        </div>
        <p>
            Phishing emails succeed because they're built to bypass careful thinking &mdash; urgency and
            fear push people to act before they question anything. This project exists to slow that down:
            giving people a second opinion, in plain language, before they click.
        </p>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="card-icon"><x-icon name="cpu" /></span>
            <h3>Built with</h3>
        </div>
        <ul class="stack-list">
            <li><strong>Python</strong> <span class="text-muted">FastAPI, scikit-learn, spaCy &mdash; the detection engine</span></li>
            <li><strong>Laravel</strong> <span class="text-muted">the web experience and scan history</span></li>
            <li><strong>VirusTotal</strong> <span class="text-muted">link reputation intelligence</span></li>
        </ul>
    </div>

    <div class="card">
        <div class="card-header">
            <span class="card-icon is-green"><x-icon name="lock" /></span>
            <h3>A note on privacy</h3>
        </div>
        <p>
            Emails you submit are used only to produce your result. Personal details like email addresses,
            phone numbers, and card numbers are automatically masked before analysis. Scans are saved to
            your account so you can revisit them, and you're free to delete your account &mdash; and
            everything tied to it &mdash; at any time from your profile.
        </p>
    </div>

@endsection
