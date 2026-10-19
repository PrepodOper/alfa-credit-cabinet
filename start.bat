@echo off
chcp 65001 >nul
setlocal

rem Запуск приложения одним процессом: FastAPI раздаёт собранный фронтенд из frontend\dist.
rem Использование: start.bat [порт]

cd /d "%~dp0"
if "%~1"=="" (set PORT=8000) else (set PORT=%~1)

where python >nul 2>nul
if errorlevel 1 (
  echo [X] Python не найден. Установите Python 3.11+ с https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist backend\.venv (
  echo [1/4] Создаю виртуальное окружение backend\.venv...
  python -m venv backend\.venv
  if errorlevel 1 ( echo [X] Не удалось создать окружение & pause & exit /b 1 )
)

echo [2/4] Устанавливаю зависимости...
call backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
call backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
if errorlevel 1 ( echo [X] Ошибка установки зависимостей & pause & exit /b 1 )

if not exist frontend\dist\index.html (
  echo [!] Собранный фронтенд не найден: frontend\dist
  echo     Соберите его: cd frontend ^&^& npm install ^&^& npm run build
  echo     Или используйте Docker: docker compose up --build
  pause
  exit /b 1
)

if not exist backend\data mkdir backend\data

echo.
echo   [3/4] Приложение:  http://localhost:%PORT%
echo         API/Swagger: http://localhost:%PORT%/docs
echo         Логин:       ivan@vesna.ru / demo1234
echo   [4/4] Остановить — Ctrl+C
echo.

cd backend
set STATIC_DIR=../frontend/dist
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
