# Poll task until completed/failed, then verify bookshelf/toc/50 chapters. Usage: .\poll_and_verify.ps1 -TaskId a37fd0b0
param([string]$TaskId = "a37fd0b0", [string]$Base = "http://104.244.90.202:9000/api", [int]$IntervalSec = 120, [int]$MaxWaitHours = 6)
$deadline = (Get-Date).AddHours($MaxWaitHours)
while ((Get-Date) -lt $deadline) {
    $t = Invoke-RestMethod -Uri "$Base/tasks/$TaskId" -Method Get -ErrorAction SilentlyContinue
    $status = $t.status
    Write-Output "$(Get-Date -Format 'HH:mm:ss') task $TaskId status=$status"
    if ($status -eq "completed") {
        # Verify bookshelf has book, toc >= 200, chapters 0..49 have content
        $books = (Invoke-RestMethod -Uri "$Base/bookshelf" -Method Get).books
        $our = $books | Where-Object { $_.task_id -eq $TaskId }
        if (-not $our) { Write-Output "FAIL: book not in bookshelf"; exit 2 }
        $toc = Invoke-RestMethod -Uri "$Base/tasks/$TaskId/novel/toc" -Method Get
        $n = ($toc.toc).Count
        if ($n -lt 200) { Write-Output "FAIL: toc has $n chapters (need >= 200)"; exit 3 }
        $bad = 0
        for ($i = 0; $i -lt 50; $i++) {
            $ch = Invoke-RestMethod -Uri "$Base/tasks/$TaskId/novel/chapters/$i" -Method Get -ErrorAction SilentlyContinue
            if (-not $ch -or -not $ch.content -or $ch.content.Length -lt 10) { $bad++ }
        }
        if ($bad -gt 0) { Write-Output "FAIL: $bad of first 50 chapters missing content"; exit 4 }
        Write-Output "OK: bookshelf has book, toc=$n chapters, first 50 chapters have content"
        exit 0
    }
    if ($status -eq "failed") { Write-Output "FAIL: task failed"; exit 1 }
    Start-Sleep -Seconds $IntervalSec
}
Write-Output "TIMEOUT after $MaxWaitHours h"; exit 5
