#!/bin/bash

echo "📦 Устанавливаем зависимости..."
pip install -r requirements.txt

echo "🎨 Собираем статику..."
python manage.py collectstatic --noinput

echo "✅ Сборка завершена!"