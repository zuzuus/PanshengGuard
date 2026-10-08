@props(['probability' => 0])

{{-- Compact CVSS-style score square used in lists: the phishing probability
     out of 10, one decimal. Same conversion as risk-badge. --}}
@php
    $pgScore = round(((float) $probability) * 100) / 10;
    $pgBand = match (true) {
        $pgScore < 4.0 => 'low',
        $pgScore < 7.0 => 'moderate',
        $pgScore < 9.0 => 'high',
        default        => 'critical',
    };
@endphp

<span {{ $attributes->merge(['class' => "score-tile band-{$pgBand}"]) }} title="Phishing probability {{ number_format($pgScore, 1) }} / 10 (CVSS-style)">
    <span>{{ number_format($pgScore, 1) }}<small>/10</small></span>
</span>
