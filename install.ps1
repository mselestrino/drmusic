$ErrorActionPreference = "Stop"

$Owner = "mselestrino"
$Repo = "drmusic"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\DrMusic"
$ApiUrl = "https://api.github.com/repos/$Owner/$Repo/releases/tags/latest"

Write-Host ""
Write-Host "  DrMusic - inicializador" -ForegroundColor Green
Write-Host "  Preparando o aplicativo..." -ForegroundColor Gray
Write-Host ""

try {
    $release = Invoke-RestMethod -Uri $ApiUrl -Headers @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "DrMusic-Installer"
    }

    $asset = $release.assets | Where-Object { $_.name -eq "DrMusic-windows.zip" } | Select-Object -First 1
    if (-not $asset) {
        throw "Ainda não existe uma versão pronta para download. O primeiro build pode levar alguns minutos após a publicação dos arquivos."
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $zipPath = Join-Path $env:TEMP "DrMusic-windows.zip"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    $exe = Join-Path $InstallDir "DrMusic.exe"
    if (-not (Test-Path $exe)) {
        throw "O pacote baixado não contém DrMusic.exe."
    }

    Write-Host "Aplicativo pronto! Abrindo DrMusic..." -ForegroundColor Green
    Start-Process -FilePath $exe
}
catch {
    Write-Host "Não foi possível iniciar o DrMusic:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Confira as versões em: https://github.com/$Owner/$Repo/releases" -ForegroundColor Gray
}
