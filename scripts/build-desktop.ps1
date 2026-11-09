# Builds the Windows x64 app and installer into dist-desktop\. Run on Windows x64 with
# Python 3.12, Node 22 and Inno Setup 6.3+ (ISCC on PATH or in its default folder).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = if ($env:PYTHON) { $env:PYTHON } else { "backend\.venv\Scripts\python.exe" }
$version = & $py -c "import tomllib;print(tomllib.load(open('backend/pyproject.toml','rb'))['project']['version'])"
if ($LASTEXITCODE -ne 0) { throw "could not read the version" }
$work = "build\desktop"

Write-Host "== web app"
Push-Location frontend
if (-not (Test-Path node_modules)) { npm ci; if ($LASTEXITCODE -ne 0) { throw "npm ci failed" } }
npm run build; if ($LASTEXITCODE -ne 0) { throw "web build failed" }
Pop-Location

Write-Host "== icons"
if (-not (Test-Path desktop\assets\cockpit.ico)) { & $py desktop\make_icons.py }

Write-Host "== app folder"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
& $py -m PyInstaller desktop\cockpit.spec --noconfirm --distpath "$work\dist" --workpath "$work\work"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "== installer"
New-Item -ItemType Directory -Force dist-desktop | Out-Null
$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) { $iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "Inno Setup (ISCC.exe) not found: install it from https://jrsoftware.org/isinfo.php" }
& $iscc "/DAppVersion=$version" desktop\installer.iss
if ($LASTEXITCODE -ne 0) { throw "installer build failed" }
# The same app as a plain zip, for Scoop (no installer, no admin rights).
$zip = "dist-desktop\Cockpit-$version-windows-x64.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path "$work\dist\Cockpit" -DestinationPath $zip
Write-Host "built dist-desktop\Cockpit-$version-windows-x64-setup.exe and $zip"
