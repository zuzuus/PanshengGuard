@if (session('status') === 'password-updated')
    <div class="alert alert-success" style="margin-bottom: 20px;"><x-icon name="check-circle" /><span>Password updated successfully.</span></div>
@endif

<form method="POST" action="{{ route('password.update') }}">
    @csrf
    @method('put')

    <div class="field">
        <label for="update_password_current_password">Current password</label>
        <input id="update_password_current_password" name="current_password" type="password" autocomplete="current-password">
        @error('current_password', 'updatePassword')
            <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
        @enderror
    </div>

    <div class="field">
        <label for="update_password_password">New password</label>
        <input id="update_password_password" name="password" type="password" autocomplete="new-password">
        @error('password', 'updatePassword')
            <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
        @enderror
    </div>

    <div class="field">
        <label for="update_password_password_confirmation">Confirm password</label>
        <input id="update_password_password_confirmation" name="password_confirmation" type="password" autocomplete="new-password">
        @error('password_confirmation', 'updatePassword')
            <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
        @enderror
    </div>

    <div style="margin-top: 24px;">
        <button type="submit" class="btn btn-primary">Save password</button>
    </div>
</form>
