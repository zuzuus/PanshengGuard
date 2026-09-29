@if (session('status') === 'password-updated')
    <div class="alert alert-success">Password updated successfully.</div>
@endif

<form method="POST" action="{{ route('password.update') }}">
    @csrf
    @method('put')

    <label for="update_password_current_password">Current Password</label>
    <input id="update_password_current_password" name="current_password" type="password" autocomplete="current-password">
    @error('current_password', 'updatePassword')
        <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
    @enderror

    <div style="margin-top:16px;">
        <label for="update_password_password">New Password</label>
        <input id="update_password_password" name="password" type="password" autocomplete="new-password">
        @error('password', 'updatePassword')
            <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
        @enderror
    </div>

    <div style="margin-top:16px;">
        <label for="update_password_password_confirmation">Confirm Password</label>
        <input id="update_password_password_confirmation" name="password_confirmation" type="password" autocomplete="new-password">
        @error('password_confirmation', 'updatePassword')
            <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
        @enderror
    </div>

    <div style="margin-top:20px;">
        <button type="submit" class="btn">Save</button>
    </div>
</form>