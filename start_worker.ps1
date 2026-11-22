# Start Celery Background Task Worker
Write-Host "=== Starting Personal AI Assistant - Celery Worker ===" -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\backend"
$env:PYTHONPATH = "."
& ".\.venv\Scripts\celery.exe" -A app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo --concurrency=1
