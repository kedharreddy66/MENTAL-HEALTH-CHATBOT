param(
  [string]$AuthToken,
  [int]$Port = 8765,
  [switch]$NoStartUvicorn
)

Write-Host "=== MH Chatbot: ngrok deployment helper ==="

# 1) Ensure ngrok is available
$ngrokCmd = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokCmd) {
  Write-Error "ngrok not found. Install from https://ngrok.com/download and ensure it is on PATH."
  exit 1
}

# 2) Optionally set authtoken
if ($AuthToken) {
  Write-Host "Configuring ngrok authtoken..."
  & ngrok config add-authtoken $AuthToken | Out-Null
}

# 3) Start Uvicorn (if not already listening)
function Test-PortOpen($port) {
  try {
    $r = Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue
    return $r.TcpTestSucceeded
  } catch { return $false }
}

if (-not $NoStartUvicorn) {
  if (-not (Test-PortOpen -port $Port)) {
    Write-Host "Starting Uvicorn on 0.0.0.0:$Port ..."
    Start-Process -NoNewWindow -FilePath python -ArgumentList @("-m","uvicorn","src.mh_core.api:app","--host","0.0.0.0","--port","$Port")
    Start-Sleep -Seconds 2
  } else {
    Write-Host "Uvicorn already listening on port $Port."
  }
}

# 4) Start ngrok tunnel
Write-Host "Starting ngrok http tunnel to port $Port ..."
Start-Process -NoNewWindow -FilePath ngrok -ArgumentList @("http","$Port")

# 5) Discover public URL via ngrok local API
$publicUrl = $null
for ($i=0; $i -lt 30; $i++) {
  try {
    $tunnels = Invoke-RestMethod -Method GET -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2
    $https = $tunnels.tunnels | Where-Object { $_.proto -eq 'https' } | Select-Object -First 1
    if ($https -and $https.public_url) { $publicUrl = $https.public_url; break }
  } catch {}
  Start-Sleep -Milliseconds 500
}

if (-not $publicUrl) {
  Write-Warning "Couldn't detect ngrok URL. Open http://127.0.0.1:4040/status in your browser to copy it."
  exit 0
}

Write-Host ""
Write-Host "Public URL: $publicUrl" -ForegroundColor Green
Write-Host "Open this in your browser and share it with others."
Write-Host "(It serves /chat.html and the UI calls the same origin.)"

