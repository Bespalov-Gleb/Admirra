@echo off
title Lead Validator Bridge
cls
echo ========================================================
echo        LEAD VALIDATOR SECURE BRIDGE
echo ========================================================
echo.
echo This script will create a temporary public link for your client.
echo DO NOT CLOSE this window while the client is testing.
echo.

echo 1. Cleaning up ports (stopping old processes)...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

echo 2. Starting Backend Server (Production Mode)...
echo    Server will run on http://localhost:8000
start /B python -m lead_validator.standalone > server.log 2>&1

echo    Waiting for server to initialize (5 seconds)...
timeout /t 5 >nul

echo 3. Getting Tunnel Password...
echo    (LocalTunnel requires your IP as a password for security)
for /f "delims=" %%i in ('curl -s https://loca.lt/mytunnelpassword') do set TUNNEL_PASS=%%i

echo.
echo ========================================================
echo   TUNNEL PASSWORD: %TUNNEL_PASS%
echo   (Copy this password!)
echo ========================================================
echo.
echo 4. Establishing Secure Tunnel...
echo.
echo ========================================================
echo   COPY THE URL BELOW AND SEND IT TO THE CLIENT:
echo   (It will look like https://random-name.loca.lt)
echo ========================================================
echo.
echo   NOTE: When opening the link, the client WILL see a 
echo   "Tunnel Password" screen. 
echo   They MUST enter the password shown above: %TUNNEL_PASS%
echo   (Or simply click "Click to Continue" if their IP matches)
echo.
echo   Public URL:
call npx -y localtunnel --port 8000
pause
