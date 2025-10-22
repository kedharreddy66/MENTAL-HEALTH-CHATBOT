<#
  Setup Gmail SMTP for OTP and start the chatbot API (Windows PowerShell)
  Usage examples:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\scripts\setup_gmail_otp.ps1 -Email "you@gmail.com" -RequireAuth -DebugOtp
    .\scripts\setup_gmail_otp.ps1 -Email "you@gmail.com" -AppPassword "YOUR_APP_PASSWORD" -RequireAuth -DebugOtp
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)] [string]$Email,
  [Parameter(Mandatory=$false)] [string]$AppPassword,
  [Parameter(Mandatory=$false)] [int]$Port = 8765,
  [Parameter(Mandatory=$false)] [switch]$RequireAuth,
  [Parameter(Mandatory=$false)] [switch]$DebugOtp
)

function Read-Secret($Prompt) {
  $sec = Read-Host -AsSecureString -Prompt $Prompt
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

Write-Host "-- Gmail SMTP setup for OTP --" -ForegroundColor Cyan
if (-not $Email) { $Email = Read-Host -Prompt "Enter your Gmail address (e.g., you@gmail.com)" }
if (-not $AppPassword) {
  Write-Host "Enter your Gmail App Password (16 chars; no spaces)." -ForegroundColor Yellow
  $AppPassword = Read-Secret "App Password"
}

# Set env vars for this PowerShell process so uvicorn inherits them
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SMTP_USER = $Email
$env:SMTP_PASS = $AppPassword
$env:SMTP_FROM = $Email
$env:REQUIRE_AUTH = $(if ($RequireAuth) { "true" } else { "false" })
if ($DebugOtp) { $env:DEBUG_OTP = "1" } else { Remove-Item Env:DEBUG_OTP -ErrorAction SilentlyContinue }

Write-Host "Configured SMTP for $Email (host=smtp.gmail.com, port=587)." -ForegroundColor Green
if ($RequireAuth) { Write-Host "RequireAuth: ON (users must log in)." -ForegroundColor Yellow }
if ($DebugOtp) { Write-Host "DEBUG_OTP: ON (will log OTP send events)." -ForegroundColor Yellow }

Write-Host "Starting API on http://127.0.0.1:$Port ..." -ForegroundColor Cyan
Start-Process -FilePath "python" -ArgumentList @("-m","uvicorn","src.mh_core.api:app","--host","0.0.0.0","--port","$Port") -NoNewWindow
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:$Port/auth.html"

Write-Host "If the browser didn’t open, visit: http://127.0.0.1:$Port/auth.html" -ForegroundColor Gray
