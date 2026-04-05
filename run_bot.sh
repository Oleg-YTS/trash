#!/bin/bash
# Скрипт автоперезапуска бота для PythonAnywhere
# Запускай в Bash-консоли: bash run_bot.sh
# Бот будет перезапускаться автоматически если упадёт

LOG_FILE="$HOME/trash-diet/bot.log"
cd "$HOME/trash-diet" || exit 1

echo "🍔 Трэш-диетолог: запускаю..."
echo "📝 Логи пишутся в $LOG_FILE"

while true; do
    echo "[$(date)] 🚀 Запуск бота..." >> "$LOG_FILE"
    python3.11 fridge_bot.py >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    echo "[$(date)] 💥 Бот упал с кодом $EXIT_CODE. Перезапуск через 10 секунд..." >> "$LOG_FILE"
    sleep 10
done
