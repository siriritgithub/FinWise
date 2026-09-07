@echo off
echo Starting FinWise...

:: ── 1. Ollama ────────────────────────────────────────────────────────────────
echo [1/3] Starting Ollama (qwen2.5:7b)...
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %ERRORLEVEL%==0 (
    echo        Ollama already running, skipping.
) else (
    start "Ollama" /MIN "C:\Users\orlot\AppData\Local\Programs\Ollama\ollama.exe" serve
    echo        Ollama started.
)

:: ── 2. Backend ───────────────────────────────────────────────────────────────
echo [2/3] Starting FastAPI backend on port 8000...
start "FinWise Backend" cmd /k "cd /d c:\FinWise\backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

:: ── 3. Frontend ──────────────────────────────────────────────────────────────
echo [3/3] Starting Vite frontend on port 5173...
start "FinWise Frontend" cmd /k "cd /d c:\FinWise\frontend && npm run dev"

echo.
echo FinWise is starting up:
echo   Frontend  : http://localhost:5173
echo   Backend   : http://localhost:8000
echo   API docs  : http://localhost:8000/docs
echo   Ollama    : http://localhost:11434
echo.
echo Close the Backend and Frontend terminal windows to stop the servers.
pause
