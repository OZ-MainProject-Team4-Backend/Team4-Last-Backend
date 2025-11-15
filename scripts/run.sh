#!/bin/bash
export DJANGO_SETTINGS_MODULE=settings.production
set -e

until nc -z last-AWS-db 5432; do
  echo "Waiting for Postgres..."
  sleep 1
done
echo "Postgres is up!"

until nc -z redis 6379; do
  echo "Waiting for Redis..."
  sleep 1
done
echo "Redis is up!"

# 마이그레이션 확인 및 적용
python manage.py makemigrations --check --noinput || echo "No changes"
python manage.py migrate

# Gunicorn 실행
gunicorn settings.wsgi:application --bind 0.0.0.0:8000 --workers 3

