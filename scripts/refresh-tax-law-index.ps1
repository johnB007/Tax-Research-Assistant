param(
    [string]$PythonPath = "python",
     [string]$ProjectPath = "C:\path\to\Tax-Research-Assistant"
)

$ErrorActionPreference = "Stop"

Push-Location $ProjectPath
try {
    & $PythonPath "scripts\refresh_law_index.py"
}
finally {
    Pop-Location
}
