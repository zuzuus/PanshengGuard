<?php

use App\Http\Controllers\Auth\SocialiteController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\HistoryController;
use App\Http\Controllers\PhishingController;
use App\Http\Controllers\ProfileController;
use Illuminate\Support\Facades\Route;

Route::get('/', [PhishingController::class, 'index'])->name('home');
Route::post('/analyze', [PhishingController::class, 'analyze'])->name('analyze');
Route::view('/about', 'about')->name('about');

Route::get('/auth/google/redirect', [SocialiteController::class, 'redirectToGoogle'])->name('auth.google');
Route::get('/auth/google/callback', [SocialiteController::class, 'handleGoogleCallback']);

Route::middleware(['auth', 'verified'])->group(function () {
    Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');

    // Credential for the browser extension.
    Route::post('/profile/api-token', [ProfileController::class, 'generateApiToken'])->name('profile.token.generate');
    Route::delete('/profile/api-token', [ProfileController::class, 'revokeApiToken'])->name('profile.token.revoke');

    Route::get('/history', [HistoryController::class, 'index'])->name('history');
    Route::get('/history/{scan}', [HistoryController::class, 'show'])->name('history.show');
    Route::delete('/history/{scan}', [HistoryController::class, 'destroy'])->name('history.destroy');
});

require __DIR__.'/auth.php';