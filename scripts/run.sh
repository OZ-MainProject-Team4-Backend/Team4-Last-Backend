#!/bin/bash
set -e

# 마이그레이션 확인 및 적용
python manage.py makemigrations --check --noinput || echo "No changes"
python manage.py migrate

# Gunicorn 실행
gunicorn settings.wsgi:application --bind 0.0.0.0:8000 --workers 2 --preload --log-level debug

