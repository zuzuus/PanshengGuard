<?php

namespace App\Http\Controllers;

use App\Models\Scan;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Carbon;

class DashboardController extends Controller
{
    public function index()
    {
        $userId = Auth::id();

        $totalScans = Scan::where('user_id', $userId)->count();
        $phishingCount = Scan::where('user_id', $userId)->where('label', 'PHISHING')->count();
        $legitimateCount = $totalScans - $phishingCount;
        $phishingPercent = $totalScans > 0 ? round(($phishingCount / $totalScans) * 100, 1) : 0;

        // --- Most common manipulation technique ---
        $techniqueCounts = [];
        Scan::where('user_id', $userId)->pluck('techniques')->each(function ($techniques) use (&$techniqueCounts) {
            foreach ($techniques as $technique => $hits) {
                if (count($hits) > 0) {
                    $techniqueCounts[$technique] = ($techniqueCounts[$technique] ?? 0) + 1;
                }
            }
        });
        arsort($techniqueCounts);
        $topTechnique = array_key_first($techniqueCounts) ?? 'None yet';

        // --- Last 14 days trend for the chart ---
        $days = collect(range(13, 0))->map(fn ($i) => Carbon::now()->subDays($i)->format('Y-m-d'));

        $scansByDay = Scan::where('user_id', $userId)
            ->where('created_at', '>=', Carbon::now()->subDays(14))
            ->get()
            ->groupBy(fn ($scan) => $scan->created_at->format('Y-m-d'));

        $chartLabels = $days->map(fn ($d) => Carbon::parse($d)->format('d M'))->toArray();
        $chartPhishing = $days->map(function ($day) use ($scansByDay) {
            return isset($scansByDay[$day]) ? $scansByDay[$day]->where('label', 'PHISHING')->count() : 0;
        })->toArray();
        $chartLegitimate = $days->map(function ($day) use ($scansByDay) {
            return isset($scansByDay[$day]) ? $scansByDay[$day]->where('label', 'LEGITIMATE')->count() : 0;
        })->toArray();

        $recentScans = Scan::where('user_id', $userId)
            ->orderBy('created_at', 'desc')
            ->limit(5)
            ->get();

        return view('dashboard', [
            'totalScans' => $totalScans,
            'phishingCount' => $phishingCount,
            'legitimateCount' => $legitimateCount,
            'phishingPercent' => $phishingPercent,
            'topTechnique' => $topTechnique,
            'chartLabels' => $chartLabels,
            'chartPhishing' => $chartPhishing,
            'chartLegitimate' => $chartLegitimate,
            'recentScans' => $recentScans,
        ]);
    }
}