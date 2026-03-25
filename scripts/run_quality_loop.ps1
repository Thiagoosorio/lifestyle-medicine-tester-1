param(
    [int]$IntervalMinutes = 30
)

if ($IntervalMinutes -lt 1) {
    Write-Error "IntervalMinutes must be at least 1."
    exit 1
}

while ($true) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$stamp] Starting quality loop..."
    python scripts/quality_loop.py
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Quality loop failed (exit code: $LASTEXITCODE)."
    }

    $nextMinutes = [Math]::Round($IntervalMinutes, 2)
    Write-Host "Sleeping for $nextMinutes minutes..."
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
