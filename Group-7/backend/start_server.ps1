# Start server script for Intervexa backend
# This ensures the backend runs with the correct Python path

$env:PYTHONPATH = "$PSScriptRoot"
Set-Location $PSScriptRoot

Write-Host "Starting Intervexa Backend Server..." -ForegroundColor Green
Write-Host "PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "Working Directory: $(Get-Location)" -ForegroundColor Cyan

& "$PSScriptRoot\..\.venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
