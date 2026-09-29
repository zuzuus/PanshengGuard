<?php

namespace App\Http\Controllers;

use App\Models\Scan;
use Illuminate\Http\RedirectResponse;
use Illuminate\Support\Facades\Auth;

class HistoryController extends Controller
{
    public function index()
    {
        $scans = Scan::where('user_id', Auth::id())
            ->orderBy('created_at', 'desc')
            ->paginate(15);

        return view('history.index', ['scans' => $scans]);
    }

    public function show(Scan $scan)
    {
        $this->authoriseOwnership($scan);

        return view('history.show', ['scan' => $scan]);
    }

    /**
     * Remove a single scan.
     *
     * Someone who pasted a genuinely private email had no way to take it back:
     * the only removal path was deleting the whole account. A scan record keeps
     * the first 200 characters of whatever was pasted, so this needs to be
     * reachable per record.
     */
    public function destroy(Scan $scan): RedirectResponse
    {
        $this->authoriseOwnership($scan);

        $scan->delete();

        return redirect()
            ->route('history')
            ->with('success', 'Scan deleted. It is no longer stored on your account.');
    }

    /**
     * Route model binding resolves any id, so ownership has to be checked on
     * every action that reaches a scan - otherwise any signed-in user could
     * read or delete another account's records by guessing ids.
     */
    private function authoriseOwnership(Scan $scan): void
    {
        if ($scan->user_id === null || $scan->user_id !== Auth::id()) {
            abort(403);
        }
    }
}