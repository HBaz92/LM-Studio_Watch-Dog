$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -m lm_studio_watchdog serve
    exit $LASTEXITCODE
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & $py.Source -m lm_studio_watchdog serve
    exit $LASTEXITCODE
}

throw "Python 3.10+ was not found. Install Python from https://www.python.org/downloads/ and try again."
