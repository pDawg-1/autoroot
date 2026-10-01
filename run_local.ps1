$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$portablePython = Join-Path $PSScriptRoot '.runtime/python/python.exe'
if (Test-Path -LiteralPath $projectPython) {
    & $projectPython -m streamlit run app.py
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m streamlit run app.py
} elseif (Test-Path -LiteralPath $portablePython) {
    & $portablePython -m streamlit run app.py
} else {
    throw 'Install Python 3.10 or 3.11 and follow the README setup instructions.'
}
