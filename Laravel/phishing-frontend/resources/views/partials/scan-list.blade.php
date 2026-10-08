{{--
    List of saved scans, used by History, the Dashboard and the home page.
    Expects $scans (iterable of Scan). Optional $showHead (bool).
--}}
@php
    $showHead = $showHead ?? true;
    $tqLabels = ['urgency' => 'Urgency', 'authority' => 'False Authority', 'fear' => 'Fear', 'scarcity' => 'Scarcity'];
@endphp

<div class="scan-list">
    @if ($showHead)
        <div class="scan-list-head" aria-hidden="true">
            <span>Score</span>
            <span>Email</span>
            <span>Analyzed</span>
            <span>Classification</span>
            <span></span>
        </div>
    @endif

    @foreach ($scans as $scan)
        @php
            $found = collect($scan->techniques ?? [])->filter(fn ($hits) => is_array($hits) && count($hits) > 0)->keys();
        @endphp
        <a href="{{ route('history.show', $scan) }}" class="scan-row">
            <x-score-tile :probability="$scan->probability" />
            <div style="min-width: 0;">
                <div class="scan-row-snippet">{{ $scan->email_snippet }}</div>
                <div class="scan-row-meta">
                    <x-risk-badge :probability="$scan->probability" :show-score="false" suffix=" probability" style="height: 22px; font-size: 0.62rem;" />
                    @foreach ($found as $technique)
                        <span class="chip">{{ $tqLabels[$technique] ?? ucfirst($technique) }}</span>
                    @endforeach
                </div>
                <div class="scan-row-mobile-date">{{ $scan->created_at->format('d M Y, g:i A') }}</div>
            </div>
            <span class="scan-row-date col-date">{{ $scan->created_at->format('d M Y, g:i A') }}</span>
            <span class="scan-row-label col-label">{{ $scan->label }}</span>
            <span class="scan-row-arrow"><x-icon name="arrow-right" /></span>
        </a>
    @endforeach
</div>
