$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $parentPython = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $parentPython) { $python = $parentPython }
    else {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or newer, then retry.' }
    }
}
& $python -c "import flask, flask_sqlalchemy, dotenv"
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
$env:DATABASE_URL = 'sqlite:///farmer_marketplace.db'
& $python initialize_db.py
if ($LASTEXITCODE -ne 0) { throw 'Database setup failed.' }
& $python testdata.py
if ($LASTEXITCODE -ne 0) { throw 'Demo data setup failed.' }
Write-Host 'Open http://127.0.0.1:5000. Farmer keys are in demo-credentials.json.'
& $python app.py
