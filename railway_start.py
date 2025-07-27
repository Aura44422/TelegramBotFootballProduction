#!/usr/bin/env python3
"""
Football Signals Bot - Railway запуск
"""

import asyncio
import os
import sys
import logging
import signal

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import FootballBot

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RailwayBot:
    def __init__(self):
        self.bot = FootballBot()
        self.running = False
    
    async def start(self):
        """Запуск бота для Railway"""
        try:
            self.running = True
            
            # Инициализируем бота
            await self.bot.initialize()
            
            # Получаем URL из переменных окружения Railway
            railway_url = os.environ.get('RAILWAY_STATIC_URL')
            if not railway_url:
                logger.error("RAILWAY_STATIC_URL не установлен")
                return
            
            # Настраиваем webhook URL
            webhook_url = f"https://{railway_url}/webhook"
            logger.info(f"🚀 Запуск бота с webhook URL: {webhook_url}")
            
            # Устанавливаем webhook URL для Telegram
            await self.bot.application.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook URL установлен: {webhook_url}")
            
            # Настраиваем обработчики сигналов
            def signal_handler(signum, frame):
                logger.info(f"Получен сигнал {signum}, завершаем работу...")
                self.running = False
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            logger.info("Бот запущен и готов к работе")
            
            # Держим приложение запущенным
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка бота"""
        try:
            logger.info("Останавливаем бота...")
            await self.bot.shutdown()
            logger.info("Бот успешно остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")

async def main():
    """Главная функция"""
    railway_bot = RailwayBot()
    await railway_bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 
