#!/bin/bash
set +e

echo "=== Starting deployment ==="
cd ~/Team4-Last-Backend || { echo "❌ Directory not found"; exit 1; }

echo "📦 Pulling latest code..."
git pull origin main || { echo "❌ Git pull failed"; exit 1; }

export DJANGO_SETTINGS_MODULE=settings.production

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