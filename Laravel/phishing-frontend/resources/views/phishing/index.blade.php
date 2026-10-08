@extends('layouts.site')

@section('title', 'PanshengGuard — See the threat before you click')

{{-- This page presents analysis errors inside the scanner itself. --}}
@section('inline-error', '1')

@section('content')

    @php
        $scanError = session('error');
        $initialState = $scanError ? 'is-error' : 'is-idle';
    @endphp

    {{-- ==================================================================
         Hero
         ================================================================== --}}
    <section class="hero" data-hero>
        {{-- Cursor-following "threat lens": a faint field of example phishing
             wording sits behind the headline; wherever the cursor goes, the
             lens reveals the manipulation inside it. Illustrative copy only -
             it is decoration, not analysis. Built by public/js/hero.js. --}}
        <div class="hero-field" aria-hidden="true" data-hero-field>
            <div class="field-layer field-base" data-field-base></div>
            <div class="field-layer field-reveal" data-field-reveal></div>
            <div class="hero-lens" data-lens>
                <span class="lens-tick t"></span><span class="lens-tick r"></span><span class="lens-tick b"></span><span class="lens-tick l"></span>
                <span class="lens-readout" data-lens-readout>Scanning</span>
            </div>
        </div>

        <div class="container hero-content">
            <div class="eyebrow fade-up">Email threat analysis</div>
            <h1 class="hero-title fade-up d1">See the threat <span class="muted">before you click.</span></h1>
            <p class="lead fade-up d2">
                Analyze suspicious emails with PanshengGuard and understand
                the signals behind potential phishing threats.
            </p>
            <div class="btn-row fade-up d3">
                <a href="#scanner" class="btn btn-primary btn-lg btn-label-caps" data-focus-scanner data-magnetic>
                    Analyze email
                    <x-icon name="arrow-right" class="icon-trail" />
                </a>
                <a href="{{ Route::has('history') ? route('history') : '#' }}" class="btn btn-secondary btn-lg btn-label-caps" data-magnetic>
                    View history
                </a>
            </div>
            <div class="hero-meta fade-up d4">
                <span><x-icon name="cpu" /> Trained classifier</span>
                <span><x-icon name="mask" /> Manipulation detection</span>
                <span><x-icon name="globe" /> VirusTotal link intelligence</span>
            </div>
        </div>
    </section>

    {{-- ==================================================================
         Scanner
         ================================================================== --}}
    <section class="scanner-section" id="scanner">
        <div class="container">
            <div class="scanner {{ $initialState }} fade-up d4" data-scanner="intake" data-spotlight>

                <div class="scanner-bar">
                    <span class="scanner-bar-brand"><x-brand-mark /> PanshengGuard</span>
                    <span class="scanner-bar-sep" aria-hidden="true"></span>
                    <span class="scanner-bar-title" data-scan-title>{{ $scanError ? 'Analysis interrupted' : 'Analyze an email' }}</span>
                    <div class="scanner-bar-right">
                        <span class="status-pill {{ $scanError ? 'is-error' : '' }}" data-scan-status aria-live="polite">
                            <span class="status-dot"></span>
                            <span data-scan-status-text>{{ $scanError ? 'Not checked' : 'Ready' }}</span>
                        </span>
                    </div>
                </div>

                <div class="scanner-grid">
                    {{-- LEFT: input / live preview --}}
                    <div class="scanner-main">
                        <div class="scanner-heading">
                            <h2>Analyze an Email</h2>
                            <p>Paste or enter the email content you want to analyze &mdash; subject line first, then the body.</p>
                        </div>

                        <form action="{{ route('analyze') }}" method="POST" id="scanForm" data-no-busy>
                            @csrf

                            <div class="email-frame">
                                <div class="email-frame-head">
                                    <span>Email content</span>
                                    <span class="counter" data-char-count>0 characters</span>
                                </div>

                                <div data-when="idle error">
                                    <label for="email_text" class="sr-only">Email content</label>
                                    <textarea
                                        id="email_text"
                                        name="email_text"
                                        rows="12"
                                        placeholder="Urgent: Account Verification Required&#10;&#10;Dear customer, your account requires immediate verification…"
                                        required
                                    >{{ old('email_text') }}</textarea>
                                </div>

                                {{-- Read-only preview shown while the request is in flight.
                                     Filled from the textarea by scanner.js. --}}
                                <div class="email-doc" data-when="analyzing" data-email-doc>
                                    <div class="scanline" aria-hidden="true"></div>
                                    <div class="email-doc-text" data-preview></div>
                                </div>
                            </div>

                            @error('email_text')
                                <div class="alert alert-error" style="margin-top: 12px;">
                                    <x-icon name="alert-circle" />
                                    <span>{{ $message }}</span>
                                </div>
                            @enderror

                            <div class="scanner-footer">
                                <div class="scanner-footer-left">
                                    <label class="check">
                                        <input type="checkbox" name="check_urls" value="1" checked>
                                        Check links with VirusTotal
                                    </label>
                                    <button type="button" class="text-btn flex" data-sample data-when="idle error">
                                        <x-icon name="file-text" />
                                        Use a sample email
                                    </button>
                                </div>

                                <button type="submit" class="btn btn-primary btn-lg btn-label-caps" data-submit>
                                    <x-icon name="scan" />
                                    <span data-submit-label>Analyze email</span>
                                </button>
                            </div>
                        </form>
                    </div>

                    {{-- RIGHT: what happens / live progress / error --}}
                    <div class="scanner-side">

                        {{-- Idle: the pipeline the email will go through --}}
                        <div data-when="idle">
                            <div class="side-label">What happens</div>
                            <ol class="stages pipeline">
                                @foreach ([
                                    ['Email content',           'The text is cleaned and normalised.'],
                                    ['Suspicious phrases',      'Wording is checked against known phishing patterns.'],
                                    ['Manipulation techniques', 'Urgency, false authority, fear and scarcity are identified.'],
                                    ['Threat intelligence',     'Links are checked against VirusTotal.'],
                                    ['Threat assessment',       'Probability and sophistication are each scored CVSS-style, out of 10.'],
                                ] as [$title, $desc])
                                    <li class="stage">
                                        <span class="stage-dot"></span>
                                        <div class="stage-body">
                                            <div class="stage-title">{{ $title }}</div>
                                            <div class="stage-desc">{{ $desc }}</div>
                                        </div>
                                    </li>
                                @endforeach
                            </ol>
                        </div>

                        {{-- Analyzing: visual progress while the real request runs.
                             Steps advance on the client only; the final step stays
                             open until the server's answer arrives. --}}
                        <div data-when="analyzing" aria-live="polite">
                            <div class="side-label">Analyzing this email&hellip;</div>
                            <ol class="stages" data-live-stages>
                                <li class="stage" data-stage="content">
                                    <span class="stage-dot"><x-icon name="check" /></span>
                                    <div class="stage-body">
                                        <div class="stage-title">Email content</div>
                                        <div class="stage-desc">Reading the message.</div>
                                    </div>
                                </li>
                                <li class="stage" data-stage="phrases">
                                    <span class="stage-dot"><x-icon name="check" /></span>
                                    <div class="stage-body">
                                        <div class="stage-title">Suspicious phrases</div>
                                        <div class="stage-desc">Checking the wording.</div>
                                    </div>
                                </li>
                                <li class="stage" data-stage="intel">
                                    <span class="stage-dot"><x-icon name="check" /></span>
                                    <div class="stage-body">
                                        <div class="stage-title">Threat intelligence</div>
                                        <div class="stage-desc" data-intel-desc>Waiting for the analysis service.</div>
                                    </div>
                                </li>
                                <li class="stage" data-stage="score">
                                    <span class="stage-dot"><x-icon name="check" /></span>
                                    <div class="stage-body">
                                        <div class="stage-title">Threat assessment</div>
                                        <div class="stage-desc">Generated when the analysis returns.</div>
                                    </div>
                                </li>
                            </ol>
                        </div>

                        {{-- Error: the existing error message, presented properly --}}
                        <div data-when="error">
                            <div class="scan-error" role="alert">
                                <span class="scan-error-icon"><x-icon name="alert-triangle" /></span>
                                <h3>Could not check this email</h3>
                                <p>The analysis did not complete, so no assessment was made. Your email is still in the box &mdash; nothing was lost.</p>
                                @if ($scanError)
                                    <div class="detail">{{ $scanError }}</div>
                                @endif
                                <div class="btn-row">
                                    <button type="submit" form="scanForm" class="btn btn-primary btn-label-caps">
                                        <x-icon name="refresh" />
                                        Try again
                                    </button>
                                    <button type="button" class="btn btn-ghost" data-edit-email>Edit email</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    {{-- ==================================================================
         Recent analyses (signed-in users)
         ================================================================== --}}
    @auth
        @php
            // Read-only: the same records the History page lists.
            $recentScans = \App\Models\Scan::where('user_id', auth()->id())->latest()->limit(4)->get();
        @endphp
        @if ($recentScans->isNotEmpty())
            <section class="section section-subtle">
                <div class="container">
                    <div class="page-head-row" style="margin-bottom: 32px;">
                        <div class="section-head" style="margin-bottom: 0;">
                            <div class="eyebrow">Analysis history</div>
                            <h2>Your recent analyses</h2>
                        </div>
                        <a href="{{ route('history') }}" class="link-arrow">View all history <x-icon name="arrow-right" /></a>
                    </div>
                    @include('partials.scan-list', ['scans' => $recentScans])
                </div>
            </section>
        @endif
    @endauth

    {{-- ==================================================================
         How it works
         ================================================================== --}}
    <section class="section">
        <div class="container">
            <div class="section-head reveal">
                <div class="eyebrow">How it works</div>
                <h2>Four checks. One clear answer.</h2>
                <p>Every email goes through the same pipeline, and every finding is shown to you &mdash; not hidden behind a single number.</p>
            </div>

            <div class="process reveal">
                @foreach ([
                    ['icon' => 'sparkles', 'title' => 'Clean',          'body' => 'The text is stripped to its core wording, with personal details masked before analysis.'],
                    ['icon' => 'cpu',      'title' => 'Classify',       'body' => 'A trained model reads the wording and the structure of links and sender.'],
                    ['icon' => 'mask',     'title' => 'Detect tactics', 'body' => 'Urgency, false authority, fear and scarcity language is identified and highlighted.'],
                    ['icon' => 'globe',    'title' => 'Check links',    'body' => "Any URLs are checked against VirusTotal's threat intelligence."],
                ] as $i => $step)
                    <div class="process-item">
                        <div class="process-num">0{{ $i + 1 }}</div>
                        <div class="process-icon"><x-icon :name="$step['icon']" /></div>
                        <h3>{{ $step['title'] }}</h3>
                        <p>{{ $step['body'] }}</p>
                    </div>
                @endforeach
            </div>
        </div>
    </section>

    {{-- ==================================================================
         CVSS-style scale
         ================================================================== --}}
    <section class="section section-subtle">
        <div class="container">
            <div class="section-head reveal" style="margin-bottom: 0;">
                <div class="eyebrow">CVSS-style scoring</div>
                <h2>Two scores, both out of 10.</h2>
                <p>
                    <strong>Phishing probability</strong> is how likely the email is to be phishing.
                    <strong>Sophistication</strong> is how convincing its tactics are. Both use the
                    familiar CVSS severity bands &mdash; higher means more dangerous.
                </p>
            </div>
            <div class="band-scale reveal">
                @foreach ([
                    ['low', '0.0', 'None'],
                    ['low', '0.1–3.9', 'Low'],
                    ['moderate', '4.0–6.9', 'Medium'],
                    ['high', '7.0–8.9', 'High'],
                    ['critical', '9.0–10.0', 'Critical'],
                ] as [$b, $range, $name])
                    <div class="band-step band-{{ $b }}">
                        <div class="band-step-range">{{ $range }}</div>
                        <div class="band-step-name">{{ $name }}</div>
                    </div>
                @endforeach
            </div>
        </div>
    </section>

@endsection

@push('scripts')
    <script src="{{ asset('js/scanner.js') }}?v=3" defer></script>
    <script src="{{ asset('js/hero.js') }}?v=1" defer></script>
@endpush
