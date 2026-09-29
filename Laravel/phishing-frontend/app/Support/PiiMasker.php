<?php

namespace App\Support;

/**
 * Redacts personal details from text before it is written to the database.
 *
 * The Python service already masks PII before the model reads an email, but
 * that copy never came back across the API - Laravel stored the raw text it
 * was posted. The result was that `scans.email_snippet` held real addresses in
 * plain text (58 of 73 rows), while the About page told people that "email
 * addresses, phone numbers, and card numbers are automatically masked". This
 * closes that gap on the side that actually owns the database.
 *
 * Masking here rather than asking the API for a masked copy is deliberate:
 * Laravel decides what Laravel persists, so the guarantee holds even if the
 * detection service changes or is swapped out.
 */
class PiiMasker
{
    /**
     * Order matters. Cards are matched before phone numbers so a 16-digit card
     * is not partly consumed by the phone pattern first.
     */
    public static function mask(string $text): string
    {
        $text = preg_replace(
            '/\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b/',
            '[EMAIL]',
            $text
        );

        // 16 digits in groups of four, with or without separators.
        $text = preg_replace(
            '/\b(?:\d{4}[-\s]?){3}\d{4}\b/',
            '[CARD]',
            $text
        );

        // Malaysian numbers, which the Python side misses entirely - its
        // pattern is US-shaped, so "+6012-3456789" and "03-7890 1234" both
        // passed through unmasked on a Malaysia-focused tool.
        //
        // Covers: +60 / 60 / leading 0, then a 1-2 digit mobile or area code,
        // then 7-8 digits with optional -, . or space separators.
        $text = preg_replace(
            '/(?:\+?60[-.\s]?|\b0)\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}\b/',
            '[PHONE]',
            $text
        );

        // International / US-style, kept so foreign-brand phishing is covered
        // too (fake Netflix and PayPal mails quote US support numbers).
        $text = preg_replace(
            '/\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/',
            '[PHONE]',
            $text
        );

        return $text;
    }
}
