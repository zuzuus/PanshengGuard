@extends('layouts.error')

@section('code', '500')
@section('stamp', 'Internal Fault')
@section('title', 'Something broke on our side')
@section('message', "This one is not your fault. The request reached us but could not be completed. Try again in a moment — if it keeps happening, the detail is in the application log.")
