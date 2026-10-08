@props(['probability' => 0, 'showScore' => true, 'suffix' => ''])

{{--
    CVSS-style badge for the phishing probability.

    Display conversion of the API's existing probability (0–1): one decimal
    out of 10 (0.76 -> 7.6), with the CVSS v3 severity bands
    None 0.0 · Low 0.1–3.9 · Medium 4.0–6.9 · High 7.0–8.9 · Critical 9.0–10.0.
    The backend scoring is untouched.
--}}
@php
    $pgScore = round(((float) $probability) * 100) / 10;
    [$pgBand, $pgName] = match (true) {
        $pgScore <= 0.0 => ['low', 'None'],
        $pgScore < 4.0  => ['low', 'Low'],
        $pgScore < 7.0  => ['moderate', 'Medium'],
        $pgScore < 9.0  => ['high', 'High'],
        default         => ['critical', 'Critical'],
    };
@endphp

<span {{ $attributes->merge(['class' => "risk-badge band-{$pgBand}" . ($showScore ? '' : ' no-score')]) }} title="Phishing probability {{ number_format($pgScore, 1) }} / 10 (CVSS-style)">
    @if ($showScore)
        <span class="risk-badge-score">{{ number_format($pgScore, 1) }}</span>
    @endif
    {{ $pgName }}{{ $suffix }}
</span>
