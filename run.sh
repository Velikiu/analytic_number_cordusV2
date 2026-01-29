#!/bin/bash

echo "========================================"
echo "Система аналитики Ozon"
echo "========================================"
echo ""
echo "Проверка зависимостей..."

python3 -c "import flask, pandas, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Установка зависимостей..."
    pip3 install -r requirements.txt
fi

echo ""
echo "Запуск сервера..."
echo "Откройте в браузере: http://localhost:5000"
echo ""

python3 app.py
