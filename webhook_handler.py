import asyncio
import logging
from aiohttp import web
from typing import Dict, Optional
from database import Database
from donation_alerts import DonationAlerts

logger = logging.getLogger(__name__)

class WebhookHandler:
    def __init__(self, database: Database, donation_alerts: DonationAlerts, bot_application):
        self.db = database
        self.donation_alerts = donation_alerts
        self.bot_application = bot_application
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Настройка маршрутов для webhook'ов"""
        # Telegram webhook
        self.app.router.add_post('/webhook', self.handle_telegram_webhook)
        # DonationAlerts webhook
        self.app.router.add_post('/webhook/donation_alerts', self.handle_donation_alerts_webhook)
        # Health check
        self.app.router.add_get('/health', self.health_check)
    
    async def handle_telegram_webhook(self, request):
        """Обработка webhook от Telegram"""
        try:
            # Получаем данные из webhook
            data = await request.json()
            logger.info(f"Получен webhook от Telegram")
            
            # Создаем Update объект
            from telegram import Update
            update = Update.de_json(data, self.bot_application.bot)
            
            # Обрабатываем update через application
            await self.bot_application.process_update(update)
            
            return web.json_response({'status': 'ok'})
            
        except Exception as e:
            logger.error(f"Ошибка обработки Telegram webhook: {e}")
            return web.json_response({'status': 'error'}, status=500)
    
    async def handle_donation_alerts_webhook(self, request):
        """Обработка webhook от DonationAlerts"""
        try:
            # Получаем данные из webhook
            data = await request.json()
            logger.info(f"Получен webhook от DonationAlerts: {data}")
            
            # Обрабатываем платеж
            payment_result = await self.donation_alerts.process_payment_webhook(data)
            
            if payment_result and payment_result['status'] == 'success':
                user_id = payment_result['user_id']
                subscription_type = payment_result['subscription_type']
                amount = payment_result['amount']
                payment_id = payment_result['payment_id']
                
                # Определяем количество дней для подписки
                subscription_days = {
                    'week': 7,
                    'two_weeks': 14,
                    'month': 30
                }
                
                days = subscription_days.get(subscription_type, 7)
                
                # Обновляем подписку пользователя
                await self.db.update_user_subscription(user_id, subscription_type, days)
                
                # Добавляем запись о платеже
                await self.db.add_subscription_record(user_id, subscription_type, amount, payment_id)
                
                # Отправляем уведомление пользователю
                await self.send_payment_success_message(user_id, subscription_type, amount, days)
                
                logger.info(f"Платеж успешно обработан для пользователя {user_id}")
                
                return web.json_response({'status': 'success'})
            
            elif payment_result and payment_result['status'] == 'insufficient_amount':
                logger.warning(f"Недостаточная сумма платежа: {payment_result}")
                return web.json_response({'status': 'insufficient_amount'})
            
            else:
                logger.warning(f"Неуспешный платеж: {payment_result}")
                return web.json_response({'status': 'failed'})
                
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return web.json_response({'status': 'error'}, status=500)
    
    async def send_payment_success_message(self, user_id: int, subscription_type: str, amount: float, days: int):
        """Отправка сообщения об успешной оплате"""
        try:
            subscription_names = {
                'week': 'неделю',
                'two_weeks': 'две недели',
                'month': 'месяц'
            }
            
            subscription_name = subscription_names.get(subscription_type, subscription_type)
            
            message_text = f"""
✅ **Оплата прошла успешно!**

💳 **Подписка активирована:**
📅 Тип: {subscription_name}
💰 Сумма: {amount}₽
⏰ Срок: {days} дней

🎉 **Приятного пользования!**

Теперь вы можете получать до 15 сигналов в день.

💡 Используйте команды:
/status - проверить статус
/help - справка
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Статус подписки", callback_data="status")],
                [InlineKeyboardButton("⚽️ Найти матчи", callback_data="find_matches")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.bot_application.bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об успешной оплате: {e}")
    
    async def health_check(self, request):
        """Проверка здоровья сервиса"""
        return web.json_response({'status': 'healthy'})
    
    async def start_server(self, host: str = '0.0.0.0', port: int = 8080):
        """Запуск webhook сервера"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Webhook сервер запущен на {host}:{port}")
        
        return runner
    
    async def stop_server(self, runner):
        """Остановка webhook сервера"""
        await runner.cleanup()
        logger.info("Webhook сервер остановлен")

# Импорты для inline кнопок
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
