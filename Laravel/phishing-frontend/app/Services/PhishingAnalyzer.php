<?php

namespace App\Services;

use App\Models\Scan;
use App\Models\User;
use App\Support\PiiMasker;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

/**
 * Calls the detection service and records the result.
 *
 * Extracted so the web form and the browser extension share one path. They
 * differ only in how they authenticate and how they render the answer; the
 * work in between - calling the API, masking, persisting - must stay identical,
 * or a scan made from Gmail would be stored differently from the same scan made
 * on the website.
 */
class PhishingAnalyzer
{
    public const TIMEOUT = 30;

    /**
     * @param  string      $emailText  raw pasted text
     * @param  bool        $checkUrls  run the VirusTotal lookup
     * @param  User|null   $user       owner of the scan, null for a guest
     * @param  string      $clientId   rate-limit identity sent to the API
     * @param  string|null $sessionId  web session, for attributing guest scans
     *
     * @return array{ok: bool, status: int, result?: array, scan?: Scan, error?: string}
     */
    public function analyze(
        string $emailText,
        bool $checkUrls,
        ?User $user,
        string $clientId,
        ?string $sessionId = null,
    ): array {
        $apiUrl = config('services.phishing_api.url');

        try {
            $response = Http::timeout(self::TIMEOUT)
                ->withHeaders(['X-Client-Id' => $clientId])
                ->post("{$apiUrl}/api/analyze", [
                    'email_text' => $emailText,
                    'check_urls' => $checkUrls,
                ]);
        } catch (ConnectionException $e) {
            Log::error('Phishing API connection failed: ' . $e->getMessage());

            return [
                'ok' => false,
                'status' => 503,
                'error' => 'Could not reach the analysis service. Please try again shortly.',
            ];
        }

        if ($response->failed()) {
            // FastAPI explains why it refused: input too long, rate limit
            // reached, nothing usable after preprocessing. Pass that through -
            // telling a rate-limited caller to "try again" only sends them
            // straight back into the limit.
            $detail = $response->json('detail');

            return [
                'ok' => false,
                'status' => $response->status(),
                'error' => is_string($detail) && trim($detail) !== ''
                    ? $detail
                    : 'Analysis service returned an error. Please try again.',
            ];
        }

        $result = $response->json();

        $scan = Scan::create([
            'user_id' => $user?->id,
            'session_id' => $sessionId,

            // Masked before it is stored, not just before it is analysed.
            // Mask first, then truncate, so a redaction cannot be cut in half
            // and leave a fragment of the original behind.
            'email_snippet' => Str::limit(PiiMasker::mask($emailText), 200),

            'label' => $result['label'],
            'probability' => $result['probability'],
            'sophistication_score' => $result['sophistication_score'],
            'risk' => $result['risk'],
            'techniques' => $result['techniques'],
            'url_results' => $result['url_results'] ?? [],
            'tips' => $result['tips'] ?? [],
            'checklist' => $result['checklist'] ?? [],
            'signals' => $result['signals'] ?? [],
            'link_trusted' => $result['link_trusted'] ?? null,
            'clean_tokens' => $result['clean_tokens'] ?? null,
        ]);

        return [
            'ok' => true,
            'status' => 200,
            'result' => $result,
            'scan' => $scan,
        ];
    }
}
