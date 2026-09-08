# SIH26054 one-time setup (Windows PowerShell / pwsh).
# Creates the Python venv, installs pip + npm deps.
# GPU extras: .\scripts\setup.ps1 -WithGpu
# zsh/bash users: run scripts/setup.sh instead.
#
# Usage:
#   .\scripts\setup.ps1              # CPU setup
#   .\scripts\setup.ps1 -WithGpu     # also install CUDA PyTorch + GPU requirements
[CmdletBinding()]
param(
    [switch]$WithGpu,
    [switch]$Help
)

if ($Help) {
    Get-Content $MyInvocation.MyCommand.Path | Select-Object -Skip 1 -First 7 | ForEach-Object { $_ -replace "^# ?", "" }
    exit 0
}

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Find a Python launcher (py launcher, python, then python3)
$python = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $python = $candidate
        break
    }
}
if (-not $python) {
    throw "No Python launcher found. Install Python 3.11+ from https://python.org"
}

$pyExe = Join-Path ".venv" "Scripts" | Join-Path -ChildPath "python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Host "==> Creating Python virtual environment (.venv)"
    & $python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
} else {
    Write-Host "==> Virtual environment already present (.venv)"
}

Write-Host "==> Upgrading pip"
& $pyExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

Write-Host "==> Installing Python dependencies"
& $pyExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }

if ($WithGpu) {
    Write-Host "==> Installing GPU (CUDA) build of PyTorch"
    & $pyExe -m pip install torch --index-url https://download.pytorch.org/whl/cu124
    & $pyExe -m pip install -r requirements-gpu.txt
    if ($LASTEXITCODE -ne 0) { throw "GPU dependency install failed" }
    Write-Host "    (match the cu124 tag to your driver - see docs/gpu_training.md)"
}

Write-Host "==> Installing frontend dependencies"
Push-Location frontend
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "npm install failed" }
Pop-Location

Write-Host ""
Write-Host "Setup complete. Next:"
Write-Host "  .\scripts\train_models.ps1          # CPU baselines"
Write-Host "  .\scripts\train_gpu.ps1             # GPU models"
Write-Host "  .\scripts\start_demo.ps1            # full stack"
