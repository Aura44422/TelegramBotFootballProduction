#!/usr/bin/env python3
"""
Football Signals Bot - Railway запуск
"""

import asyncio
import os
import sys

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import FootballBot

async def railway_main():
    """Главная функция для Railway"""
    bot = FootballBot()
    
    # Получаем URL из переменных окружения Railway
    railway_url = os.environ.get('RAILWAY_STATIC_URL')
    if not railway_url:
        # Fallback для локальной разработки
        railway_url = 'localhost'
    
    try:
        await bot.initialize()
        
        # Настраиваем webhook URL
        webhook_url = f"https://{railway_url}/webhook"
        print(f"🚀 Запуск бота с webhook URL: {webhook_url}")
        
        # Запускаем webhook
        await bot.application.run_webhook(
            listen="0.0.0.0",
            port=8080,
            webhook_url=webhook_url
        )
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(railway_main()) 