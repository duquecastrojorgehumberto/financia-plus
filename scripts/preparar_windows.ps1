# FINANCIA+ - Prepara el entorno en Windows (Tarea 1) y ejecuta la migracion y las pruebas.
#
# Uso, en PowerShell, desde la carpeta del proyecto:
#   powershell -ExecutionPolicy Bypass -File .\scripts\preparar_windows.ps1
#
# Que hace (se puede ejecutar varias veces; lo que ya existe no se repite):
#   1. Instala con winget lo que falte: Python 3.13, Git y PostgreSQL 17.
#   2. Crea el entorno virtual .venv e instala requirements.txt.
#   3. Crea .env, los roles financia_admin y financia_app y las bases financia y financia_pruebas.
#   4. Aplica las migraciones en las dos bases.
#   5. Ejecuta todas las pruebas.
# Nunca borra nada. Windows pedira permiso de administrador para instalar: responda "Si".

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

function Paso($texto) { Write-Host ""; Write-Host "=== $texto ===" -ForegroundColor Cyan }
function Tiene($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function RefrescarPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Instalar($id) {
    Write-Host "Instalando $id con winget..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
    RefrescarPath
}

# Devuelve la ruta de un python.exe 3.11 o superior, o $null.
function BuscarPython {
    $candidatos = @()
    if (Tiene "py") {
        try { $candidatos += (& py -3 -c "import sys; print(sys.executable)" 2>$null) } catch {}
    }
    $candidatos += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe", "C:\Program Files\Python3*\python.exe" -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
    if (Tiene "python") { $candidatos += (Get-Command python).Source }
    foreach ($exe in $candidatos) {
        if (-not $exe -or $exe -like "*WindowsApps*") { continue }   # el atajo de la Tienda no sirve
        try {
            $ok = & $exe -c "import sys; print(1 if sys.version_info >= (3, 11) else 0)" 2>$null
            if ($ok -eq "1") { return $exe }
        } catch {}
    }
    return $null
}

function BuscarPsql {
    $p = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue |
         Sort-Object { [int]($_.Directory.Parent.Name -replace '\D', '') } | Select-Object -Last 1
    if ($p) { return $p.FullName } else { return $null }
}

function LeerClave($mensaje) {
    $seguro = Read-Host $mensaje -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

# ---------------------------------------------------------------- 1. Programas
Paso "1. Programas"
if (-not (Tiene "winget")) { throw "No se encontro winget. Actualice 'Instalador de aplicacion' desde Microsoft Store y vuelva a intentarlo." }

$Python = BuscarPython
if (-not $Python) { Instalar "Python.Python.3.13"; $Python = BuscarPython }
if (-not $Python) { throw "Python se instalo pero no se encuentra. Cierre PowerShell, abralo de nuevo y repita el comando." }
Write-Host "Python: $Python ($(& $Python --version))"

if (-not (Tiene "git")) { Instalar "Git.Git" }
if (Tiene "git") { Write-Host "Git: $(git --version)" } else { Write-Host "Git: instalado; estara disponible al reabrir PowerShell." }

$Psql = BuscarPsql
if (-not $Psql) {
    Write-Host ""
    Write-Host "PostgreSQL no esta instalado. Elija la contrasena del usuario administrador 'postgres'." -ForegroundColor Yellow
    Write-Host "Guardela bien. Sin espacios ni comillas. No se la escriba a nadie, tampoco a Claude." -ForegroundColor Yellow
    $ClavePostgres = LeerClave "Nueva contrasena para postgres"
    Write-Host "Instalando PostgreSQL 17 (tarda unos minutos)..."
    winget install --id PostgreSQL.PostgreSQL.17 -e --accept-package-agreements --accept-source-agreements `
        --override "--mode unattended --unattendedmodeui minimal --superpassword `"$ClavePostgres`" --serverport 5432"
    $Psql = BuscarPsql
    if (-not $Psql) { throw "PostgreSQL no quedo instalado. Revise los mensajes de arriba." }
} else {
    $ClavePostgres = LeerClave "Contrasena del usuario 'postgres' de su PostgreSQL"
}
$env:Path = (Split-Path $Psql) + ";" + $env:Path
Write-Host "PostgreSQL: $(& $Psql --version)"

# ---------------------------------------------------------------- 2. Entorno virtual
Paso "2. Entorno virtual y librerias"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $Python -m venv .venv }
$Py = Join-Path $Raiz ".venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip --quiet
& $Py -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de librerias." }
& $Py -m pip freeze

# ---------------------------------------------------------------- 3. Bases de datos
Paso "3. Archivo .env, rol y bases de datos"
$env:FINANCIA_CLAVE_POSTGRES = $ClavePostgres
try { & $Py scripts\preparar_bd.py } finally { Remove-Item Env:\FINANCIA_CLAVE_POSTGRES -ErrorAction SilentlyContinue }
if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar las bases." }

# ---------------------------------------------------------------- 4. Migraciones
Paso "4. Migraciones"
& $Py scripts\migrar.py
if ($LASTEXITCODE -ne 0) { throw "Fallo la migracion en la base principal." }
& $Py scripts\migrar.py --variable DATABASE_URL_PRUEBAS
if ($LASTEXITCODE -ne 0) { throw "Fallo la migracion en la base de pruebas." }

# ---------------------------------------------------------------- 5. Pruebas
Paso "5. Pruebas de restricciones"
& $Py -m pytest tests -q -rs | Tee-Object -FilePath "tests\ultimo_resultado.txt"
$resultado = $LASTEXITCODE

Write-Host ""
if ($resultado -eq 0) { Write-Host "Listo: todas las pruebas pasaron." -ForegroundColor Green }
else { Write-Host "Algunas pruebas fallaron. El detalle quedo en tests\ultimo_resultado.txt: avisele a Claude." -ForegroundColor Yellow }
