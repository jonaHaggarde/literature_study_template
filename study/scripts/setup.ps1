# One-time environment setup: creates a virtual environment and installs
# dependencies. Run from anywhere; this script locates study/ itself.
#
#   .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Installing dependencies..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r scripts\requirements.txt

Write-Host ""
Write-Host "Done. Activate the environment in your shell with:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host "Then drop PDFs into PDFs\ and run: python scripts\convert.py"
