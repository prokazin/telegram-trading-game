#!/bin/bash

# CRON задания для Trading Game Bot

# Обновление данных каждые 5 минут
*/5 * * * * cd /path/to/telegram-trading-game && /usr/bin/python3 update_data.py >> logs/cron.log 2>&1

# Ежедневная очистка в 3:00
0 3 * * * cd /path/to/telegram-trading-game && /usr/bin/python3 update_data.py --cleanup >> logs/cron.log 2>&1

# Еженедельное резервное копирование в воскресенье в 2:00
0 2 * * 0 cd /path/to/telegram-trading-game && /usr/bin/python3 update_data.py --backup >> logs/cron.log 2>&1
