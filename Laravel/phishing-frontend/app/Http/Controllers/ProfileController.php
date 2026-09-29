<?php

namespace App\Http\Controllers;

use App\Http\Requests\ProfileUpdateRequest;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Redirect;
use Illuminate\View\View;

class ProfileController extends Controller
{
    /**
     * Display the user's profile form.
     */
    public function edit(Request $request): View
    {
        return view('profile.edit', [
            'user' => $request->user(),
        ]);
    }

    /**
     * Update the user's profile information.
     */
    public function update(ProfileUpdateRequest $request): RedirectResponse
    {
        $request->user()->fill($request->validated());

        if ($request->user()->isDirty('email')) {
            $request->user()->email_verified_at = null;
        }

        $request->user()->save();

        return Redirect::route('profile.edit')->with('status', 'profile-updated');
    }

    /**
     * Issue a token for the browser extension.
     *
     * The plain token is flashed to the session rather than stored, because
     * the column only keeps its hash - this is the one moment it can be shown.
     * Generating again replaces the old token, which is also how a user revokes
     * one they think has leaked.
     */
    public function generateApiToken(Request $request): RedirectResponse
    {
        $plain = $request->user()->generateApiToken();

        return Redirect::route('profile.edit')
            ->with('api_token_plain', $plain)
            ->with('success', 'New extension token generated. Copy it now — it will not be shown again.');
    }

    public function revokeApiToken(Request $request): RedirectResponse
    {
        $request->user()->revokeApiToken();

        return Redirect::route('profile.edit')
            ->with('success', 'Extension token revoked. The extension will stop working until you generate a new one.');
    }

    /**
     * Delete the user's account.
     */
    public function destroy(Request $request): RedirectResponse
    {
        $request->validateWithBag('userDeletion', [
            'password' => ['required', 'current_password'],
        ]);

        $user = $request->user();

        Auth::logout();

        // The scans table declares its foreign key as ON DELETE SET NULL, so
        // deleting the account alone would orphan every scan rather than remove
        // it - the pasted email snippets would stay in the database forever with
        // user_id = NULL. The About page tells people that deleting their account
        // removes everything tied to it, so remove it.
        $user->scans()->delete();

        $user->delete();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return Redirect::to('/');
    }
}
