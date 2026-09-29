@props(['messages'])

@if ($messages)
    <div {{ $attributes->merge(['class' => 'alert alert-error']) }}>
        @foreach ((array) $messages as $message)
            <div>{{ $message }}</div>
        @endforeach
    </div>
@endif
