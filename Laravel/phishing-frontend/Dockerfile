# PanshengGuard web app (Laravel) — same app, same port (8001).
FROM php:8.3-cli

RUN apt-get update \
 && apt-get install -y --no-install-recommends unzip git libsqlite3-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# PHP dependencies first, for faster rebuilds.
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --no-scripts --no-autoloader --prefer-dist

COPY . .
RUN composer dump-autoload --optimize --no-dev \
 && mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs bootstrap/cache \
 && chmod +x docker/entrypoint.sh

ENV PHP_CLI_SERVER_WORKERS=4
EXPOSE 8001
ENTRYPOINT ["docker/entrypoint.sh"]
