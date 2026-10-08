# Start PanshengGuard in Docker and print the public Cloudflare link.
# Run from this folder:   powershell -ExecutionPolicy Bypass -File .\docker-start.ps1

Set-Location -Path $PSScriptRoot

Write-Host "Starting PanshengGuard (first run builds the images, this can take several minutes)..." -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Write-Host "Docker failed to start. Is Docker Desktop running?" -ForegroundColor Red; exit 1 }

Write-Host "Waiting for the Cloudflare link..." -ForegroundColor Cyan
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 2
    $logs = docker compose logs cloudflared 2>&1 | Out-String
    $m = [regex]::Match($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($m.Success) { $url = $m.Value }
}

Write-Host ""
Write-Host "Local website : http://127.0.0.1:8001" -ForegroundColor Green
if ($url) {
    Write-Host "Public link   : $url" -ForegroundColor Green
} else {
    Write-Host "Public link not ready yet. Run:  docker compose logs cloudflared" -ForegroundColor Yellow
}
Write-Host "Stop everything with:  docker compose down"
