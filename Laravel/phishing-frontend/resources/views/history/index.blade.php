@extends('layouts.site')

@section('title', 'Analysis History — PanshengGuard')

@section('content')

<div class="container">
    <header class="page-head">
        <div class="page-head-row">
            <div>
                <div class="eyebrow">Analysis history</div>
                <h1>Every email you&rsquo;ve analyzed</h1>
                <p class="lead">Open any analysis to see its full PanshengGuard report. Only a short, masked excerpt of each email is stored.</p>
            </div>
            <a href="{{ route('home') }}#scanner" class="btn btn-primary btn-label-caps">
                <x-icon name="scan" />
                Analyze email
            </a>
        </div>
    </header>

    <div class="page-body">
        @if ($scans->isEmpty())
            <div class="panel">
                <div class="empty-state">
                    <div class="empty-state-icon"><x-icon name="inbox" /></div>
                    <h3>No analyses yet</h3>
                    <p>When you analyze an email &mdash; here or with the Gmail extension &mdash; it appears in this list.</p>
                    <a href="{{ route('home') }}#scanner" class="btn btn-primary">
                        <x-icon name="scan" />
                        Analyze your first email
                    </a>
                </div>
            </div>
        @else
            @include('partials.scan-list', ['scans' => $scans])

            {{ $scans->links() }}
        @endif
    </div>
</div>

@endsection
