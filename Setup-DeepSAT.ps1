param(
    [string] $Python
)

$ErrorActionPreference = 'Stop'
$workspace = $PSScriptRoot
$upstream = Join-Path $workspace 'upstream'
$revision = 'e50336bc1574a966c2c7831110cfc99b0e8401a3'

function Test-Upstream([string] $Folder) {
    foreach ($file in @('Classifier/SMART_3.py', 'Classifier/superclass.json', 'Classifier/input/Calcd_42086.csv', 'test/swinolide.csv', 'LICENSE')) {
        if (!(Test-Path -LiteralPath (Join-Path $Folder $file) -PathType Leaf)) { return $false }
    }
    return $true
}

if (!(Test-Upstream $upstream)) {
    if ((Test-Path -LiteralPath (Join-Path $workspace '.git')) -and (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        & git.exe -C $workspace submodule update --init -- upstream
        if ($LASTEXITCODE -ne 0) { throw 'Git could not initialize the DeepSAT submodule.' }
    }
}

if (!(Test-Upstream $upstream)) {
    if ((Test-Path -LiteralPath $upstream) -and (Get-ChildItem -LiteralPath $upstream -Force | Select-Object -First 1)) {
        throw 'The upstream folder is incomplete and contains files. For a Git clone, run git submodule update --init. For a ZIP download, extract a fresh copy and run setup there.'
    }
    Write-Host 'Downloading the pinned DeepSAT source from GitHub...'
    $staging = Join-Path $workspace ('.upstream-' + [guid]::NewGuid().ToString('N'))
    $archive = "$staging.zip"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/mwang87/DeepSAT/zip/$revision" -OutFile $archive
        New-Item -ItemType Directory -Path $staging | Out-Null
        & tar.exe -xf $archive -C $staging --strip-components 1
        if ($LASTEXITCODE -ne 0 -or !(Test-Upstream $staging)) { throw 'Could not extract the pinned DeepSAT source.' }
        if (Test-Path -LiteralPath $upstream) { [IO.Directory]::Delete($upstream) }
        [IO.Directory]::Move($staging, $upstream)
    } finally {
        if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive }
        if (Test-Path -LiteralPath $staging) {
            $resolvedStaging = (Resolve-Path -LiteralPath $staging).ProviderPath
            if ([IO.Path]::GetDirectoryName($resolvedStaging) -eq $workspace -and $resolvedStaging -eq $staging) {
                Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
            }
        }
    }
}

function Find-Python311 {
    $probe = 'import sys; print(sys.executable) if sys.version_info[:2] == (3, 11) and sys.maxsize > 2**32 else sys.exit(1)'
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        $candidate = & py.exe -3.11 -c $probe 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate }
    }
    $installed = Get-ItemProperty -Path 'HKCU:\Software\Python\PythonCore\3.11\InstallPath', 'HKLM:\Software\Python\PythonCore\3.11\InstallPath' -ErrorAction SilentlyContinue
    $candidates = @($installed | ForEach-Object { $_.ExecutablePath })
    $candidates += @(Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    foreach ($candidate in $candidates) {
        if (!$candidate -or $candidate -like '*\Microsoft\WindowsApps\python.exe' -or !(Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $executable = & $candidate -c $probe 2>$null
        if ($LASTEXITCODE -eq 0 -and $executable) { return $executable }
    }
}

if ($Python) {
    $runtime = (Get-Command $Python -CommandType Application).Source
} else {
    $runtime = Join-Path $workspace '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $runtime -PathType Leaf)) {
        $basePython = Find-Python311
        if (!$basePython -and (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
            Write-Host 'Installing 64-bit Python 3.11 for the current user with WinGet...'
            & winget.exe install --id Python.Python.3.11 --exact --source winget --scope user --architecture x64
            $basePython = Find-Python311
        }
        if (!$basePython) { throw 'Install 64-bit Python 3.11 from python.org with the Python launcher and Tcl/Tk enabled, then rerun setup.' }
        & $basePython -m venv (Join-Path $workspace '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.11 virtual environment.' }
    }
    & $runtime -m pip install -r (Join-Path $workspace 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the DeepSAT dependencies.' }
}

& $runtime -c 'import tensorflow, keras, pandas, numpy, matplotlib, rdkit, tkinter'
if ($LASTEXITCODE -ne 0) { throw 'Python could not import the required packages or Tkinter. See TROUBLESHOOTING.md.' }

& $runtime -X utf8 (Join-Path $workspace 'fetch_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Could not download the DeepSAT model files and database.' }

if ($Python) {
    [IO.File]::WriteAllText((Join-Path $workspace '.python-path'), $runtime + [Environment]::NewLine)
} elseif (Test-Path -LiteralPath (Join-Path $workspace '.python-path')) {
    Remove-Item -LiteralPath (Join-Path $workspace '.python-path')
}
Write-Host 'DeepSAT is ready. Open Open_DeepSAT.bat, then load an example or select an HSQC peak list.'
