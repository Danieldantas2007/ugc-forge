@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title ugc-forge

echo.
echo   ================================================
echo    ugc-forge - geracao em lote
echo   ================================================
echo.

REM ---------------------------------------------- 1. Python instalado?
python --version >nul 2>&1
if errorlevel 1 (
    echo   [x] Python nao encontrado.
    echo.
    echo   Instale pela Microsoft Store ^(busque por "Python 3"^)
    echo   ou em python.org marcando "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------- 2. Dependencias
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo   Instalando dependencias, so na primeira vez...
    python -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo   [x] Falha ao instalar. Rode manualmente:
        echo       python -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo   [ok] Dependencias instaladas.
    echo.
)

REM ---------------------------------------------- 3. Chave da API
set "ATLASCLOUD_API_KEY="
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if /i "%%A"=="ATLASCLOUD_API_KEY" set "ATLASCLOUD_API_KEY=%%B"
    )
)

if "!ATLASCLOUD_API_KEY!"=="" goto ask_key
if "!ATLASCLOUD_API_KEY!"=="your-api-key-here" goto ask_key
goto have_key

:ask_key
echo   Sua chave da Atlas Cloud ainda nao esta salva.
echo   Pegue em: https://www.atlascloud.ai/console/api-keys
echo.
set /p "ATLASCLOUD_API_KEY=  Cole a chave aqui: "
if "!ATLASCLOUD_API_KEY!"=="" (
    echo.
    echo   [x] Nenhuma chave informada.
    pause
    exit /b 1
)
>".env" echo ATLASCLOUD_API_KEY=!ATLASCLOUD_API_KEY!
echo.
echo   [ok] Chave salva em .env ^(esse arquivo nunca vai pro GitHub^).
echo.

:have_key

REM ---------------------------------------------- 4. Qual CSV
set "CSVFILE=%~1"
if not "!CSVFILE!"=="" goto have_csv

set /a COUNT=0
echo   Arquivos CSV encontrados nesta pasta:
echo.
for %%F in (*.csv) do (
    set /a COUNT+=1
    set "CSV_!COUNT!=%%F"
    echo     !COUNT!^) %%F
)
for %%F in (examples\*.csv) do (
    set /a COUNT+=1
    set "CSV_!COUNT!=examples\%%~nxF"
    echo     !COUNT!^) examples\%%~nxF
)

if !COUNT!==0 (
    echo     ^(nenhum^)
    echo.
    echo   Coloque seu arquivo .csv nesta pasta e rode de novo,
    echo   ou arraste o arquivo em cima deste .bat.
    echo.
    pause
    exit /b 1
)

echo.
set /p "PICK=  Digite o numero do arquivo: "
set "CSVFILE=!CSV_%PICK%!"

if "!CSVFILE!"=="" (
    echo.
    echo   [x] Opcao invalida.
    pause
    exit /b 1
)

:have_csv
if not exist "!CSVFILE!" (
    echo.
    echo   [x] Arquivo nao encontrado: !CSVFILE!
    pause
    exit /b 1
)

echo.
echo   Arquivo: !CSVFILE!
echo.

REM ---------------------------------------------- 5. Teste antes de gastar
echo   Conferindo o arquivo sem gastar credito...
echo.
python -m src.forge run "!CSVFILE!" --dry-run --out ".\output"
if errorlevel 1 (
    echo.
    echo   [x] O arquivo tem algum problema. Corrija e rode de novo.
    echo.
    pause
    exit /b 1
)

echo.
echo   ------------------------------------------------
echo    Isso vai gerar de verdade e consumir credito.
echo   ------------------------------------------------
echo.
set "GO="
set /p "GO=  Digite S para gerar, ou Enter para cancelar: "
if /i not "!GO!"=="S" (
    echo.
    echo   Cancelado. Nada foi gerado.
    echo.
    pause
    exit /b 0
)

REM ---------------------------------------------- 6. Rodar
echo.
echo   Gerando. Pode fechar essa janela a qualquer momento -
echo   ao rodar de novo, ele continua de onde parou.
echo.
python -m src.forge run "!CSVFILE!" --out ".\output" --workers 2

echo.
if exist "output" start "" "output"
echo   Arquivos salvos na pasta output.
echo.
pause
endlocal
