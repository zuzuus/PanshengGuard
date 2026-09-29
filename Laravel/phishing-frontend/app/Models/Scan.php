<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Scan extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'session_id',
        'email_snippet',
        'label',
        'probability',
        'sophistication_score',
        'risk',
        'techniques',
        'url_results',
        'tips',
        'checklist',
        'signals',
        'link_trusted',
        'clean_tokens',
    ];

    protected $casts = [
        'techniques' => 'array',
        'url_results' => 'array',
        'tips' => 'array',
        'checklist' => 'array',
        'signals' => 'array',
        'link_trusted' => 'boolean',
        'probability' => 'float',
        'sophistication_score' => 'float',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}