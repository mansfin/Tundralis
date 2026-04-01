$ErrorActionPreference = 'Stop'

$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$debugDir = 'C:\temp\chrome-debug'

if (-not (Test-Path $chrome)) {
  throw "Chrome not found at $chrome"
}

New-Item -ItemType Directory -Force -Path $debugDir | Out-Null

try {
  taskkill /IM chrome.exe /F | Out-Null
} catch {
  # ignore if Chrome was not running
}

Start-Process $chrome '--remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="C:\temp\chrome-debug"'

Start-Sleep -Seconds 2
Invoke-WebRequest http://127.0.0.1:9222/json/version | Out-Null
Write-Host 'Automation Chrome launched with CDP on 127.0.0.1:9222'
