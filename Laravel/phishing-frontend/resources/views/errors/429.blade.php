@extends('layouts.error')

@section('code', '429')
@section('stamp', 'Rate limited')
@section('title', 'Too many requests')
@section('message', "You have sent more requests than the scanner accepts in a short window. Wait about a minute, then try again.")
