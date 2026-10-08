@extends('layouts.site')

@section('title', 'Full Report — PanshengGuard')

@section('content')

    <div class="container">
        <header class="page-head" style="padding-bottom: 32px;">
            <a href="{{ route('history') }}" class="auth-back">
                <x-icon name="arrow-left" />
                Analysis history
            </a>
            <div class="page-head-row" style="margin-top: 20px;">
                <div>
                    <div class="eyebrow">Full report &middot; #{{ $scan->id }}</div>
                    <h1>PanshengGuard report</h1>
                </div>
                <x-risk-badge :probability="$scan->probability" suffix=" probability" />
            </div>
        </header>

        <div class="page-body">
            @include('partials.verdict', [
                'label'          => $scan->label,
                'risk'           => $scan->risk,
                'probability'    => $scan->probability,
                'sophistication' => $scan->sophistication_score,
                'techniques'     => $scan->techniques ?? [],
                'tips'           => $scan->tips ?? [],
                'checklist'      => $scan->checklist ?? [],
                'urlResults'     => $scan->url_results ?? [],
                'signals'        => $scan->signals ?? [],
                'linkTrusted'    => $scan->link_trusted,
                'cleanTokens'    => $scan->clean_tokens,
                'emailText'      => $scan->email_snippet,
                'emailIsExcerpt' => true,
                'animate'        => false,
                'scannedAt'      => $scan->created_at->format('d M Y, g:i A'),
                'context'        => 'history',
            ])

            <section class="settings-section is-danger" style="margin-top: 64px;">
                <div class="aside">
                    <h2>Remove this scan</h2>
                    <p>Deleting this record removes the stored excerpt of the email, along with its assessment. This cannot be undone.</p>
                </div>
                <div class="body">
                    <form method="POST"
                          action="{{ route('history.destroy', $scan) }}"
                          onsubmit="return confirm('Delete this scan permanently? This cannot be undone.');">
                        @csrf
                        @method('DELETE')
                        <button type="submit" class="btn btn-danger" data-loading-text="Deleting…">
                            <x-icon name="trash" />
                            Delete this scan
                        </button>
                    </form>
                </div>
            </section>
        </div>
    </div>

@endsection

@push('scripts')
    <script src="{{ asset('js/scanner.js') }}?v=3" defer></script>
@endpush
