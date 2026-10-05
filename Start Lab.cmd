@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
    echo Install Docker Desktop first: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
docker compose version >nul 2>nul
if errorlevel 1 (
    echo Docker Compose is required. Update Docker Desktop and try again.
    pause
    exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
    echo Open Docker Desktop, wait until it is ready, then open Start Lab again.
    pause
    exit /b 1
)
echo Preparing PDF Analyzer. The first start downloads the lab tools.
docker compose up -d --build --wait --wait-timeout 180
if errorlevel 1 (
    echo The lab could not start. Check Docker Desktop for errors or an occupied port.
    pause
    exit /b 1
)
if not defined LAB_PORT set "LAB_PORT=8080"
start "" "http://localhost:%LAB_PORT%"
echo PDF Analyzer is ready. Import your dataset through Lab setup in the web app.
