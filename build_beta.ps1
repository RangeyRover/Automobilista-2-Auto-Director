$ErrorActionPreference = "Stop"

Write-Host "Cleaning beta_staging..."
If (Test-Path "beta_staging") {
    Remove-Item -Recurse -Force "beta_staging"
}
New-Item -ItemType Directory -Force "beta_staging"

# Core Application
Write-Host "Copying core application files..."
Copy-Item "main.py" "beta_staging\"
Copy-Item "shared_memory_struct.py" "beta_staging\"
Copy-Item "README.md" "beta_staging\"
Copy-Item "LICENSE" "beta_staging\"
Copy-Item "OVERLAYS_GUIDE.md" "beta_staging\"

# Copy modules recursively
Write-Host "Copying directories..."
Copy-Item -Recurse "core" "beta_staging\"
Copy-Item -Recurse "dashboard" "beta_staging\"

# Clean up junk from staging
Write-Host "Cleaning development files from staging..."
Get-ChildItem -Path "beta_staging" -Include "*.djson", "*.djson.*", "test_time.html", "*.ps1" -Recurse | Remove-Item -Force
Get-ChildItem -Path "beta_staging" -Include "__pycache__", "_extracted", "Videos", "_SHFonts" -Recurse -Directory | Remove-Item -Recurse -Force

Write-Host "Generating PyInstaller Build in beta_staging..."
Set-Location "beta_staging"
pyinstaller --name "AMS2_Auto_Director" `
            --onedir `
            --add-data "dashboard;dashboard" `
            --add-data "shared_memory_struct.py;." `
            --hidden-import "websockets" `
            --hidden-import "websockets.legacy" `
            --hidden-import "websockets.legacy.server" `
            --hidden-import "keyboard" `
            main.py

Write-Host "Zipping the beta release..."
Compress-Archive -Path "dist\AMS2_Auto_Director" -DestinationPath "AMS2_Auto_Director_v4.1.7-beta.zip" -Force

Write-Host "Done!"
