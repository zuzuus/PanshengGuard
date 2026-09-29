<button type="button" class="btn" style="background: var(--seal-red);" onclick="document.getElementById('delete-account-confirm').style.display='block'; this.style.display='none';">
    Delete Account
</button>

<div id="delete-account-confirm" style="display:none; margin-top:16px;">
    <form method="POST" action="{{ route('profile.destroy') }}">
        @csrf
        @method('delete')

        <label for="password">Confirm your password to permanently delete your account</label>
        <input id="password" name="password" type="password" placeholder="Password">
        @error('password', 'userDeletion')
            <div class="alert alert-error" style="margin-top:6px;">{{ $message }}</div>
        @enderror

        <div style="margin-top:14px; display:flex; gap:10px;">
            <button type="submit" class="btn" style="background: var(--seal-red);">Yes, delete my account</button>
            <button type="button" class="btn-secondary btn" onclick="document.getElementById('delete-account-confirm').style.display='none';">Cancel</button>
        </div>
    </form>
</div>