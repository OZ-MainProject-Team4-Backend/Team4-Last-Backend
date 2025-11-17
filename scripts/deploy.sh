#!/bin/bash
set +e

echo "=== Starting deployment ==="

export DJANGO_SETTINGS_MODULE=settings.production

# 환경변수 로드
if [ -f ~/Team4-Last-Backend/envs/.env.prod ]; then
    echo "📋 Loading environment variables from envs/.env.prod"
    set -a
    source ~/Team4-Last-Backend/envs/.env.prod
    set +a

    # ✅ 디버깅: 주요 환경변수 확인
    echo "DEBUG: POSTGRES_HOST=$POSTGRES_HOST"
    echo "DEBUG: POSTGRES_USER=$POSTGRES_USER"
    echo "DEBUG: POSTGRES_DB=$POSTGRES_DB"
    echo "DEBUG: OPENAI_API_KEY=${OPENAI_API_KEY:0:20}..."
else
    echo "❌ envs/.env.prod not found!"
    exit 1
fi

echo "🔴 Stopping gunicorn..."
pkill -f gunicorn
sleep 3

set -e

echo "🔄 Activating virtualenv..."
source ~/.pyenv/versions/aws/bin/activate

echo "🗄️ Running migrations..."
python manage.py migrate

echo "🚀 Starting gunicorn..."
gunicorn settings.wsgi:application --bind 0.0.0.0:8000 --workers 3 --daemon
sleep 3

echo "✅ Checking if gunicorn is running..."
if pgrep -f gunicorn > /dev/null; then
    echo "✅ Gunicorn is running!"
    ps aux | grep gunicorn | grep -v grep
else
    echo "❌ Gunicorn not running"
    exit 1
fi

echo "✅ Deployment completed successfully!"