<?php

namespace App\Http\Controllers;

use App\Services\PhishingAnalyzer;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;

class PhishingController extends Controller
{
    public function __construct(private PhishingAnalyzer $analyzer)
    {
    }

    public function index()
    {
        return view('phishing.index');
    }

    public function analyze(Request $request)
    {
        $request->validate([
            'email_text' => 'required|string|max:50000',
        ]);

        // --- Guest scan limit: one free scan per session, unlimited once logged in ---
        if (!Auth::check() && $request->session()->get('guest_scan_used', false)) {
            return redirect()
                ->route('register')
                ->with('error', "You've used your free scan. Create an account to keep scanning and see your history.");
        }

        // The Python API is called server-side, so from its point of view every
        // request in the application shares one IP address. Name the account (or
        // guest session) we are acting for, so its rate limit applies per user
        // instead of throttling the whole application at once.
        $clientId = Auth::check()
            ? 'user:' . Auth::id()
            : 'guest:' . $request->session()->getId();

        $outcome = $this->analyzer->analyze(
            emailText: $request->input('email_text'),
            checkUrls: $request->boolean('check_urls', true),
            user: Auth::user(),
            clientId: $clientId,
            sessionId: $request->session()->getId(),
        );

        if (!$outcome['ok']) {
            return back()->with('error', $outcome['error'])->withInput();
        }

        // --- Mark guest scan as used ---
        if (!Auth::check()) {
            $request->session()->put('guest_scan_used', true);
        }

        return view('phishing.result', [
            'result' => $outcome['result'],
            'scan' => $outcome['scan'],
        ]);
    }
}
