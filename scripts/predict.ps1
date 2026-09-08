# SIH26054 inference CLI wrapper (Windows PowerShell / pwsh).
# Examples:
#   .\scripts\predict.ps1 --status
#   .\scripts\predict.ps1 --csv data\test.csv --out data\predictions.csv
#   .\scripts\predict.ps1 --simulate --profile hot_weather --fault-type overheating --severity 0.7
#   .\scripts\predict.ps1 --live --interval 1
# zsh/bash users: run scripts/predict.sh instead.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$pyExe = Join-Path ".venv" "Scripts" | Join-Path -ChildPath "python.exe"
if (-not (Test-Path $pyExe)) {
    Write-Error ".venv not found. Run .\scripts\setup.ps1 first."
    exit 1
}

# All arguments pass straight through to python -m ml.predict
& $pyExe -m ml.predict @args
exit $LASTEXITCODE
