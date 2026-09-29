<?php

namespace App\Models;

// use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Illuminate\Support\Str;

class User extends Authenticatable
{
    /** @use HasFactory<\Database\Factories\UserFactory> */
    use HasFactory, Notifiable;

    /**
     * The attributes that are mass assignable.
     *
     * @var list<string>
     */
    protected $fillable = [
        'name',
        'email',
        'password',
        'google_id',
        'avatar',
    ];

    /**
     * The attributes that should be hidden for serialization.
     *
     * @var list<string>
     */
    protected $hidden = [
        'password',
        'remember_token',
        'api_token',
    ];

    /**
     * Get the attributes that should be cast.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'api_token_created_at' => 'datetime',
            'password' => 'hashed',
        ];
    }

    /**
     * Issue a fresh API token for the browser extension.
     *
     * Returns the plain token, which is the ONLY time it exists in readable
     * form - the column holds a SHA-256 hash. If the user loses it they
     * generate a new one, which also invalidates the old.
     *
     * SHA-256 rather than bcrypt on purpose: this value is a 48-character
     * random string, not a human-chosen password, so there is nothing to
     * brute-force and the lookup has to be a single indexed query rather than
     * a hash comparison against every row.
     */
    public function generateApiToken(): string
    {
        $plain = Str::random(48);

        $this->forceFill([
            'api_token' => hash('sha256', $plain),
            'api_token_created_at' => now(),
        ])->save();

        return $plain;
    }

    /**
     * Revoke the current token without issuing a replacement.
     */
    public function revokeApiToken(): void
    {
        $this->forceFill([
            'api_token' => null,
            'api_token_created_at' => null,
        ])->save();
    }

    public function hasApiToken(): bool
    {
        return $this->api_token !== null;
    }

    /**
     * Resolve a plain bearer token back to its owner.
     */
    public static function findByApiToken(string $plain): ?self
    {
        if (trim($plain) === '') {
            return null;
        }

        return static::where('api_token', hash('sha256', $plain))->first();
    }

    /**
     * Scans belonging to this account.
     *
     * Note that the scans table declares the foreign key as ON DELETE SET NULL,
     * so deleting a user does NOT remove these rows on its own - see
     * ProfileController::destroy(), which clears them explicitly.
     */
    public function scans(): HasMany
    {
        return $this->hasMany(Scan::class);
    }
}