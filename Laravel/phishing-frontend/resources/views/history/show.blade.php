@extends('layouts.site')

@section('title', 'Scan Detail — PanshengGuard')

@section('content')

    <a href="{{ route('history') }}" class="btn btn-secondary back-link">
        <x-icon name="arrow-left" />
        Back to history
    </a>

    <div class="eyebrow">Case File Result &middot; {{ $scan->created_at->format('d M Y, g:i A') }}</div>
    <h1>Verdict</h1>

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
    ])

    <section class="report-section danger-zone">
        <div class="report-header">
            <span class="report-icon is-red"><x-icon name="trash" /></span>
            <h2>Remove this scan</h2>
        </div>
        <p class="text-muted">
            Deleting this record removes the stored snippet of the email you pasted,
            along with its verdict. This cannot be undone.
        </p>

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
    </section>

@endsection
