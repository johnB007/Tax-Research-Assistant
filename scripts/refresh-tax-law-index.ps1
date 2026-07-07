param(
    [string]$PythonPath = "python",
    [string]$ProjectPath = "C:\Users\jobarbar\github\Taxes"
)

$ErrorActionPreference = "Stop"

Push-Location $ProjectPath
try {
    & $PythonPath "scripts\refresh_law_index.py"
}
finally {
    Pop-Location
}
