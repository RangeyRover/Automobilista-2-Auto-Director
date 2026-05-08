Add-Type -AssemblyName System.IO.Compression.FileSystem

$dashDir = $PSScriptRoot
$outDir = Join-Path $dashDir "_extracted"

if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$dashFiles = Get-ChildItem -Path $dashDir -Filter "*.simhubdash"

foreach ($f in $dashFiles) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
    $targetDir = Join-Path $outDir $name
    
    Write-Output "--- Extracting: $name ---"
    
    if (!(Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir | Out-Null }
    
    try {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($f.FullName)
        foreach ($entry in $zip.Entries) {
            Write-Output "  $($entry.FullName) ($($entry.Length) bytes)"
            $destPath = Join-Path $targetDir $entry.FullName
            $destDir = [System.IO.Path]::GetDirectoryName($destPath)
            if (!(Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            if ($entry.FullName -notmatch '/$') {
                [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
            }
        }
        $zip.Dispose()
    } catch {
        Write-Output "  ERROR: $_"
    }
    Write-Output ""
}

Write-Output "Done. Extracted $($dashFiles.Count) dash files."
