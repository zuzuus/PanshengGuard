<?php

namespace App\Http\Middleware;

use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

/**
 * Bearer-token authentication for the browser extension.
 *
 * Session cookies are unavailable here: the extension calls from a
 * chrome-extension:// origin and does not carry the site's cookies. Rather
 * than loosening the cookie policy for the whole site, this route family
 * authenticates with a token the user copies from their profile page.
 *
 * On success the user is bound to the request via the normal auth guard, so
 * everything downstream - Auth::id(), scan ownership, rate-limit identity -
 * behaves exactly as it does for a web request.
 */
class AuthenticateApiToken
{
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->bearerToken() ?: $request->header('X-Api-Token', '');

        if (!is_string($token) || trim($token) === '') {
            return response()->json([
                'error' => 'missing_token',
                'message' => 'No API token supplied. Open your profile on the web app to generate one.',
            ], 401);
        }

        $user = User::findByApiToken($token);

        if (!$user) {
            return response()->json([
                'error' => 'invalid_token',
                'message' => 'This API token is not valid. Generate a new one from your profile page.',
            ], 401);
        }

        Auth::setUser($user);
        $request->setUserResolver(fn () => $user);

        return $next($request);
    }
}
