@extends('layouts.site')

@section('title', 'Threat Assessment — PanshengGuard')

@section('content')

    <div class="container">
        <header class="page-head" style="padding-bottom: 32px;">
            <div class="page-head-row">
                <div>
                    <div class="eyebrow">Threat assessment</div>
                    <h1>Analysis result</h1>
                </div>
                <a href="{{ route('home') }}#scanner" class="btn btn-secondary">
                    <x-icon name="arrow-left" />
                    Analyze another email
                </a>
            </div>
        </header>

        <div class="page-body">
            {{-- The email shown on the left is the text that was just submitted
                 (read from this same request); nothing is re-sent anywhere. --}}
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
                'emailText'      => trim((string) request()->input('email_text', '')),
                'emailIsExcerpt' => false,
                'animate'        => true,
                'savedReportUrl' => (isset($scan) && $scan->user_id && auth()->check()) ? route('history.show', $scan) : null,
                'context'        => 'result',
            ])
        </div>
    </div>

@endsection

@push('scripts')
    <script src="{{ asset('js/scanner.js') }}?v=3" defer></script>
@endpush
