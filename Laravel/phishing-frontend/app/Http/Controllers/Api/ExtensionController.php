<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Services\PhishingAnalyzer;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * JSON endpoints for the browser extension.
 *
 * The web routes return rendered pages, which an extension cannot use. These
 * return the verdict as data and let the extension draw its own banner, while
 * still going through PhishingAnalyzer - so a scan started in Gmail is stored
 * and attributed exactly like one started on the website, and shows up in the
 * same history and dashboard.
 */
class ExtensionController extends Controller
{
    public function __construct(private PhishingAnalyzer $analyzer)
    {
    }

    /**
     * Cheap call the extension makes on startup to confirm the token works,
     * so it can say "not connected" before the user tries to scan anything.
     */
    public function ping(Request $request): JsonResponse
    {
        return response()->json([
            'ok' => true,
            'user' => [
                'name' => $request->user()->name,
                'email' => $request->user()->email,
            ],
        ]);
    }

    public function analyze(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'email_text' => 'required|string|max:50000',
            'check_urls' => 'sometimes|boolean',
        ]);

        $user = $request->user();

        $outcome = $this->analyzer->analyze(
            emailText: $validated['email_text'],
            checkUrls: $request->boolean('check_urls', false),
            user: $user,
            clientId: 'user:' . $user->id,
        );

        if (!$outcome['ok']) {
            return response()->json([
                'error' => 'analysis_failed',
                'message' => $outcome['error'],
            ], $outcome['status']);
        }

        $result = $outcome['result'];
        $scan = $outcome['scan'];

        // Trimmed rather than the whole API payload - clean_tokens would be
        // dead weight on every email opened. `techniques` IS included though:
        // it carries the actual words that matched, which is what lets the
        // extension mark them up inside the message rather than only naming
        // them in a banner.
        return response()->json([
            'ok' => true,
            'scan_id' => $scan->id,
            'label' => $result['label'],
            'risk' => $result['risk'],
            'probability' => round($result['probability'] * 100, 1),
            'sophistication_score' => $result['sophistication_score'],
            'signals' => $result['signals'] ?? [],
            'techniques' => $this->matchedTerms($result['techniques'] ?? []),
            'link_trusted' => $result['link_trusted'] ?? null,
            'detail_url' => route('history.show', $scan),
        ]);
    }

    /**
     * Drop the techniques that found nothing, so the extension does not have
     * to filter empty buckets before highlighting.
     *
     * @param  array<string, array<int, string>>  $techniques
     * @return array<string, array<int, string>>
     */
    private function matchedTerms(array $techniques): array
    {
        return array_filter($techniques, fn ($hits) => is_array($hits) && count($hits) > 0);
    }
}
