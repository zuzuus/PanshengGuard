<?php

use App\Http\Controllers\Api\ExtensionController;
use App\Http\Middleware\AuthenticateApiToken;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API routes
|--------------------------------------------------------------------------
|
| Stateless JSON endpoints for the browser extension. Separate from web.php
| because these carry no session and no CSRF token - they authenticate with a
| bearer token instead (see AuthenticateApiToken).
|
| The throttle is a second line of defence. The Python service already limits
| per user, but that only helps once the request has been proxied; this stops
| a misbehaving extension from hammering Laravel itself.
|
*/

Route::middleware([AuthenticateApiToken::class, 'throttle:30,1'])
    ->prefix('extension')
    ->group(function () {
        Route::get('/ping', [ExtensionController::class, 'ping']);
        Route::post('/analyze', [ExtensionController::class, 'analyze']);
    });
