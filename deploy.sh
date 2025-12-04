#!/bin/bash

# Скрипт развертывания Trading Game Bot

set -e

echo "🚀 Начало развертывания Trading Game Bot..."

# Проверка переменных окружения
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: BOT_TOKEN не установлен"
    exit 1
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data logs charts

# Проверка Python
echo "🐍 Проверка версии Python..."
python3 --version

# Установка зависимостей
echo "📦 Установка зависимостей..."
pip3 install -r requirements.txt

# Инициализация базы данных
echo "🗄️ Инициализация базы данных..."
python3 -c "from database import init_db; init_db()"

# Создание service файла для systemd
echo "🔧 Создание systemd service..."
cat > /etc/systemd/system/trading-bot.service << EOF
[Unit]
Description=Telegram Trading Game Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="BOT_TOKEN=$BOT_TOKEN"
Environment="ADMIN_IDS=$ADMIN_IDS"
ExecStart=/usr/bin/python3 $(pwd)/bot.py
Restart=always
RestartSec=10
StandardOutput=append:$(pwd)/logs/bot.log
StandardError=append:$(pwd)/logs/bot_error.log

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd и запуск сервиса
echo "⚡ Запуск сервиса..."
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

echo "✅ Развертывание завершено!"
echo ""
echo "📊 Полезные команды:"
echo "• Просмотр логов: sudo journalctl -u trading-bot -f"
echo "• Перезапуск бота: sudo systemctl restart trading-bot"
echo "• Статус бота: sudo systemctl status trading-bot"
echo ""
echo "🎮 Бот запущен! Используйте /start в Telegram"
