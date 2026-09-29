<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Credential for the browser extension.
 *
 * The web app authenticates with session cookies, which an extension cannot
 * use: it calls from a chrome-extension:// origin, so it does not carry the
 * site's cookies, and making them work cross-origin would need SameSite=None
 * with Secure - which needs HTTPS the local setup does not have.
 *
 * A bearer token sidesteps all of that. Only the SHA-256 hash is stored, so a
 * stolen database does not hand over working credentials; the plain token is
 * shown to the user once, at the moment it is generated.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('api_token', 64)->nullable()->unique()->after('remember_token');
            $table->timestamp('api_token_created_at')->nullable()->after('api_token');
        });
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn(['api_token', 'api_token_created_at']);
        });
    }
};
