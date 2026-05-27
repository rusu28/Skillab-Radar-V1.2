param(
    [ValidateSet("menu", "setup", "pipeline", "dashboard", "tests", "full", "notebooks")]
    [string]$Command = "menu",
    [string]$SkillsPath = "",
    [string]$OccupationsPath = "",
    [switch]$RefreshCache
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Resolve-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @("py", "-3") }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return @("python") }
    throw "Python was not found. Install Python 3 and tick 'Add python.exe to PATH'."
}

function Invoke-BasePython($ArgsList) {
    $base = Resolve-Python
    if ($base.Count -gt 1) {
        & $base[0] $base[1] @ArgsList
    } else {
        & $base[0] @ArgsList
    }
}

function Ensure-Venv {
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "Creating local virtual environment..."
        Invoke-BasePython @("-m", "venv", ".venv")
    }
    return Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}

function Ensure-Requirements($Python) {
    $marker = Join-Path $PSScriptRoot ".venv\.skillradar_deps_installed"
    if (-not (Test-Path $marker)) {
        & $Python -m pip install -r requirements.txt
        New-Item -ItemType File -Path $marker -Force | Out-Null
    }
}

function Invoke-Setup($Python) {
    & $Python -m pip install -r requirements.txt
    New-Item -ItemType File -Path (Join-Path $PSScriptRoot ".venv\.skillradar_deps_installed") -Force | Out-Null
    $args = @("auto_config.py", "--smoke-test")
    if ($SkillsPath) { $args += @("--skills", $SkillsPath) }
    if ($OccupationsPath) { $args += @("--occupations", $OccupationsPath) }
    & $Python @args
}

function Invoke-Pipeline($Python) {
    $args = @("-m", "src.pipeline", "--config", "config.yaml")
    if ($RefreshCache) { $args += "--refresh-cache" }
    & $Python @args
}

function Invoke-Dashboard($Python) {
    & $Python -m streamlit run app/streamlit_app.py
}

function Invoke-Notebooks($Python) {
    & $Python -m pip install -r requirements.txt
    New-Item -ItemType File -Path (Join-Path $PSScriptRoot ".venv\.skillradar_deps_installed") -Force | Out-Null
    & $Python -m notebook notebooks
}

function Invoke-Tests($Python) {
    & $Python -m unittest discover -s tests
}

function Show-Menu {
    Write-Host ""
    Write-Host "SKILLAB Skill Radar"
    Write-Host "==================="
    Write-Host "1. Setup / auto-configure this PC"
    Write-Host "2. Run pipeline and regenerate outputs"
    Write-Host "3. Start Streamlit dashboard"
    Write-Host "4. Run tests"
    Write-Host "5. Full local rebuild"
    Write-Host "6. Start Jupyter notebooks"
    Write-Host "0. Exit"
    $choice = Read-Host "Choose"
    switch ($choice) {
        "1" { return "setup" }
        "2" { return "pipeline" }
        "3" { return "dashboard" }
        "4" { return "tests" }
        "5" { return "full" }
        "6" { return "notebooks" }
        default { return "exit" }
    }
}

$python = Ensure-Venv
if ($Command -ne "menu") {
    Ensure-Requirements $python
}
if ($Command -eq "menu") {
    $Command = Show-Menu
    if ($Command -ne "exit") {
        Ensure-Requirements $python
    }
}

switch ($Command) {
    "setup" { Invoke-Setup $python }
    "pipeline" { Invoke-Pipeline $python }
    "dashboard" { Invoke-Dashboard $python }
    "notebooks" { Invoke-Notebooks $python }
    "tests" { Invoke-Tests $python }
    "full" {
        Invoke-Setup $python
        Invoke-Pipeline $python
        Invoke-Tests $python
    }
}
