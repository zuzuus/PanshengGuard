@extends('layouts.site')

@section('title', 'Dashboard — PanshengGuard')

@section('content')

    <div class="eyebrow">Investigation Summary</div>
    <h1>Dashboard</h1>

    @if ($totalScans === 0)
        {{-- First run. Showing 0 / 0 / 0% / — over an empty chart frame is a
             dead first impression on the best-looking page in the app; say what
             this page will become instead, and point at the one action that
             fills it. --}}
        <p class="section-lead">
            Nothing to summarise yet &mdash; this page fills in as you scan.
        </p>

        <div class="card card-feature onboarding">
            <span class="onboarding-icon"><x-icon name="activity" /></span>
            <h2>Your case file starts empty</h2>
            <p class="onboarding-body">
                Once you analyse your first email, this page tracks how many you've
                checked, how many came back as phishing, which manipulation tactic
                you run into most, and your activity over the last fortnight.
            </p>
            <a href="{{ route('home') }}" class="btn">
                <x-icon name="search" />
                Analyse your first email
            </a>
        </div>

        <div class="report">
            <section class="report-section">
                <div class="report-header">
                    <span class="report-icon"><x-icon name="layers" /></span>
                    <h2>What gets tracked</h2>
                </div>
                <ul class="stack-list">
                    <li><strong>Totals</strong> <span class="text-muted">how many emails you've scanned, and how many were flagged</span></li>
                    <li><strong>Phishing rate</strong> <span class="text-muted">the share of your scans that came back as phishing</span></li>
                    <li><strong>Top tactic</strong> <span class="text-muted">the manipulation technique you encounter most often</span></li>
                    <li><strong>14-day trend</strong> <span class="text-muted">your scanning activity over time</span></li>
                </ul>
            </section>
        </div>
    @else
    <p class="section-lead">
        A summary of everything you've scanned so far.
    </p>

    <div class="stat-grid">
        <div class="card stat-card">
            <div class="label">Total Scans</div>
            <div class="metric">{{ $totalScans }}</div>
        </div>
        <div class="card stat-card">
            <div class="label">Flagged Phishing</div>
            <div class="metric metric-danger">{{ $phishingCount }}</div>
        </div>
        <div class="card stat-card">
            <div class="label">Phishing Rate</div>
            <div class="metric">{{ $phishingPercent }}<span class="metric-unit">%</span></div>
        </div>
        <div class="card stat-card">
            <div class="label">Top Tactic Seen</div>
            <div class="metric metric-word">{{ ucfirst($topTechnique) }}</div>
        </div>
    </div>

    {{-- Stat tiles stay cards - they are discrete readouts. Everything below is
         a flat section, so the dashboard reads as "figures, then detail" rather
         than six equally-weighted boxes. --}}
    <div class="report">
        <section class="report-section">
            <div class="report-header">
                <span class="report-icon"><x-icon name="activity" /></span>
                <h2>Last 14 Days</h2>
            </div>
            <div class="chart-wrap">
                <canvas id="trendChart"></canvas>
            </div>
        </section>

        <section class="report-section">
            <div class="report-header">
                <span class="report-icon"><x-icon name="file-text" /></span>
                <h2>Recent Scans</h2>
            </div>

            @foreach ($recentScans as $scan)
                @php
                    $riskClass = match($scan->risk) {
                        'Low Risk' => 'risk-low',
                        'Moderate Risk' => 'risk-moderate',
                        'High Risk' => 'risk-high',
                        'Critical Risk' => 'risk-critical',
                        default => 'risk-low',
                    };
                @endphp
                <a href="{{ route('history.show', $scan) }}" class="recent-row">
                    <span class="recent-row-date">{{ $scan->created_at->format('d M, g:i A') }}</span>
                    <span class="badge {{ $riskClass }}">{{ $scan->risk }}</span>
                </a>
            @endforeach

            <div class="section-actions">
                <a href="{{ route('history') }}" class="btn btn-secondary">
                    View all history
                    <x-icon name="arrow-right" />
                </a>
            </div>
        </section>
    </div>
    @endif

@endsection

@if ($totalScans > 0)
@push('scripts')
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
    (function () {
        const canvas = document.getElementById('trendChart');
        if (!canvas || typeof Chart === 'undefined') return;

        // Pull the palette from CSS rather than repeating hex codes here, so the
        // chart stays in step if the theme tokens are ever retuned.
        const css = getComputedStyle(document.documentElement);
        const token = (name, fallback) => (css.getPropertyValue(name).trim() || fallback);

        const sealRed = token('--seal-red', '#C1440E');
        const green   = token('--safe-green', '#3B7A57');
        const cream   = token('--paper-cream', '#F5F1E8');
        const slate   = token('--slate', '#939CAD');
        const grid    = 'rgba(245, 241, 232, 0.06)';

        const ctx = canvas.getContext('2d');
        const fade = (hex, top, bottom) => {
            const g = ctx.createLinearGradient(0, 0, 0, canvas.offsetHeight || 220);
            g.addColorStop(0, hex + top);
            g.addColorStop(1, hex + bottom);
            return g;
        };

        Chart.defaults.font.family = token('--font-body', 'Inter, system-ui, sans-serif');
        Chart.defaults.font.size = 11;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: @json($chartLabels),
                datasets: [
                    {
                        label: 'Phishing',
                        data: @json($chartPhishing),
                        borderColor: sealRed,
                        backgroundColor: fade(sealRed, '44', '00'),
                        pointBackgroundColor: sealRed,
                        pointBorderColor: 'transparent',
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true,
                    },
                    {
                        label: 'Legitimate',
                        data: @json($chartLegitimate),
                        borderColor: green,
                        backgroundColor: fade(green, '3D', '00'),
                        pointBackgroundColor: green,
                        pointBorderColor: 'transparent',
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        align: 'end',
                        labels: {
                            color: slate,
                            usePointStyle: true,
                            pointStyle: 'circle',
                            boxWidth: 7,
                            boxHeight: 7,
                            padding: 18,
                        }
                    },
                    tooltip: {
                        backgroundColor: token('--surface-0', '#12181F'),
                        borderColor: 'rgba(245, 241, 232, 0.12)',
                        borderWidth: 1,
                        titleColor: cream,
                        bodyColor: slate,
                        padding: 10,
                        cornerRadius: 8,
                        displayColors: true,
                        usePointStyle: true,
                    }
                },
                scales: {
                    x: {
                        ticks: { color: slate, maxRotation: 0, autoSkipPadding: 14 },
                        grid: { display: false },
                        border: { color: grid },
                    },
                    y: {
                        ticks: { color: slate, stepSize: 1, precision: 0, padding: 8 },
                        grid: { color: grid },
                        border: { display: false },
                        beginAtZero: true,
                    }
                }
            }
        });
    })();
</script>
@endpush
@endif
