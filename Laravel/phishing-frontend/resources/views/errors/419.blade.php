@extends('layouts.error')

@section('code', '419')
@section('stamp', 'Session Expired')
@section('title', 'Your session timed out')
@section('message', "The page sat open long enough for its security token to expire, so the form was not submitted. Nothing was lost — go back and send it again.")

@section('extra-action')
    <button type="button" class="btn btn-secondary" onclick="history.back()">
        Go back and retry
    </button>
@endsection
