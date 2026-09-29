<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Cross-Origin Resource Sharing
    |--------------------------------------------------------------------------
    |
    | Applied only to the API routes the browser extension uses. The web pages
    | are left alone on purpose: nothing outside this site should be able to
    | post to the login or analyse forms from another origin.
    |
    */

    'paths' => ['api/*'],

    'allowed_methods' => ['GET', 'POST', 'OPTIONS'],

    /*
     | An unpacked extension gets a randomly generated id each time it is
     | loaded, so the exact origin is not known ahead of time. The pattern
     | below accepts any chrome-extension:// origin.
     |
     | For a published extension you would pin the real id here instead:
     |
     |     'allowed_origins' => ['chrome-extension://abcdefgh...'],
     |     'allowed_origins_patterns' => [],
     |
     | Worth noting for the write-up: this is less of an exposure than it
     | looks. Every request still has to carry a valid API token, so a hostile
     | extension gains nothing by being allowed to ask.
     */
    'allowed_origins' => [],

    'allowed_origins_patterns' => ['#^chrome-extension://[a-p]+$#'],

    'allowed_headers' => ['Content-Type', 'Authorization', 'X-Api-Token', 'Accept'],

    'exposed_headers' => [],

    'max_age' => 3600,

    /*
     | False because authentication is by bearer token, not cookies. Allowing
     | credentials would mean browsers attach the session cookie to these
     | requests, which is exactly what the token design avoids.
     */
    'supports_credentials' => false,

];
