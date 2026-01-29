@echo off
echo ========================================
echo Система аналитики Ozon
echo ========================================
echo.
echo Проверка зависимостей...
python -c "import flask, pandas, openpyxl" 2>nul
if errorlevel 1 (
    echo Установка зависимостей...
    pip install -r requirements.txt
)
echo.
echo Запуск сервера...
echo Откройте в браузере: http://localhost:5000
echo.
python app.py
pause
