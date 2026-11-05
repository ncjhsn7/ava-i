@echo off
setlocal
title Ancora - inicializacao

rem Coloque este arquivo na pasta raiz do projeto (a que contem "backend" e "frontend").
set "RAIZ=%~dp0"
set "BACK=%RAIZ%backend"
set "FRONT=%RAIZ%frontend"

if not exist "%BACK%\app\main.py" (
  echo [ERRO] Nao encontrei backend\app\main.py. Coloque este .bat na pasta raiz do projeto.
  pause
  exit /b 1
)
if not exist "%FRONT%\package.json" (
  echo [ERRO] Nao encontrei frontend\package.json. Coloque este .bat na pasta raiz do projeto.
  pause
  exit /b 1
)

rem ---------- Backend: cria o ambiente virtual e instala dependencias na primeira vez ----------
if not exist "%BACK%\venv\Scripts\activate.bat" (
  echo Criando ambiente virtual do backend...
  pushd "%BACK%"
  python -m venv venv || (echo [ERRO] Python nao encontrado no PATH. & popd & pause & exit /b 1)
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt || (echo [ERRO] Falha ao instalar dependencias do backend. & popd & pause & exit /b 1)
  popd
)
if not exist "%BACK%\.env" (
  if exist "%BACK%\.env.example" copy "%BACK%\.env.example" "%BACK%\.env" >nul
)

rem ---------- Frontend: instala dependencias na primeira vez ----------
if not exist "%FRONT%\node_modules" (
  echo Instalando dependencias do frontend...
  pushd "%FRONT%"
  call npm install || (echo [ERRO] Falha no npm install. Verifique se o Node.js esta instalado. & popd & pause & exit /b 1)
  popd
)

rem ---------- Sobe os dois servidores, cada um na sua janela ----------
start "Ancora - Backend (porta 8000)" cmd /k "cd /d "%BACK%" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port 8000"
start "Ancora - Frontend (porta 4200)" cmd /k "cd /d "%FRONT%" && npx ng serve"

echo.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:4200
echo Aguardando o frontend compilar para abrir o navegador...
timeout /t 25 /nobreak >nul
start "" http://localhost:4200

echo Para encerrar, feche as janelas "Ancora - Backend" e "Ancora - Frontend".
endlocal
