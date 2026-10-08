@extends('layouts.site')

@section('title', 'Dashboard — PanshengGuard')

@section('content')

<div class="container">
    <header class="page-head">
        <div class="page-head-row">
            <div>
                <div class="eyebrow">Overview</div>
                <h1>Dashboard</h1>
                <p class="lead">
                    @if ($totalScans === 0)
                        Nothing to summarise yet &mdash; this page fills in as you analyze emails.
                    @else
                        A summary of every email you&rsquo;ve analyzed with PanshengGuard.
                    @endif
                </p>
            </div>
            <a href="{{ route('home') }}#scanner" class="btn btn-primary btn-label-caps">
                <x-icon name="scan" />
                Analyze email
            </a>
        </div>
    </header>

    <div class="page-body">
    @if ($totalScans === 0)
        {{-- First run: say what this page will become, and point at the one
             action that fills it. --}}
        <div class="panel">
            <div class="empty-state">
                <div class="empty-state-icon"><x-icon name="bar-chart" /></div>
                <h3>Your dashboard starts empty</h3>
                <p>
                    Once you analyze your first email, this page tracks how many you&rsquo;ve checked,
                    how many were phishing, the tactics you meet most often, and your activity over the last two weeks.
                </p>
                <a href="{{ route('home') }}#scanner" class="btn btn-primary">
                    <x-icon name="scan" />
                    Analyze your first email
                </a>
            </div>
        </div>
    @else
        @php
            // Read-only: CVSS-style phishing-probability scores across all of
            // this user's saved scans (probability 0–1 shown as 0.0–10.0).
            $bandDefs = [
                'critical' => ['Critical', '9.0–10.0'],
                'high'     => ['High', '7.0–8.9'],
                'moderate' => ['Medium', '4.0–6.9'],
                'low'      => ['Low / None', '0.0–3.9'],
            ];
            $bandCounts = array_fill_keys(array_keys($bandDefs), 0);
            $cvssScores = \App\Models\Scan::where('user_id', auth()->id())->pluck('probability')
                ->map(fn ($p) => round(((float) $p) * 100) / 10);
            $cvssScores->each(function ($v) use (&$bandCounts) {
                $key = $v < 4.0 ? 'low' : ($v < 7.0 ? 'moderate' : ($v < 9.0 ? 'high' : 'critical'));
                $bandCounts[$key]++;
            });
            $avgCvss = $cvssScores->count() ? round($cvssScores->avg(), 1) : 0.0;
            $maxBand = max(1, max($bandCounts));
            $tqLabels = ['urgency' => 'Urgency', 'authority' => 'False Authority', 'fear' => 'Fear', 'scarcity' => 'Scarcity'];
        @endphp

        <div class="stats reveal">
            <div class="stat">
                <div class="stat-k">Emails analyzed</div>
                <div class="stat-v">{{ $totalScans }}</div>
                <div class="stat-note">All time</div>
            </div>
            <div class="stat">
                <div class="stat-k">Classified phishing</div>
                <div class="stat-v is-danger">{{ $phishingCount }}</div>
                <div class="stat-note">{{ $legitimateCount }} legitimate</div>
            </div>
            <div class="stat">
                <div class="stat-k">Avg. phishing probability</div>
                <div class="stat-v">{{ number_format($avgCvss, 1) }} <small>/ 10</small></div>
                <div class="stat-note">CVSS-style, across your analyses</div>
            </div>
            <div class="stat">
                <div class="stat-k">Top tactic</div>
                <div class="stat-v is-word">{{ $tqLabels[$topTechnique] ?? ucfirst($topTechnique) }}</div>
                <div class="stat-note">Most frequent manipulation</div>
            </div>
        </div>

        <div class="dash-grid">
            <section class="panel panel-pad reveal">
                <div class="panel-head">
                    <div>
                        <h3>Last 14 days</h3>
                        <p>Analyses per day, by classification.</p>
                    </div>
                </div>
                <div class="chart-wrap">
                    <canvas id="trendChart" aria-label="Analyses over the last 14 days"></canvas>
                </div>
            </section>

            <section class="panel panel-pad reveal">
                <div class="panel-head">
                    <div>
                        <h3>Phishing probability</h3>
                        <p>Your analyses by CVSS-style severity, out of 10.</p>
                    </div>
                </div>
                <div class="dist">
                    @foreach ($bandDefs as $key => [$name, $range])
                        <div class="dist-row band-{{ $key }}">
                            <span><strong style="font-weight: 600;">{{ $name }}</strong> <span class="text-muted mono" style="font-size: .75rem;">{{ $range }}</span></span>
                            <span class="dist-count">{{ $bandCounts[$key] }}</span>
                            <div class="dist-bar"><span style="width: {{ round($bandCounts[$key] / $maxBand * 100) }}%;"></span></div>
                        </div>
                    @endforeach
                </div>
            </section>
        </div>

        <section class="reveal" style="margin-top: 48px;">
            <div class="page-head-row" style="margin-bottom: 20px;">
                <div>
                    <div class="eyebrow">Analysis history</div>
                    <h2 style="margin-top: 10px;">Recent analyses</h2>
                </div>
                <a href="{{ route('history') }}" class="link-arrow">View all history <x-icon name="arrow-right" /></a>
            </div>
            @include('partials.scan-list', ['scans' => $recentScans])
        </section>
    @endif
    </div>
</div>

@endsection

@if ($totalScans > 0)
@push('scripts')
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
    (function () {
        const canvas = document.getElementById('trendChart');
        if (!canvas || typeof Chart === 'undefined') return;

        let chart = null;

        // Colours come from the theme tokens, so the chart follows light/dark.
        function draw() {
            const css = getComputedStyle(document.documentElement);
            const token = (name, fallback) => (css.getPropertyValue(name).trim() || fallback);

            const phish = token('--risk-vhigh', '#DC2626');
            const legit = token('--accent', '#2563EB');
            const text  = token('--text', '#0B1426');
            const muted = token('--text-3', '#6B7689');
            const line  = token('--line', '#E4E8EF');
            const surface = token('--surface-raised', '#FFFFFF');

            Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
            Chart.defaults.font.size = 11;

            if (chart) chart.destroy();

            chart = new Chart(canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: @json($chartLabels),
                    datasets: [
                        {
                            label: 'Phishing',
                            data: @json($chartPhishing),
                            backgroundColor: phish,
                            borderRadius: 3,
                            maxBarThickness: 18,
                        },
                        {
                            label: 'Legitimate',
                            data: @json($chartLegitimate),
                            backgroundColor: legit,
                            borderRadius: 3,
                            maxBarThickness: 18,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 700, easing: 'easeOutQuart' },
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: {
                            align: 'end',
                            labels: { color: muted, usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 8, boxHeight: 8, padding: 16 }
                        },
                        tooltip: {
                            backgroundColor: surface,
                            borderColor: line,
                            borderWidth: 1,
                            titleColor: text,
                            bodyColor: muted,
                            padding: 10,
                            cornerRadius: 8,
                            usePointStyle: true,
                        }
                    },
                    scales: {
                        x: {
                            stacked: true,
                            ticks: { color: muted, maxRotation: 0, autoSkipPadding: 14 },
                            grid: { display: false },
                            border: { color: line },
                        },
                        y: {
                            stacked: true,
                            ticks: { color: muted, stepSize: 1, precision: 0, padding: 8 },
                            grid: { color: line },
                            border: { display: false },
                            beginAtZero: true,
                        }
                    }
                }
            });
        }

        draw();
        document.addEventListener('pg:themechange', draw);
    })();
</script>
@endpush
@endif
