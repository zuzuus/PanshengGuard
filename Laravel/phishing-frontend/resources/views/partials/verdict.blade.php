{{--
    Shared PanshengGuard report: the result scanner (email + threat assessment)
    followed by the full analysis.

    Rendered by phishing/result.blade.php (fresh analysis, reading the API
    response array) and history/show.blade.php (a saved Scan model). Callers
    normalise their data into the variables below and include this once.

    Everything shown here comes from the existing API response / Scan record.
    The only derived values are the CVSS-style 0.0–10.0 scores, display conversions of the
    existing sophistication_score (0–100): ceil(score / 10), minimum 1.

    Expects:
      $label           string  "PHISHING" | "LEGITIMATE"
      $risk            string  the API's own risk label (kept, shown in model details)
      $probability     float   0.0-1.0
      $sophistication  float   0-100
      $techniques      array   technique => list of matched keywords
      $tips            array   list of ['technique', 'warning', 'advice']
      $checklist       array   list of strings
      $urlResults      array   list of ['url', 'status', 'malicious', 'suspicious', 'total']
      $signals         array   plain-English red flags from the features.py block
      $linkTrusted     ?bool   does the mail link to a known-good domain (host-parsed)
      $cleanTokens     ?string the lemmatised text the classifier actually saw
    Optional:
      $emailText       ?string text to show in the email panel
      $emailIsExcerpt  bool    true when $emailText is the stored, masked 200-char snippet
      $animate         bool    replay the scan sequence on load (fresh results only)
      $savedReportUrl  ?string link to the stored report, when there is one
      $scannedAt       ?string timestamp line for stored reports
      $context         string  'result' | 'history'
--}}

@php
    $emailText      = $emailText ?? null;
    $emailIsExcerpt = $emailIsExcerpt ?? false;
    $animate        = $animate ?? false;
    $savedReportUrl = $savedReportUrl ?? null;
    $scannedAt      = $scannedAt ?? null;
    $context        = $context ?? 'result';

    // ---- CVSS-style 0.0–10.0 scores (display conversion only) ----
    // Both come straight from the API: phishing probability (0–1) and the
    // sophistication score (0–100), each shown on one decimal out of 10 with
    // the CVSS v3 severity bands: None 0.0 · Low 0.1–3.9 · Medium 4.0–6.9 ·
    // High 7.0–8.9 · Critical 9.0–10.0. Scoring itself is untouched.
    $cvssSeverity = fn (float $v) => match (true) {
        $v <= 0.0 => ['low', 'None'],
        $v < 4.0  => ['low', 'Low'],
        $v < 7.0  => ['moderate', 'Medium'],
        $v < 9.0  => ['high', 'High'],
        default   => ['critical', 'Critical'],
    };
    $probScore = round(((float) $probability) * 100) / 10;
    $sophScore = round((float) $sophistication) / 10;
    [$probBand, $probSev] = $cvssSeverity($probScore);
    [$sophBand, $sophSev] = $cvssSeverity($sophScore);
    $band = $probBand; // the card's accent follows the phishing probability

    $isPhishing = $label === 'PHISHING';

    // Presentation copy for each technique the scoring service can report.
    $techniqueMeta = [
        'urgency'   => ['label' => 'Urgency',         'desc' => 'Pressure to act quickly, before there is time to verify.'],
        'authority' => ['label' => 'False Authority', 'desc' => 'Claims to speak for a bank, government body, or internal department.'],
        'fear'      => ['label' => 'Fear',            'desc' => 'Threats of suspension, loss of access, or consequences.'],
        'scarcity'  => ['label' => 'Scarcity',        'desc' => 'Limited time, one attempt, or an exclusive offer.'],
    ];

    $detected = collect($techniques ?? [])
        ->filter(fn ($hits) => is_array($hits) && count($hits) > 0);

    $tipsByTechnique = collect($tips ?? [])->keyBy('technique');

    $urlResults = $urlResults ?? [];
    $linksChecked = count($urlResults);
    $linksFlagged = collect($urlResults)->filter(fn ($u) => in_array($u['status'] ?? '', ['malicious', 'suspicious'], true))->count();
    $linksClean   = collect($urlResults)->where('status', 'clean')->count();
    $signals = $signals ?? [];
@endphp

{{-- ======================================================================
     Result scanner
     ====================================================================== --}}
<div class="scanner is-result band-{{ $band }}"
     id="resultScanner"
     data-scanner="result"
     data-animate="{{ $animate ? '1' : '0' }}">

    <div class="scanner-bar">
        <span class="scanner-bar-brand"><x-brand-mark /> PanshengGuard</span>
        <span class="scanner-bar-sep" aria-hidden="true"></span>
        <span class="scanner-bar-title" data-scan-title>Threat assessment</span>
        <div class="scanner-bar-right">
            <button type="button" class="skip-btn" data-skip hidden>Skip</button>
            <span class="status-pill is-done" data-scan-status>
                <span class="status-dot"></span>
                <span data-scan-status-text>Complete</span>
            </span>
        </div>
    </div>

    <div class="scanner-grid">
        {{-- LEFT: the email --}}
        <div class="scanner-main">
            <div class="scanner-heading">
                <div class="eyebrow eyebrow-muted eyebrow-plain">{{ $scannedAt ? 'Analyzed ' . $scannedAt : 'Analyzed email' }}</div>
            </div>

            <div class="email-frame">
                <div class="email-frame-head">
                    <span>{{ $emailIsExcerpt ? 'Stored excerpt' : 'Email content' }}</span>
                    <span class="counter" data-phrase-count>
                        {{ $detected->flatten()->count() }} {{ \Illuminate\Support\Str::plural('term', $detected->flatten()->count()) }} matched
                    </span>
                </div>

                <div class="email-doc" data-email-doc>
                    <div class="scanline" aria-hidden="true"></div>
                    @if (filled($emailText))
                        <div class="email-doc-text"
                             data-email-text
                             data-techniques="{{ json_encode($detected->all()) }}">{{ $emailText }}</div>
                    @else
                        <div class="email-doc-text text-muted">The email text is not stored for this scan.</div>
                    @endif
                </div>

                @if ($emailIsExcerpt)
                    <div class="email-doc-note">
                        <x-icon name="lock" />
                        Only the first 200 characters are kept, with personal details masked.
                    </div>
                @endif
            </div>
        </div>

        {{-- RIGHT: threat assessment --}}
        <div class="scanner-side">
            <div class="assessment">
                <div class="assess-progress" data-assess-progress>
                    <div class="side-label">Analysis</div>
                    <ol class="stages">
                        <li class="stage is-done" data-stage="content">
                            <span class="stage-dot"><x-icon name="check" /></span>
                            <div class="stage-body">
                                <div class="stage-title">Email content</div>
                                <div class="stage-desc">Message text read and normalised.</div>
                            </div>
                        </li>
                        <li class="stage is-done" data-stage="phrases">
                            <span class="stage-dot"><x-icon name="check" /></span>
                            <div class="stage-body">
                                <div class="stage-title">Suspicious phrases</div>
                                <div class="stage-desc" data-phrase-desc>
                                    {{ $detected->isEmpty() ? 'No flagged wording found.' : 'Flagged wording marked in the email.' }}
                                </div>
                            </div>
                        </li>
                        <li class="stage is-done" data-stage="manipulation">
                            <span class="stage-dot"><x-icon name="check" /></span>
                            <div class="stage-body">
                                <div class="stage-title">Manipulation</div>
                                <div class="stage-detail">
                                    @forelse ($detected as $technique => $hits)
                                        <span class="tq-chip tq-{{ $technique }}" data-reveal>{{ $techniqueMeta[$technique]['label'] ?? ucfirst($technique) }}</span>
                                    @empty
                                        <span class="chip" data-reveal>None detected</span>
                                    @endforelse
                                </div>
                            </div>
                        </li>
                        <li class="stage is-done" data-stage="intel">
                            <span class="stage-dot"><x-icon name="check" /></span>
                            <div class="stage-body">
                                <div class="stage-title">Threat intelligence</div>
                                <div class="stage-detail">
                                    @if ($linksChecked > 0)
                                        <span class="chip chip-mono" data-reveal>{{ $linksChecked }} {{ \Illuminate\Support\Str::plural('link', $linksChecked) }} checked</span>
                                        <span class="chip chip-mono" data-reveal>{{ $linksFlagged }} flagged</span>
                                    @else
                                        <span class="chip chip-mono" data-reveal>No link results</span>
                                    @endif
                                    @if (count($signals) > 0)
                                        <span class="chip chip-mono" data-reveal>{{ count($signals) }} structural {{ \Illuminate\Support\Str::plural('signal', count($signals)) }}</span>
                                    @endif
                                </div>
                            </div>
                        </li>
                        <li class="stage is-done" data-stage="score">
                            <span class="stage-dot"><x-icon name="check" /></span>
                            <div class="stage-body">
                                <div class="stage-title">Scoring</div>
                                <div class="stage-desc">Probability and sophistication rated 0.0&ndash;10.0.</div>
                            </div>
                        </li>
                    </ol>
                </div>

                <div class="assess-result">
                    @foreach ([
                        ['Phishing probability', $probScore, $probBand, $probSev, $isPhishing ? 'Phishing' : 'Legitimate', true, 'How likely it is phishing'],
                        ['Sophistication score', $sophScore, $sophBand, $sophSev, 'CVSS-style', false, 'How convincing the tactics are'],
                    ] as [$mLabel, $mValue, $mBand, $mSev, $mAside, $mPrimary, $mRaw])
                        <div class="cvss band-{{ $mBand }}" data-cvss="{{ number_format($mValue, 1, '.', '') }}" @if ($mPrimary) data-primary @endif>
                            <div class="assess-kicker">
                                <span>{{ $mLabel }}</span>
                                <span>{{ $mAside }}</span>
                            </div>
                            <div class="cvss-row">
                                <div class="score score-sm" aria-label="{{ $mLabel }} {{ number_format($mValue, 1) }} out of 10, {{ $mSev }}">
                                    <span class="score-value" data-cvss-value>{{ number_format($mValue, 1) }}</span>
                                    <span class="score-max">/ 10</span>
                                </div>
                                <div class="cvss-side">
                                    <div class="score-band" data-cvss-sev>{{ $mSev }}</div>
                                    <div class="cvss-raw">{{ $mRaw }}</div>
                                </div>
                            </div>
                            <div class="meter" data-meter aria-hidden="true">
                                @for ($i = 0; $i < 10; $i++)
                                    <span style="--f: {{ max(0, min(1, $mValue - $i)) }};"></span>
                                @endfor
                            </div>
                            <div class="meter-scale cvss-scale" aria-hidden="true">
                                <span style="left: 0;">0.0</span><span style="left: 40%;">Med</span><span style="left: 70%;">High</span><span style="left: 90%;">Crit</span><span style="right: 0; left: auto;">10</span>
                            </div>
                        </div>
                    @endforeach

                    <div class="assess-extra">
                        <div class="assess-block-title">Detected</div>
                        <div class="assess-detected">
                            @forelse ($detected as $technique => $hits)
                                <span class="tq-chip tq-{{ $technique }}">{{ $techniqueMeta[$technique]['label'] ?? ucfirst($technique) }}</span>
                            @empty
                                <span class="chip">No manipulation techniques</span>
                            @endforelse
                        </div>
                    </div>

                    <div class="assess-verdict assess-extra">
                        <x-icon :name="$isPhishing ? 'shield-alert' : 'shield-check'" />
                        <span>Model classification: <strong>{{ $isPhishing ? 'Phishing' : 'Legitimate' }}</strong></span>
                    </div>

                    <div class="assess-actions">
                        <a href="#report" class="btn btn-primary btn-label-caps">
                            View full report
                            <x-icon name="arrow-right" class="icon-trail" />
                        </a>
                        <a href="{{ route('home') }}#scanner" class="btn btn-secondary btn-label-caps">
                            <x-icon name="refresh" />
                            Scan another email
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

{{-- ======================================================================
     Full report
     ====================================================================== --}}
<div class="report" id="report">

    {{-- Detected techniques --}}
    <section class="report-section reveal">
        <div class="report-aside">
            <div class="eyebrow">01 &middot; Techniques</div>
            <h2>Detected techniques</h2>
            <p>Manipulation tactics found in the wording, with the exact terms that matched.</p>
        </div>
        <div class="report-content">
            @if ($detected->isNotEmpty())
                <div class="tq-grid">
                    @foreach ($detected as $technique => $hits)
                        <article class="tq-card tq-{{ $technique }}">
                            <div class="tq-card-head">
                                <span class="tq-chip tq-{{ $technique }}">{{ $techniqueMeta[$technique]['label'] ?? ucfirst($technique) }}</span>
                                <span class="tq-card-count">{{ count($hits) }} {{ \Illuminate\Support\Str::plural('match', count($hits)) }}</span>
                            </div>
                            <p>{{ $tipsByTechnique[$technique]['warning'] ?? ($techniqueMeta[$technique]['desc'] ?? '') }}</p>
                            <div class="tags">
                                @foreach ($hits as $hit)
                                    <span class="tag">{{ $hit }}</span>
                                @endforeach
                            </div>
                        </article>
                    @endforeach
                </div>
            @else
                <div class="empty-line">
                    <x-icon name="check-circle" />
                    No manipulation techniques were detected in this email.
                </div>
            @endif
        </div>
    </section>

    {{-- Explanation --}}
    <section class="report-section reveal">
        <div class="report-aside">
            <div class="eyebrow">02 &middot; Explanation</div>
            <h2>Why this assessment</h2>
            <p>Structural red flags found in the links, the sender and what the message asks for.</p>
        </div>
        <div class="report-content">
            @if (!empty($signals))
                <ul class="signal-list">
                    @foreach ($signals as $signal)
                        <li><x-icon name="alert-triangle" /><span>{{ $signal }}</span></li>
                    @endforeach
                </ul>
            @else
                <div class="empty-line">
                    <x-icon name="check-circle" />
                    No structural red flags &mdash; no disguised links, no credential request, no sender mismatch.
                </div>
            @endif

            @if (!is_null($linkTrusted))
                <div class="trust-note {{ $linkTrusted ? 'is-trusted' : '' }}">
                    <x-icon :name="$linkTrusted ? 'shield-check' : 'help-circle'" />
                    <span>
                        @if ($linkTrusted)
                            Links point at a domain on the known-good list.
                        @else
                            Links do not match any domain on the known-good list.
                        @endif
                    </span>
                </div>
            @endif
        </div>
    </section>

    @if (!empty($tips) || !empty($checklist))
        <section class="report-section reveal">
            <div class="report-aside">
                <div class="eyebrow">03 &middot; Guidance</div>
                <h2>What to do</h2>
                <p>What each tactic is trying to make you do, and how to respond safely.</p>
            </div>
            <div class="report-content">
                @if (!empty($tips))
                    <div class="advice-list">
                        @foreach ($tips as $tip)
                            <div class="advice tq-{{ $tip['technique'] }}">
                                <span class="advice-rail"></span>
                                <div>
                                    <div class="advice-title">{{ $techniqueMeta[$tip['technique']]['label'] ?? ucfirst($tip['technique']) }}</div>
                                    <p>{{ $tip['warning'] }}</p>
                                    <p class="advice-do">{{ $tip['advice'] }}</p>
                                </div>
                            </div>
                        @endforeach
                    </div>
                @endif

                @if (!empty($checklist))
                    <h3 style="margin: {{ !empty($tips) ? '32px' : '0' }} 0 8px;">Safety checklist</h3>
                    <ul class="checklist">
                        @foreach ($checklist as $item)
                            <li><span>{{ $item }}</span></li>
                        @endforeach
                    </ul>
                @endif
            </div>
        </section>
    @endif

    {{-- Threat intelligence --}}
    <section class="report-section reveal">
        <div class="report-aside">
            <div class="eyebrow">{{ (!empty($tips) || !empty($checklist)) ? '04' : '03' }} &middot; Intelligence</div>
            <h2>Threat intelligence</h2>
            <p>Link reputation from VirusTotal&rsquo;s scanning engines.</p>
        </div>
        <div class="report-content">
            @if (empty($urlResults))
                <div class="empty-line neutral">
                    <x-icon name="globe" />
                    No URLs were found, or link scanning was turned off for this analysis.
                </div>
            @else
                <div class="intel-summary">
                    <div><div class="k">Links checked</div><div class="v">{{ $linksChecked }}</div></div>
                    <div><div class="k">Flagged</div><div class="v" style="color: {{ $linksFlagged > 0 ? 'var(--risk-vhigh)' : 'inherit' }}">{{ $linksFlagged }}</div></div>
                    <div><div class="k">Clean</div><div class="v">{{ $linksClean }}</div></div>
                </div>

                @foreach ($urlResults as $url)
                    @php
                        [$statusIcon, $statusClass, $statusLabel, $statusDetail] = match ($url['status']) {
                            'malicious'  => ['shield-x',       'intel-malicious',  'Malicious',   "{$url['malicious']}/{$url['total']} engines"],
                            'suspicious' => ['alert-triangle', 'intel-suspicious', 'Suspicious',  "{$url['suspicious']}/{$url['total']} engines"],
                            'clean'      => ['check-circle',   'intel-clean',      'Clean',       "0/{$url['total']} engines"],
                            default      => ['help-circle',    'intel-error',      'Not scanned', 'Could not be checked'],
                        };
                    @endphp
                    <div class="intel-row">
                        <span class="intel-status {{ $statusClass }}"><x-icon :name="$statusIcon" /> {{ $statusLabel }}</span>
                        <span class="intel-url" title="{{ $url['url'] }}">{{ $url['url'] }}</span>
                        <span class="intel-engines">{{ $statusDetail }}</span>
                    </div>
                @endforeach
            @endif
        </div>
    </section>

    {{-- Model details --}}
    <section class="report-section reveal">
        <div class="report-aside">
            <div class="eyebrow">{{ (!empty($tips) || !empty($checklist)) ? '05' : '04' }} &middot; Model</div>
            <h2>Model details</h2>
            <p>The outputs behind the scores, all on the same CVSS-style 0.0&ndash;10.0 scale.</p>
        </div>
        <div class="report-content">
            <dl class="kv">
                <div><dt>Probability score</dt><dd>{{ number_format($probScore, 1) }} / 10 &middot; {{ $probSev }}</dd></div>
                <div><dt>Sophistication score</dt><dd>{{ number_format($sophScore, 1) }} / 10 &middot; {{ $sophSev }}</dd></div>
                <div><dt>Classification</dt><dd>{{ $isPhishing ? 'Phishing' : 'Legitimate' }}</dd></div>
                <div><dt>Service risk label</dt><dd>{{ $risk }}</dd></div>
            </dl>

            @if (!empty($cleanTokens))
                {{-- Collapsed by default: the honest answer to "what did the
                     classifier actually read?" --}}
                <details class="disclosure">
                    <summary>
                        <x-icon name="chevron-right" class="chev" />
                        What the model actually read
                    </summary>
                    <div class="disclosure-body">
                        <p>
                            Your email after cleaning &mdash; lowercased, stopwords and punctuation removed,
                            each word reduced to its base form. This is the text that became the classifier&rsquo;s input.
                        </p>
                        <code class="token-block">{{ $cleanTokens }}</code>
                    </div>
                </details>
            @endif
        </div>
    </section>

    <div class="report-actions">
        <a href="{{ route('home') }}#scanner" class="btn btn-primary btn-label-caps">
            <x-icon name="scan" />
            Scan another email
        </a>
        <div class="btn-row">
            @if ($savedReportUrl)
                <a href="{{ $savedReportUrl }}" class="btn btn-secondary">
                    Open saved report
                    <x-icon name="arrow-right" class="icon-trail" />
                </a>
            @endif
            @auth
                <a href="{{ route('history') }}" class="btn btn-ghost">Analysis history</a>
            @endauth
        </div>
    </div>
</div>
