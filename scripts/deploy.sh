#!/bin/bash
set +e

echo "=== Starting deployment ==="

export DJANGO_SETTINGS_MODULE=settings.production

# ✅ envs/.env.prod 로드 (심볼릭 링크로 env/.env.prod도 가능)
if [ -f ~/Team4-Last-Backend/envs/.env.prod ]; then
    echo "📋 Loading environment variables from envs/.env.prod"
    set -a
    source ~/Team4-Last-Backend/envs/.env.prod
    set +a
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