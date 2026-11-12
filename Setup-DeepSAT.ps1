param(
    [string] $Python
)

$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
if ($Python) {
    $runtime = (Get-Command $Python -CommandType Application).Source
    & $runtime -c 'import tensorflow, pandas, numpy, matplotlib, rdkit, tkinter'
    if ($LASTEXITCODE -ne 0) {
        throw 'The supplied Python environment needs the packages in requirements.txt and Tkinter.'
    }
} else {
    $runtime = Join-Path $workspace '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $runtime)) {
        if (!(Get-Command py -ErrorAction SilentlyContinue)) {
            throw 'Use the Python 3.11 Windows launcher (py), or pass -Python with an existing environment that has the dependencies installed.'
        }
        & py -3.11 -m venv (Join-Path $workspace '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.11 virtual environment.' }
    }
    & $runtime -m pip install -r (Join-Path $workspace 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the DeepSAT dependencies.' }
}

& $runtime -X utf8 (Join-Path $workspace 'fetch_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not download the DeepSAT model files and database.' }

[IO.File]::WriteAllText((Join-Path $workspace '.python-path'), $runtime + [Environment]::NewLine)
Write-Host 'DeepSAT is ready. Open Open_DeepSAT.bat, then load an example or select an HSQC peak list.'
