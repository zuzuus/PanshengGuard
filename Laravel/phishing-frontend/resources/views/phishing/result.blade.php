@extends('layouts.site')

@section('title', 'Analysis Result — PanshengGuard')

@section('content')

    <a href="{{ route('home') }}" class="btn btn-secondary back-link">
        <x-icon name="arrow-left" />
        Analyse another email
    </a>

    <div class="eyebrow">Case File Result</div>
    <h1>Verdict</h1>

    @include('partials.verdict', [
        'label'          => $result['label'],
        'risk'           => $result['risk'],
        'probability'    => $result['probability'],
        'sophistication' => $result['sophistication_score'],
        'techniques'     => $result['techniques'],
        'tips'           => $result['tips'] ?? [],
        'checklist'      => $result['checklist'] ?? [],
        'urlResults'     => $result['url_results'] ?? [],
        'signals'        => $result['signals'] ?? [],
        'linkTrusted'    => $result['link_trusted'] ?? null,
        'cleanTokens'    => $result['clean_tokens'] ?? null,
    ])

@endsection
