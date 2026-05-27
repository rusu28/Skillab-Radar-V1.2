param(
    [string]$SkillsPath = "",
    [string]$OccupationsPath = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Setting up SKILLAB Skill Radar in a local .venv..."
if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is not installed or not on PATH. Install Python 3 first."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } else {
        python -m venv .venv
    }
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $python -m pip install -r requirements.txt

$args = @("auto_config.py", "--smoke-test")
if ($SkillsPath) { $args += @("--skills", $SkillsPath) }
if ($OccupationsPath) { $args += @("--occupations", $OccupationsPath) }
& $python @args

Write-Host ""
Write-Host "Setup complete. Next:"
Write-Host "  .\run.ps1 pipeline"
Write-Host "  .\run.ps1 dashboard"
