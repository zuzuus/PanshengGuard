# PanshengGuard — Setup & Running Guide

GitHub Repository: https://github.com/zuzuus/PanshengGuard

There are **two ways to run the project**:
- **Method 1:** Run locally using Python and Laravel.
- **Method 2:** Run using Docker and Cloudflare Tunnel to generate a public link.

## REQUIREMENTS

Install these first:
- Git: https://git-scm.com/
- Python
- PHP and Composer
- Node.js and npm, if required by the frontend
- Docker Desktop (for Method 2)

## STEP 1 — DOWNLOAD THE PROJECT

Open PowerShell or your terminal:

```bash
git clone https://github.com/zuzuus/PanshengGuard.git
cd PanshengGuard
```

## STEP 2 — CONFIGURE THE LARAVEL ENVIRONMENT

Go into the Laravel project directory:

```bash
cd Laravel/phishing-frontend
```

Create your own `.env` file by copying `.env.example`:

```powershell
Copy-Item .env.example .env
```

**Important:** If `.env` already exists, don't overwrite it.

Generate a new Laravel application key:

```bash
php artisan key:generate
```

This generates the `APP_KEY` required by Laravel. Each team member should generate their own key rather than sharing yours.

If the project requires additional environment variables, configure them according to `.env.example`.

Return to the root project directory when finished:

```powershell
cd ../..
```

## METHOD 1 — RUN LOCALLY (WITHOUT DOCKER)

### Terminal 1 — Start the FastAPI backend

From the `Piton` directory:

```bash
python -m venv .venv
```

Activate the virtual environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the Python dependencies using the project's `requirements.txt`:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
python -m uvicorn main:app --reload --port 8000
```

Keep this terminal running.

### Terminal 2 — Start the Laravel frontend

From the `Laravel/phishing-frontend` directory, install PHP dependencies if necessary:

```bash
composer install
```

Clear the cached views:

```bash
php artisan view:clear
```

Start Laravel:

```bash
php artisan serve --port=8001
```

Open the website:

http://127.0.0.1:8001

After changing Blade, CSS, or JavaScript files, refresh the browser using `Ctrl + F5`.

## METHOD 2 — RUN USING DOCKER + CLOUDFLARE

This method runs the configured application services in Docker and uses Cloudflare Tunnel to provide a public URL.

### 1. Install Docker Desktop

Download it here:

https://www.docker.com/products/docker-desktop/

Open Docker Desktop and wait until the Docker Engine is running.

If Windows reports that virtualization features are disabled, enable the required Windows features and restart your computer as instructed by Docker.

### 2. Configure environment files

Make sure the required environment files exist:

- `Laravel/phishing-frontend/.env` — must contain a valid `APP_KEY`.
- `Piton/.env` — optional if VirusTotal integration is not being used; configure `VIRUSTOTAL_API_KEY` if required.

For the Laravel key, follow the setup in Step 2 above.

### 3. Start Docker

Return to the project root directory and run:

```powershell
docker compose up -d --build
```

Alternatively, if the project's startup script is available:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker-start.ps1
```

The first build may take several minutes.

Check the containers:

```powershell
docker compose ps
```

Local website:

http://127.0.0.1:8001

The startup script may also display a public Cloudflare URL ending in `.trycloudflare.com`.

**Note:** The public URL can change when the tunnel restarts. To find the current URL, check:

```powershell
docker compose logs cloudflared
```

### Useful Docker commands

```powershell
docker compose up -d --build
docker compose down
docker compose ps
docker compose logs web
docker compose logs piton
docker compose logs cloudflared
docker compose restart piton
```

- After editing application code, rebuild or restart the relevant services as needed.
- After retraining the model, rebuild the `piton` service if the updated model files need to be copied into the Docker image.
- Stop local Uvicorn and Laravel servers before starting Docker if they are already using ports 8000 and 8001.

## CHROME EXTENSION SETUP

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Click **Load unpacked** and select the project's `extension` folder.
4. Open the website at `http://127.0.0.1:8001/profile`.
5. Generate and copy the extension token.
6. Click the PanshengGuard extension icon.
7. Open Connection Settings, paste the token, and save.
8. Click Test Connection and confirm that it reports a successful connection.
9. Reload the extension and refresh the Gmail tab if necessary.

The extension is configured to connect to the local Laravel frontend. Public access through Cloudflare may require additional configuration.

