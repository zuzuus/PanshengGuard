<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * The detection service already returned these three fields; nothing stored or
 * displayed them, so the explanation of WHY a mail scored the way it did never
 * reached the user.
 *
 * All three are nullable because the 68 scans recorded before this migration
 * were saved without them.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('scans', function (Blueprint $table) {
            // Plain-English red flags that fired on this mail, from the
            // features.py block (raw IP link, typosquat, credential request...).
            $table->json('signals')->nullable()->after('checklist');

            // Whether the mail links to a domain on the known-good list. Parsed
            // by host on the Python side, so a lookalike such as
            // "maybank2u.com.my.attacker.net" does not count as a match.
            $table->boolean('link_trusted')->nullable()->after('signals');

            // The lemmatised text the classifier actually saw, after stopwords
            // and punctuation were stripped. Shown collapsed - it is the honest
            // answer to "what did the model read?".
            $table->text('clean_tokens')->nullable()->after('link_trusted');
        });
    }

    public function down(): void
    {
        Schema::table('scans', function (Blueprint $table) {
            $table->dropColumn(['signals', 'link_trusted', 'clean_tokens']);
        });
    }
};
