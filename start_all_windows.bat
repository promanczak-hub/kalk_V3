@echo off
echo =======================================================
echo Uruchamianie LTR Kalkulator V3
echo =======================================================

echo 1. Uruchamianie Redis (Docker)
docker-compose up -d redis

echo 2. Uruchamianie Backend (FastAPI) w nowym oknie
start "Backend" cmd /c "cd backend && poetry run uvicorn main:app --reload"

echo 3. Uruchamianie Celery Worker (Docker)
docker-compose up -d celery_worker --build

echo 4. Uruchamianie Frontend (Vite)
cd frontend
npm run dev
