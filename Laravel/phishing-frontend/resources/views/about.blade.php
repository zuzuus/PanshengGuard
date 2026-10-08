@extends('layouts.site')

@section('title', 'About — PanshengGuard')

@section('content')

<div class="container">
    <header class="page-head">
        <div class="eyebrow">About</div>
        <h1 style="max-width: 18ch;">A second opinion before you click.</h1>
        <p class="lead">
            PanshengGuard is a final year project built to help everyday people recognise phishing emails
            &mdash; and understand why they are dangerous &mdash; before they cost them something.
        </p>
    </header>

    <div class="page-body">
        <section class="split reveal">
            <div>
                <div class="eyebrow">01</div>
                <h2>What it does</h2>
            </div>
            <div class="split-body">
                <p>
                    PanshengGuard reads an email and checks it two ways: a machine learning model trained to
                    recognise phishing in the wording and structure of a message, and a rule-based scan for the
                    classic manipulation tactics &mdash; urgency, false authority, fear and scarcity. Links are
                    checked against VirusTotal&rsquo;s threat intelligence.
                </p>
                <p>
                    The result is two CVSS-style scores out of 10 &mdash; phishing probability and sophistication &mdash;
                    with a plain-language explanation, so you know
                    not just <em>whether</em> to worry, but <em>why</em> &mdash; and what to do next.
                </p>
            </div>
        </section>

        <section class="split reveal">
            <div>
                <div class="eyebrow">02</div>
                <h2>How it works</h2>
            </div>
            <div class="split-body">
                <ol class="num-list">
                    <li><span><strong>Cleaning</strong> &mdash; the text is stripped of noise, de-obfuscated, and personal details are masked.</span></li>
                    <li><span><strong>Classification</strong> &mdash; a trained model estimates how likely the email is to be phishing.</span></li>
                    <li><span><strong>Technique detection</strong> &mdash; the wording is scanned for manipulation tactics and blended into the sophistication score.</span></li>
                    <li><span><strong>Link intelligence</strong> &mdash; URLs are checked against VirusTotal&rsquo;s scanning engines.</span></li>
                </ol>
            </div>
        </section>

        <section class="split reveal">
            <div>
                <div class="eyebrow">03</div>
                <h2>CVSS-style scores</h2>
            </div>
            <div class="split-body">
                <p>
                    Every analysis gets two scores from 0.0 to 10.0: <strong>phishing probability</strong>
                    (how likely the email is phishing) and <strong>sophistication</strong> (how convincing its
                    manipulation is). Both use the CVSS severity bands:
                </p>
                <ul class="def-list">
                    <li><strong><x-risk-badge :probability="0.2" /></strong><span>0.1&ndash;3.9 &middot; little sign of phishing (0.0 is None)</span></li>
                    <li><strong><x-risk-badge :probability="0.55" /></strong><span>4.0&ndash;6.9 &middot; warning signs worth a second look</span></li>
                    <li><strong><x-risk-badge :probability="0.8" /></strong><span>7.0&ndash;8.9 &middot; strong phishing indicators</span></li>
                    <li><strong><x-risk-badge :probability="0.95" /></strong><span>9.0&ndash;10.0 &middot; treat as a phishing attack</span></li>
                </ul>
            </div>
        </section>

        <section class="split reveal">
            <div>
                <div class="eyebrow">04</div>
                <h2>Built with</h2>
            </div>
            <div class="split-body">
                <ul class="def-list">
                    <li><strong>Python</strong><span>FastAPI, scikit-learn and spaCy &mdash; the detection engine</span></li>
                    <li><strong>Laravel</strong><span>The web application and analysis history</span></li>
                    <li><strong>Chrome</strong><span>A Gmail extension that analyzes the message you are reading</span></li>
                    <li><strong>VirusTotal</strong><span>Link reputation intelligence</span></li>
                </ul>
            </div>
        </section>

        <section class="split reveal">
            <div>
                <div class="eyebrow">05</div>
                <h2>Privacy</h2>
            </div>
            <div class="split-body">
                <p>
                    Emails you submit are used only to produce your result. Email addresses, phone numbers and
                    card numbers are masked automatically before analysis. Only a short, masked excerpt is stored
                    with each analysis, and you can delete any analysis &mdash; or your whole account and
                    everything tied to it &mdash; at any time.
                </p>
            </div>
        </section>
    </div>
</div>

@endsection
