# PowerShell cleanup script to prepare for ZIP
Write-Host "Cleaning up heavy folders to reach ~30MB target..." -ForegroundColor Cyan

$folders = @(
    "node_modules",
    "frontend/node_modules",
    ".venv",
    ".git",
    "frontend/dist",
    "backend/__pycache__"
)

foreach ($folder in $folders) {
    if (Test-Path $folder) {
        Write-Host "Removing $folder..."
        Remove-Item -Recurse -Force $folder
    }
}

Write-Host "Cleanup complete! You can now ZIP the 'kalk_v3' folder." -ForegroundColor Green
