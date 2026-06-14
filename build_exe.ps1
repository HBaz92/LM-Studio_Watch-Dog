$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pythonExe = $python.Source
} else {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $pythonExe = $py.Source
    } else {
        throw "Python 3.10+ was not found. Install Python from https://www.python.org/downloads/ and try again."
    }
}

& $pythonExe -m pip install -r requirements.txt
& $pythonExe -m pip install -r requirements-dev.txt
& $pythonExe -m PyInstaller --noconfirm --clean LM-Studio-WatchDog.spec

Write-Host ""
Write-Host "Portable EXE created at: dist\LM-Studio-WatchDog.exe"
