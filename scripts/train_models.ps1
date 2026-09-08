# SIH26054 training script (Windows PowerShell / pwsh). Run only when you want
# to (re)train; the demo also works without trained models.
#
# Usage:
#   .\scripts\train_models.ps1                  # CPU baselines (scikit-learn)
#   .\scripts\train_models.ps1 -Gpu             # GPU/PyTorch models
#   .\scripts\train_models.ps1 -Gpu -TrainArgs @("--device","cuda:0","--epochs","30")
#   .\scripts\train_models.ps1 -Missions 60
# zsh/bash users: run scripts/train_models.sh instead.
[CmdletBinding()]
param(
    [switch]$Gpu,
    [int]$Missions = 40,
    [string[]]$TrainArgs = @(),
    [switch]$Help
)

if ($Help) {
    Get-Content $MyInvocation.MyCommand.Path | Select-Object -Skip 1 -First 8 | ForEach-Object { $_ -replace "^# ?", "" }
    exit 0
}

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$pyExe = Join-Path ".venv" "Scripts" | Join-Path -ChildPath "python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Error ".venv not found. Run .\scripts\setup.ps1 first."
    exit 1
}

# 1. Dataset ---------------------------------------------------------------
$trainCsv = Join-Path "data" "train.csv"
if (-not (Test-Path $trainCsv)) {
    Write-Host "==> Generating synthetic dataset (fixed seed, identical everywhere)"
    & $pyExe -m simulator.generate_dataset --missions $Missions --rows-per-mission 4000
    if ($LASTEXITCODE -ne 0) { Write-Error "dataset generation failed"; exit 1 }
} else {
    Write-Host "==> Dataset already present (data/train.csv); skipping generation"
}

# 2. Models ----------------------------------------------------------------
if ($Gpu) {
    Write-Host "==> Training PyTorch models (anomaly AE, fault MLP, degradation + RUL)"
    & $pyExe -m ml.train_gpu --task all --device auto @TrainArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "GPU training failed"; exit 1 }
} else {
    Write-Host "==> Training anomaly detection model (scikit-learn)"
    & $pyExe -m ml.train_anomaly
    if ($LASTEXITCODE -ne 0) { Write-Error "anomaly training failed"; exit 1 }

    Write-Host "==> Training fault classifier model (scikit-learn)"
    & $pyExe -m ml.train_fault_classifier
    if ($LASTEXITCODE -ne 0) { Write-Error "fault classifier training failed"; exit 1 }

    Write-Host "==> Training degradation + RUL models (scikit-learn)"
    & $pyExe -m ml.train_degradation_rul
    if ($LASTEXITCODE -ne 0) { Write-Error "degradation/RUL training failed"; exit 1 }
}

Write-Host ""
Write-Host "All models saved to models/. Verify with:"
Write-Host "  .\scripts\predict.ps1 --status"
