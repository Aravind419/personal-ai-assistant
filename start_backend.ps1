# Start Backend Development Server
Write-Host "=== Starting Personal AI Assistant - Backend ===" -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\backend"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
