#!/bin/sh
# Container start-up for the Laravel app.
set -e

if [ -z "$APP_KEY" ]; then
  echo "APP_KEY is empty. Make sure Laravel/phishing-frontend/.env exists and has an APP_KEY." >&2
  exit 1
fi

# SQLite file lives in the mounted database folder, so data survives restarts.
if [ "${DB_CONNECTION:-sqlite}" = "sqlite" ]; then
  touch "${DB_DATABASE:-database/database.sqlite}"
fi

php artisan package:discover --ansi >/dev/null
php artisan migrate --force
php artisan config:clear >/dev/null
php artisan view:clear >/dev/null

exec php artisan serve --host=0.0.0.0 --port=8001
