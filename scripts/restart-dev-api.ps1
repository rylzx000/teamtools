$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root 'data\logs'
$outLog = Join-Path $logDir 'dev-api.out.log'
$errLog = Join-Path $logDir 'dev-api.err.log'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$currentPid = $PID

function Get-ProcessTreeIds {
    param(
        [int[]]$RootProcessIds,
        [object[]]$AllProcesses
    )

    $result = New-Object System.Collections.Generic.HashSet[int]
    $queue = New-Object System.Collections.Generic.Queue[int]

    foreach ($processId in $RootProcessIds) {
        if ($processId -and $processId -ne $currentPid -and $result.Add([int]$processId)) {
            $queue.Enqueue([int]$processId)
        }
    }

    while ($queue.Count -gt 0) {
        $parentId = $queue.Dequeue()
        $children = $AllProcesses | Where-Object { $_.ParentProcessId -eq $parentId }
        foreach ($child in $children) {
            if ($child.ProcessId -ne $currentPid -and $result.Add([int]$child.ProcessId)) {
                $queue.Enqueue([int]$child.ProcessId)
            }
        }
    }

    $processIds = @()
    foreach ($processId in $result) {
        $processIds += [int]$processId
    }
    return $processIds
}

function Get-TeamToolsBackendProcessIds {
    $allProcesses = @(Get-CimInstance Win32_Process)
    $rootProcesses = $allProcesses | Where-Object {
        $_.ProcessId -ne $currentPid -and
        $_.CommandLine -and
        (
            $_.CommandLine -like '*teamtools*scripts\dev-api.ps1*' -or
            $_.CommandLine -like '*uvicorn*app.main:app*--port 8000*' -or
            $_.CommandLine -like '*teamtools\backend\.venv\Scripts\uvicorn.exe*app.main:app*' -or
            $_.CommandLine -like '*teamtools\backend*uvicorn*app.main:app*' -or
            (
                $_.CommandLine -like '*multiprocessing.spawn*' -and
                $_.CommandLine -like '*--multiprocessing-fork*'
            )
        )
    }

    $processIds = @()
    $rootProcessIds = @($rootProcesses | Select-Object -ExpandProperty ProcessId)
    if ($rootProcessIds.Count -gt 0) {
        $processIds += Get-ProcessTreeIds -RootProcessIds $rootProcessIds -AllProcesses $allProcesses
    }

    $listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listeners) {
        $processIds += $listeners | Select-Object -ExpandProperty OwningProcess
    }

    return @($processIds | Where-Object { $_ -and $_ -ne $currentPid } | Select-Object -Unique)
}

for ($attempt = 1; $attempt -le 5; $attempt++) {
    $processIds = @(Get-TeamToolsBackendProcessIds)
    if ($processIds.Count -eq 0) {
        break
    }

    Write-Host "Stop attempt ${attempt}: $($processIds -join ', ')"
    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Stopping PID ${processId} ($($process.ProcessName))"
            & taskkill.exe /PID $processId /T /F | Out-Host
        }
    }
    Start-Sleep -Seconds 2
}

$remaining = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    $remainingIds = @($remaining | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($processId in $remainingIds) {
        if ($processId -and $processId -ne $currentPid) {
            Write-Host "Force stopping remaining listener PID ${processId}"
            & taskkill.exe /PID $processId /T /F | Out-Host
        }
    }
    Start-Sleep -Seconds 2
}

$remaining = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    $remainingIds = $remaining | Select-Object -ExpandProperty OwningProcess -Unique
    throw "Port 8000 is still occupied by PID(s): $($remainingIds -join ', ')"
}

$launcher = Start-Process `
    -FilePath 'powershell.exe' `
    -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $root 'scripts\dev-api.ps1')) `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -PassThru

Write-Host "Started backend launcher PID $($launcher.Id)"

Start-Sleep -Seconds 8

try {
    $health = Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 10
    $health | ConvertTo-Json -Depth 5
} catch {
    Write-Host '--- stdout tail ---'
    if (Test-Path -LiteralPath $outLog) {
        Get-Content -LiteralPath $outLog -Encoding utf8 -Tail 80
    }
    Write-Host '--- stderr tail ---'
    if (Test-Path -LiteralPath $errLog) {
        Get-Content -LiteralPath $errLog -Encoding utf8 -Tail 120
    }
    throw
}
