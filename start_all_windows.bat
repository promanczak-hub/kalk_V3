@echo off
echo =======================================================
echo Uruchamianie LTR Kalkulator V3
echo =======================================================

echo 1. Uruchamianie Redis (Docker)
docker-compose up -d redis

echo 2. Uruchamianie Backend (FastAPI) w nowym oknie
start "Backend" cmd /c "cd backend && poetry run python run_dev.py"

echo 3. Uruchamianie Celery Worker w nowym oknie
start "Celery Worker" cmd /k "cd backend && poetry run celery -A core.celery_app worker --pool=solo --loglevel=info"

echo 4. Uruchamianie Frontend (Vite)
cd frontend
npm run dev
