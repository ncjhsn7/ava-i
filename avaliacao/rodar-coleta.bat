@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1
set PY=..\backend\venv\Scripts\python.exe
if not exist "%PY%" (echo [ERRO] Nao achei o Python do backend. Rode o iniciar-ancora.bat uma vez antes. & pause & exit /b 1)

echo ===== Passo 0: checando o ambiente =====
"%PY%" 0_checar_ambiente.py || goto parar
echo.
echo ===== Passo 1: sorteio dos fragmentos e temas =====
"%PY%" 1_sortear_fragmentos.py || goto parar
echo.
echo ===== Passo 2: geracao das questoes =====
"%PY%" 2_gerar_questoes.py || goto parar
echo.
echo ===== Passo 3: julgamento pelo Opus =====
"%PY%" 3_julgar.py || goto parar
echo.
echo ===== Passo 4: amostra para avaliacao humana =====
"%PY%" 4_amostra_humana.py
echo.
echo ===== Passo 5: analise =====
"%PY%" 5_analisar.py
echo.
echo Coleta concluida. Tabelas em avaliacao\resultados\tabelas.tex
pause
exit /b 0

:parar
echo.
echo A coleta parou antes do fim (limite de uso ou erro acima).
echo Rode este .bat de novo mais tarde: ele continua de onde parou, sem refazer nada.
pause
exit /b 1
