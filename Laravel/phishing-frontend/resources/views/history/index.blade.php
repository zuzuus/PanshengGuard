@extends('layouts.site')

@section('title', 'Scan History — PanshengGuard')

@section('content')

    <div class="eyebrow">Case Archive</div>
    <h1>Your Scan History</h1>
    <p class="section-lead">
        Every email you've analysed, kept on record.
    </p>

    @if ($scans->isEmpty())
        <div class="card">
            <div class="empty-state">No scans yet. <a href="{{ route('home') }}">Analyse your first email</a>.</div>
        </div>
    @else
        @foreach ($scans as $scan)
            @php
                $riskClass = match($scan->risk) {
                    'Low Risk' => 'risk-low',
                    'Moderate Risk' => 'risk-moderate',
                    'High Risk' => 'risk-high',
                    'Critical Risk' => 'risk-critical',
                    default => 'risk-low',
                };
                $accentColor = match($scan->risk) {
                    'Low Risk' => 'var(--risk-low)',
                    'Moderate Risk' => 'var(--risk-moderate)',
                    'High Risk' => 'var(--risk-high)',
                    'Critical Risk' => 'var(--risk-critical)',
                    default => 'var(--risk-moderate)',
                };
            @endphp
            <a href="{{ route('history.show', $scan) }}" class="history-row">
                <span class="history-row-accent" style="background: {{ $accentColor }};"></span>
                <div class="history-row-body">
                    <div class="label">{{ $scan->created_at->format('d M Y, g:i A') }}</div>
                    <p class="history-row-snippet">{{ $scan->email_snippet }}</p>
                </div>
                <span class="badge {{ $riskClass }}">{{ $scan->risk }}</span>
                <span class="history-row-arrow"><x-icon name="arrow-right" /></span>
            </a>
        @endforeach

        {{ $scans->links() }}
    @endif

@endsection
