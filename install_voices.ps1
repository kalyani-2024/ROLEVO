# PowerShell script to install additional Windows TTS voices
# Run as Administrator: Right-click PowerShell -> Run as Administrator

Write-Host "============================================" -ForegroundColor Green
Write-Host "Windows TTS Voice Installer" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Installing additional English voices..." -ForegroundColor Cyan

# Install English (US) voices
Add-WindowsCapability -Online -Name "Language.Speech~~~en-US~"
Add-WindowsCapability -Online -Name "Language.TextToSpeech~~~en-US~"

# Install English (UK) voices  
Add-WindowsCapability -Online -Name "Language.Speech~~~en-GB~"
Add-WindowsCapability -Online -Name "Language.TextToSpeech~~~en-GB~"

# Install English (India) voices
Add-WindowsCapability -Online -Name "Language.Speech~~~en-IN~"
Add-WindowsCapability -Online -Name "Language.TextToSpeech~~~en-IN~"

# Install Hindi voices
Add-WindowsCapability -Online -Name "Language.Speech~~~hi-IN~"
Add-WindowsCapability -Online -Name "Language.TextToSpeech~~~hi-IN~"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "Voice installation complete!" -ForegroundColor Green
Write-Host "Restart your computer for changes to take effect." -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "After restart, run 'python check_voices.py' to see available voices." -ForegroundColor Cyan
