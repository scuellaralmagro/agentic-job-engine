<#
.SYNOPSIS
    Starts the agentic-job-engine backend and frontend together.

.DESCRIPTION
    Runs both dev servers in this one window with per-service prefixes, and stops
    both cleanly on Ctrl+C.

    Two details this script exists to get right, both of which have bitten before:

      * The backend MUST start from backend/. `data_dir` is relative, so launching
        uvicorn from the repo root creates an empty data/aje.sqlite3 there and the
        app dies with "no such table: saved_searches".
      * `uv run uvicorn` and `npm run dev` each spawn a child process. Killing the
        parent orphans the child, which then keeps holding the port. Shutdown here
        kills the whole process tree.

    Missing setup is repaired on the way: `uv sync` when backend/.venv is absent,
    `npm install` when frontend/node_modules is absent, and `alembic upgrade head`
    always (a no-op when the DB is already current).

.PARAMETER BackendPort
    Port for uvicorn. Default 8000. The frontend's Vite proxy expects 8000, so
    changing this alone will break /api calls from the browser.

.PARAMETER FrontendPort
    Port for Vite. Default 5173.

.PARAMETER SkipSetup
    Skip the dependency and migration checks and launch immediately.

.EXAMPLE
    .\dev.ps1

.EXAMPLE
    .\dev.ps1 -SkipSetup
#>
[CmdletBinding()]
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipSetup
)

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"

function Write-Step($message) {
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Write-Problem($message) {
    Write-Host "!!! $message" -ForegroundColor Red
}

function Resolve-Launcher($name) {
    <#
        Start-Process needs something Windows can execute. `npm` resolves to npm.ps1
        under PowerShell, which Start-Process cannot run -- it would hand it to the
        shell's file association instead. Prefer the .cmd/.exe shim next to it.
    #>
    foreach ($candidate in @("$name.cmd", "$name.exe", $name)) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -eq $cmd) { continue }
        if ($cmd.CommandType -eq "Application") { return $cmd.Source }
    }
    return $null
}

function Test-PortBusy($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

# --- preflight ---------------------------------------------------------------

$UvExe = Resolve-Launcher "uv"
$NpmExe = Resolve-Launcher "npm"
foreach ($tool in @(@{Name = "uv"; Path = $UvExe }, @{Name = "npm"; Path = $NpmExe })) {
    if ($null -eq $tool.Path) {
        Write-Problem "$($tool.Name) is not on PATH. Install it and try again."
        exit 1
    }
}

foreach ($p in @(@{Name = "backend"; Port = $BackendPort }, @{Name = "frontend"; Port = $FrontendPort })) {
    if (Test-PortBusy $p.Port) {
        Write-Problem "Port $($p.Port) is already in use -- is a $($p.Name) server already running?"
        Write-Host "    Free it with:  Get-NetTCPConnection -LocalPort $($p.Port) -State Listen | ForEach-Object { Stop-Process -Id `$_.OwningProcess -Force }"
        exit 1
    }
}

# --- setup -------------------------------------------------------------------

if (-not $SkipSetup) {
    if (-not (Test-Path (Join-Path $BackendDir ".venv"))) {
        Write-Step "backend/.venv missing -- running uv sync (first run takes a while)"
        Push-Location $BackendDir
        try { uv sync } finally { Pop-Location }
    }

    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Step "frontend/node_modules missing -- running npm install"
        Push-Location $FrontendDir
        try { npm install } finally { Pop-Location }
    }

    # Idempotent and quick when already current, so it is simpler and safer to run
    # every time than to parse `alembic current` and compare against heads.
    Write-Step "applying database migrations"
    # Deliberately NOT `uv run alembic ... 2>&1`. In PowerShell 5.1, merging a native
    # command's stderr into the success stream wraps every line in an ErrorRecord, and
    # alembic logs its INFO output to stderr -- so a *successful* migration raises a
    # NativeCommandError and $ErrorActionPreference = "Stop" kills the script.
    # Start-Process redirects at the OS level and has no such behaviour.
    $migrationOut = Join-Path ([System.IO.Path]::GetTempPath()) "aje-alembic-$PID.log"
    $alembic = Start-Process -FilePath $UvExe `
        -ArgumentList "run alembic upgrade head" `
        -WorkingDirectory $BackendDir `
        -RedirectStandardError $migrationOut `
        -RedirectStandardOutput "$migrationOut.out" `
        -NoNewWindow -Wait -PassThru

    $migrationLog = ""
    if (Test-Path $migrationOut) { $migrationLog = Get-Content $migrationOut -Raw }
    Remove-Item $migrationOut, "$migrationOut.out" -Force -ErrorAction SilentlyContinue

    if ($alembic.ExitCode -ne 0) {
        Write-Problem "alembic upgrade head failed (exit $($alembic.ExitCode)):"
        Write-Host $migrationLog
        exit 1
    }
    if ($migrationLog -match "Running upgrade") {
        ($migrationLog -split "`r?`n") | Where-Object { $_ -match "Running upgrade" } | ForEach-Object {
            Write-Host "    $($_.Trim())"
        }
    }
}

# --- launch ------------------------------------------------------------------

$logDir = Join-Path ([System.IO.Path]::GetTempPath()) "aje-dev-$PID"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$services = @(
    [pscustomobject]@{
        Name      = "backend "
        Colour    = "Green"
        Directory = $BackendDir
        File      = $UvExe
        Arguments = "run uvicorn aje.app:create_app --factory --port $BackendPort"
        Process   = $null
        OutFile   = Join-Path $logDir "backend.out"
        ErrFile   = Join-Path $logDir "backend.err"
        OutAt     = 0
        ErrAt     = 0
    },
    [pscustomobject]@{
        Name      = "frontend"
        Colour    = "Magenta"
        Directory = $FrontendDir
        File      = $NpmExe
        Arguments = "run dev -- --port $FrontendPort"
        Process   = $null
        OutFile   = Join-Path $logDir "frontend.out"
        ErrFile   = Join-Path $logDir "frontend.err"
        OutAt     = 0
        ErrAt     = 0
    }
)

function Stop-Service($service) {
    if ($null -eq $service.Process) { return }
    if ($service.Process.HasExited) { return }
    # /T kills the whole tree. `uv run` and `npm run` are launchers: killing only
    # the parent leaves uvicorn or node alive and still holding the port.
    # `2> $null` discards, rather than `2>&1` which would wrap stderr in ErrorRecords
    # and can throw during cleanup under $ErrorActionPreference = "Stop".
    & taskkill.exe /PID $service.Process.Id /T /F > $null 2> $null
}

function Show-NewOutput($service) {
    foreach ($stream in @("Out", "Err")) {
        $path = $service."${stream}File"
        if (-not (Test-Path $path)) { continue }
        $length = (Get-Item $path).Length
        $seen = $service."${stream}At"
        if ($length -le $seen) { continue }

        $reader = [System.IO.File]::Open($path, "Open", "Read", "ReadWrite")
        try {
            $reader.Seek($seen, "Begin") | Out-Null
            $buffer = New-Object byte[] ($length - $seen)
            $read = $reader.Read($buffer, 0, $buffer.Length)
            $text = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
        } finally {
            $reader.Close()
        }
        $service."${stream}At" = $length

        foreach ($line in ($text -split "`r?`n")) {
            if ($line.Trim().Length -eq 0) { continue }
            Write-Host "[$($service.Name)] " -ForegroundColor $service.Colour -NoNewline
            Write-Host $line
        }
    }
}

try {
    foreach ($service in $services) {
        Write-Step "starting $($service.Name.Trim())"
        $service.Process = Start-Process -FilePath $service.File `
            -ArgumentList $service.Arguments `
            -WorkingDirectory $service.Directory `
            -RedirectStandardOutput $service.OutFile `
            -RedirectStandardError $service.ErrFile `
            -NoNewWindow -PassThru
        # Touching .Handle makes .NET cache the process handle. Without it the object
        # loses access to the exit code once the process dies and ExitCode reads back
        # as null, so a crash reports "exited with code " and tells you nothing.
        $null = $service.Process.Handle
    }

    Write-Host ""
    Write-Host "  backend   http://localhost:$BackendPort" -ForegroundColor Green
    Write-Host "  frontend  http://localhost:$FrontendPort" -ForegroundColor Magenta
    Write-Host "  Ctrl+C stops both." -ForegroundColor DarkGray
    Write-Host ""

    while ($true) {
        foreach ($service in $services) { Show-NewOutput $service }

        $dead = $services | Where-Object { $null -ne $_.Process -and $_.Process.HasExited }
        if ($dead) {
            Start-Sleep -Milliseconds 300
            foreach ($service in $services) { Show-NewOutput $service }
            # WaitForExit on an already-exited process returns at once, but it is what
            # makes ExitCode readable on a Start-Process -PassThru object; without it
            # the code comes back blank.
            $dead[0].Process.WaitForExit()
            $code = $dead[0].Process.ExitCode
            if ($null -eq $code) { $code = "unknown" }
            Write-Problem "$($dead[0].Name.Trim()) exited with code $code -- shutting the other one down too."
            break
        }
        Start-Sleep -Milliseconds 200
    }
} finally {
    # Runs on Ctrl+C as well as on a service dying, which is the point: without it
    # the servers outlive this window and keep their ports.
    Write-Host ""
    Write-Step "stopping both servers"
    foreach ($service in $services) { Stop-Service $service }
    Remove-Item $logDir -Recurse -Force -ErrorAction SilentlyContinue
}
