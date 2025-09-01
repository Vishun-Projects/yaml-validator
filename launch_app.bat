@echo off
echo ========================================
echo   Audit Validator - Enhanced Dashboard
echo ========================================
echo.
echo Starting the application...
echo.

REM Change to project directory
cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Change to audit_validator directory
cd audit_validator

REM Check if streamlit is available
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo ERROR: Streamlit not found in virtual environment
    echo Please install it with: pip install streamlit
    pause
    exit /b 1
)

echo.
echo Starting Streamlit app on localhost:8501...
echo.
echo The app will open in your browser automatically.
echo Press Ctrl+C to stop the app.
echo.

REM Start the app
streamlit run streamlit_app.py --server.port 8502 --server.address localhost

echo.
echo App stopped.
pause
