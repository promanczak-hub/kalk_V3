@echo off
echo Uruchamiam GŁÓWNEGO workera Celery (z wymuszeniem --pool=solo dla Windowsa)
poetry run celery -A worker worker -Q celery --pool=solo --loglevel=info
pause
