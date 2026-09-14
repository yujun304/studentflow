@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
set "DOCKER_CONFIG=%~dp0.data\docker-config"
set "DOCKER_DESKTOP=C:\Program Files\Docker\Docker\Docker Desktop.exe"
set "APP_URL=http://localhost:8081"
set "HEALTH_URL=%APP_URL%/api/v1/health"

if not exist "%DOCKER_CONFIG%" mkdir "%DOCKER_CONFIG%"

echo [StudentFlow] Checking Docker engine...
docker info >nul 2>&1
if errorlevel 1 (
    if not exist "%DOCKER_DESKTOP%" (
        echo [ERROR] Docker Desktop was not found.
        echo Install Docker Desktop or start it manually, then run this file again.
        pause
        exit /b 1
    )

    echo [StudentFlow] Starting Docker Desktop...
    start "" "%DOCKER_DESKTOP%"

    set /a WAIT_COUNT=0
    :wait_for_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    set /a WAIT_COUNT+=1
    if !WAIT_COUNT! LSS 40 goto wait_for_docker

    echo [ERROR] Docker engine did not become ready within 2 minutes.
    echo Check Docker Desktop, then run this file again.
    pause
    exit /b 1
)

:docker_ready
echo [StudentFlow] Building and starting the server...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] Docker Compose failed to start StudentFlow.
    pause
    exit /b 1
)

echo [StudentFlow] Waiting for the API health check...
set /a HEALTH_COUNT=0
:wait_for_health
curl.exe -fsS "%HEALTH_URL%" >nul 2>&1
if not errorlevel 1 goto server_ready
timeout /t 3 /nobreak >nul
set /a HEALTH_COUNT+=1
if %HEALTH_COUNT% LSS 40 goto wait_for_health

echo [WARNING] Containers started, but the API health check did not pass within 2 minutes.
docker compose ps
pause
exit /b 1

:server_ready
echo.
echo [StudentFlow] Server is ready: %APP_URL%
docker compose ps
start "" "%APP_URL%"
echo.
echo You can close this window. The server will keep running in Docker.
pause
exit /b 0
