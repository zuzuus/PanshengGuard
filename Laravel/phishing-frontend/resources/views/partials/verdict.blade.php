{{--
    Shared verdict report.

    Rendered by both phishing/result.blade.php (fresh analysis, reading the API
    response array) and history/show.blade.php (a saved Scan model). Callers
    normalise their data into the variables below and include this once.

    Layout note: only the verdict itself is a raised card. Everything below it
    is a flat section on the page background, divided by hairlines. Previously
    all five blocks were equally elevated cards, so the answer the whole tool
    exists to produce carried no more visual weight than the URL list under it.

    Expects:
      $label           string  "PHISHING" | "LEGITIMATE"
      $risk            string  "Low Risk" | "Moderate Risk" | "High Risk" | "Critical Risk"
      $probability     float   0.0-1.0
      $sophistication  float   0-100
      $techniques      array   technique => list of matched keywords
      $tips            array   list of ['technique', 'warning', 'advice']
      $checklist       array   list of strings
      $urlResults      array   list of ['url', 'status', 'malicious', 'suspicious', 'total']
      $signals         array   plain-English red flags from the features.py block
      $linkTrusted     ?bool   does the mail link to a known-good domain (host-parsed)
      $cleanTokens     ?string the lemmatised text the classifier actually saw
--}}

@php
    $riskClass = match($risk) {
        'Low Risk' => 'risk-low',
        'Moderate Risk' => 'risk-moderate',
        'High Risk' => 'risk-high',
        'Critical Risk' => 'risk-critical',
        default => 'risk-low',
    };
    $gaugeColor = match($risk) {
        'Low Risk' => 'var(--risk-low)',
        'Moderate Risk' => 'var(--risk-moderate)',
        'High Risk' => 'var(--risk-high)',
        'Critical Risk' => 'var(--risk-critical)',
        default => 'var(--risk-moderate)',
    };
    $isPhishing = $label === 'PHISHING';
    $probabilityPct = round($probability * 100, 1);

    $anyTechnique = collect($techniques)->contains(fn ($hits) => count($hits) > 0);
@endphp

<div class="card card-feature verdict-card">
    <div class="verdict-top">
        <span class="verdict-seal {{ $isPhishing ? 'is-red' : 'is-green' }}">
            <x-icon :name="$isPhishing ? 'shield-x' : 'shield-check'" />
        </span>
        <div class="verdict-headline">
            <span class="verdict-classification">{{ $label }}</span>
            <span class="badge badge-lg {{ $riskClass }}">{{ $risk }}</span>
        </div>
    </div>

    <div class="verdict-stats">
        <div class="gauge-stat">
            {{-- Coloured by severity: this gauge encodes risk. --}}
            <div class="gauge" style="--pct: {{ $probabilityPct }}; --gauge-color: {{ $gaugeColor }};">
                <div class="gauge-value">{{ $probabilityPct }}%</div>
            </div>
            <div class="label">Phishing Probability</div>
        </div>
        <div class="gauge-stat">
            {{-- Deliberately neutral: sophistication is a measurement, not a
                 severity, and colouring it would imply a second risk reading. --}}
            <div class="gauge" style="--pct: {{ $sophistication }}; --gauge-color: var(--gauge-neutral);">
                <div class="gauge-value">{{ $sophistication }}%</div>
            </div>
            <div class="label">Sophistication Score</div>
        </div>
    </div>
</div>

<div class="report">

    {{-- First, because it is the explanation of the verdict directly above it.
         These come from the structural feature block, not the keyword rules:
         raw-IP links, typosquatted domains, sender/link mismatch, credential
         requests. This is the difference between "93% phishing" and "93%
         phishing, because the domain is a near-miss for Maybank and it is
         asking for your TAC". --}}
    <section class="report-section">
        <div class="report-header">
            <span class="report-icon {{ !empty($signals) ? 'is-red' : 'is-green' }}">
                <x-icon name="flag" />
            </span>
            <h2>Why This Verdict</h2>
        </div>

        @if (!empty($signals))
            <ul class="signal-list">
                @foreach ($signals as $signal)
                    <li>{{ $signal }}</li>
                @endforeach
            </ul>
        @else
            <p class="text-muted">
                No structural red flags fired on this email &mdash; no disguised links,
                no credential request, no sender mismatch.
            </p>
        @endif

        @if (!is_null($linkTrusted))
            <div class="signal-trust {{ $linkTrusted ? 'is-trusted' : '' }}">
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
    </section>

    <section class="report-section">
        <div class="report-header">
            <span class="report-icon"><x-icon name="mask" /></span>
            <h2>Manipulation Techniques</h2>
        </div>

        @if ($anyTechnique)
            <dl class="technique-list">
                @foreach ($techniques as $technique => $hits)
                    @if (count($hits) > 0)
                        <dt>{{ ucfirst($technique) }}</dt>
                        <dd>
                            @foreach ($hits as $hit)
                                <span class="tag">{{ $hit }}</span>
                            @endforeach
                        </dd>
                    @endif
                @endforeach
            </dl>
        @else
            <p class="text-muted">No manipulation techniques detected.</p>
        @endif
    </section>

    @if (!empty($tips))
        <section class="report-section">
            <div class="report-header">
                <span class="report-icon"><x-icon name="lightbulb" /></span>
                <h2>What This Means &amp; What To Do</h2>
            </div>
            @foreach ($tips as $tip)
                <div class="tip-box">
                    <div class="tip-title">{{ ucfirst($tip['technique']) }} detected</div>
                    <p class="tip-warning">{{ $tip['warning'] }}</p>
                    <p class="tip-advice"><em>{{ $tip['advice'] }}</em></p>
                </div>
            @endforeach
        </section>
    @endif

    @if (!empty($checklist))
        <section class="report-section">
            <div class="report-header">
                <span class="report-icon is-green"><x-icon name="clipboard-check" /></span>
                <h2>Safety Checklist</h2>
            </div>
            <ul class="checklist">
                @foreach ($checklist as $item)
                    <li>{{ $item }}</li>
                @endforeach
            </ul>
        </section>
    @endif

    <section class="report-section">
        <div class="report-header">
            <span class="report-icon"><x-icon name="link" /></span>
            <h2>URL Scan <span class="report-note">VirusTotal</span></h2>
        </div>

        @if (empty($urlResults))
            <p class="text-muted">No URLs found or scanning was disabled.</p>
        @else
            @foreach ($urlResults as $url)
                @php
                    [$statusIcon, $statusClass, $statusLabel, $statusDetail] = match ($url['status']) {
                        'malicious'  => ['shield-x',       'url-status-malicious',  'Malicious',   "{$url['malicious']}/{$url['total']} engines flagged this link"],
                        'suspicious' => ['alert-triangle', 'url-status-suspicious', 'Suspicious',  "{$url['suspicious']}/{$url['total']} engines flagged this link"],
                        'clean'      => ['check-circle',   'url-status-clean',      'Clean',       "0/{$url['total']} engines flagged this link"],
                        default      => ['help-circle',    'url-status-error',      'Not scanned', 'This link could not be checked'],
                    };
                @endphp
                <div class="url-row">
                    <span class="{{ $statusClass }}"><x-icon :name="$statusIcon" /></span>
                    <div class="url-row-body">
                        <strong class="{{ $statusClass }}">{{ $statusLabel }}</strong>
                        <span class="text-muted">&mdash; {{ $statusDetail }}</span>
                        <div><code>{{ $url['url'] }}</code></div>
                    </div>
                </div>
            @endforeach
        @endif
    </section>

    @if (!empty($cleanTokens))
        {{-- Collapsed by default: a normal user does not need it, but it is the
             honest answer when someone asks what the classifier actually read.
             Stopwords, punctuation and short tokens are gone; what remains are
             the lemmas that became the TF-IDF vector. --}}
        <section class="report-section">
            <details class="model-input">
                <summary>
                    <x-icon name="terminal" />
                    What the model actually read
                </summary>
                <p class="model-input-note">
                    Your email after cleaning &mdash; lowercased, stopwords and punctuation
                    removed, each word reduced to its base form. This is the text that
                    became the classifier's input.
                </p>
                <code class="model-input-tokens">{{ $cleanTokens }}</code>
            </details>
        </section>
    @endif

</div>
