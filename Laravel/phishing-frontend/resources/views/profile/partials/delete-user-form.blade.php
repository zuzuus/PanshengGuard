<button type="button" class="btn btn-danger" id="delete-account-open"
        onclick="document.getElementById('delete-account-confirm').hidden = false; this.hidden = true; document.getElementById('password').focus();">
    <x-icon name="trash" />
    Delete account
</button>

<div id="delete-account-confirm" class="inline-confirm" @if (! $errors->userDeletion->isNotEmpty()) hidden @endif>
    <form method="POST" action="{{ route('profile.destroy') }}">
        @csrf
        @method('delete')

        <div class="field">
            <label for="password">Confirm your password to permanently delete your account</label>
            <input id="password" name="password" type="password" placeholder="Password">
            @error('password', 'userDeletion')
                <div class="alert alert-error"><x-icon name="alert-circle" /><span>{{ $message }}</span></div>
            @enderror
        </div>

        <div class="btn-row" style="margin-top: 16px;">
            <button type="submit" class="btn btn-danger-solid">Yes, delete my account</button>
            <button type="button" class="btn btn-ghost"
                    onclick="document.getElementById('delete-account-confirm').hidden = true; document.getElementById('delete-account-open').hidden = false;">Cancel</button>
        </div>
    </form>
</div>
