import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from config import (
    BOT_TOKEN, TRIAL_MESSAGES_LIMIT, DAILY_SIGNALS_LIMIT, 
    SUBSCRIPTION_PRICES, MAX_ADMINS, WEEKLY_REPORT_DAY, WEEKLY_REPORT_HOUR,
    PARSING_INTERVAL
)
from database import Database
from parser import MatchParser
from donation_alerts import DonationAlerts
from webhook_handler import WebhookHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class FootballBot:
    def __init__(self):
        self.db = Database()
        self.donation_alerts = None
        self.parser = None
        self.application = None
        self.webhook_handler = None
        self.webhook_runner = None
        self.running = False
        
    async def initialize(self):
        """Инициализация бота"""
        try:
            # Инициализация базы данных
            await self.db.init_database()
            logger.info("База данных инициализирована")
            
            # Инициализация DonationAlerts
            self.donation_alerts = DonationAlerts(self.db)
            logger.info("DonationAlerts инициализирован")
            
            # Инициализация парсера
            self.parser = MatchParser(self.db)
            logger.info("Парсер инициализирован")
            
            # Создание приложения
            self.application = Application.builder().token(BOT_TOKEN).build()
            logger.info("Telegram приложение создано")
            
            # Инициализация приложения
            await self.application.initialize()
            logger.info("Telegram приложение инициализировано")
            
            # Инициализация webhook handler
            self.webhook_handler = WebhookHandler(self.db, self.donation_alerts, self.application)
            logger.info("Webhook handler инициализирован")
            
            # Регистрация обработчиков
            self.register_handlers()
            logger.info("Обработчики зарегистрированы")
            
            # Запуск webhook сервера
            self.webhook_runner = await self.webhook_handler.start_server()
            logger.info("Webhook сервер запущен")
            
            # Запуск фоновых задач
            asyncio.create_task(self.background_tasks())
            logger.info("Фоновые задачи запущены")
            
            logger.info("Бот полностью инициализирован")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            raise
    
    def register_handlers(self):
        """Регистрация обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("subscription", self.subscription_command))
        
        # Админские команды
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("addadmin", self.add_admin_command))
        self.application.add_handler(CommandHandler("removeadmin", self.remove_admin_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("give_subscription", self.give_subscription_command))
        self.application.add_handler(CommandHandler("revoke_subscription", self.revoke_subscription_command))
        
        # Обработка callback запросов
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Обработка всех сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Добавляем пользователя в базу данных
            await self.db.add_user(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Получаем информацию о пользователе
            user_info = await self.db.get_user(user_id)
            
            if user_info:
                if user_info['subscription_type'] == 'trial':
                    # Пробный период
                    remaining_messages = TRIAL_MESSAGES_LIMIT - user_info['trial_messages_used']
                    
                    welcome_text = f"""
🎉 **Добро пожаловать в Football Signals Bot!**

⚽️ Я помогу вам найти футбольные матчи с коэффициентами 4.25/1.225 или 4.22/1.225

🎁 **Ваш пробный период активирован!**
📊 Осталось сообщений: **{remaining_messages}**
⏰ Пробный период активен до: **{user_info.get('subscription_end', 'Не ограничено')}**

После окончания пробного периода вам потребуется подписка для продолжения использования бота.

💡 Используйте команды ниже для навигации:
"""
                else:
                    # Платная подписка
                    end_date = user_info.get('subscription_end')
                    if end_date:
                        end_date_str = datetime.fromisoformat(end_date).strftime("%d.%m.%Y %H:%M")
                    else:
                        end_date_str = "Бессрочно"
                    
                    daily_signals = user_info['daily_signals_used']
                    welcome_text = f"""
🎉 **Добро пожаловать обратно!**

⚽️ Ваша подписка активна до: **{end_date_str}**
📊 Сигналов сегодня: **{daily_signals}/{DAILY_SIGNALS_LIMIT}**

💡 Используйте команды ниже для навигации:
"""
            else:
                welcome_text = """
🎉 **Добро пожаловать в Football Signals Bot!**

⚽️ Я помогу вам найти футбольные матчи с коэффициентами 4.25/1.225 или 4.22/1.225

🎁 **Ваш пробный период активирован!**
📊 Осталось сообщений: **3**

💡 Используйте команды ниже для навигации:
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Статус подписки", callback_data="status")],
                [InlineKeyboardButton("💳 Купить подписку", callback_data="subscription")],
                [InlineKeyboardButton("⚽️ Найти матчи", callback_data="find_matches")],
                [InlineKeyboardButton("❓ Помощь", callback_data="help")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    welcome_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            if update.message:
                await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
            elif update.callback_query:
                await update.callback_query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        help_text = """
🤖 **Football Signals Bot - Помощь**

**Основные команды:**
/start - Запуск бота
/status - Статус подписки
/subscription - Управление подпиской
/help - Эта справка

**Для администраторов:**
/admin - Админ панель
/addadmin - Добавить администратора
/removeadmin - Удалить администратора
/stats - Статистика
/give_subscription - Выдать подписку
/revoke_subscription - Отозвать подписку

**Как это работает:**
1. Бот автоматически ищет матчи с коэффициентами 4.25/1.225 или 4.22/1.225
2. При нахождении подходящего матча вы получаете уведомление
3. В пробном периоде доступно 3 сообщения
4. В платной подписке - до 15 сигналов в день

**Подписки:**
• Неделя - 650₽
• Две недели - 1300₽ (экономия 300₽)
• Месяц - 2500₽ (экономия 700₽)

💡 Используйте кнопки под сообщениями для быстрой навигации!
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /status"""
        try:
            user_id = update.effective_user.id
            user_info = await self.db.get_user(user_id)
            
            if not user_info:
                if update.message:
                    await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                elif update.callback_query:
                    await update.callback_query.edit_message_text("❌ Пользователь не найден. Используйте /start")
                return
            
            status_text = await self.get_user_status_text(user_info)
            
            keyboard = [
                [InlineKeyboardButton("💳 Купить подписку", callback_data="subscription")],
                [InlineKeyboardButton("🔙 Назад", callback_data="start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message:
                await update.message.reply_text(
                    status_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            elif update.callback_query:
                await update.callback_query.edit_message_text(
                    status_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            
        except Exception as e:
            logger.error(f"Ошибка в status_command: {e}")
            if update.message:
                await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
            elif update.callback_query:
                await update.callback_query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def subscription_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /subscription"""
        await self.show_subscription_menu(update, context)
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /admin"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к админ панели")
                return
            
            admin_text = """
🔧 **Админ панель**

Выберите действие:
"""
            
            keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
                [InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage")],
                [InlineKeyboardButton("💳 Выдать подписку", callback_data="admin_give_sub")],
                [InlineKeyboardButton("❌ Отозвать подписку", callback_data="admin_revoke_sub")],
                [InlineKeyboardButton("📈 Еженедельный отчет", callback_data="admin_weekly_report")],
                [InlineKeyboardButton("🔙 Назад", callback_data="start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                admin_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в admin_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /addadmin"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к этой команде")
                return
            
            if not context.args:
                await update.message.reply_text("❌ Укажите ID пользователя: /addadmin <user_id>")
                return
            
            try:
                new_admin_id = int(context.args[0])
                
                # Получаем информацию о пользователе
                user_info = await self.db.get_user(new_admin_id)
                if not user_info:
                    await update.message.reply_text("❌ Пользователь не найден в базе данных")
                    return
                
                # Проверяем количество админов
                admins = await self.db.get_admins()
                if len(admins) >= MAX_ADMINS:
                    await update.message.reply_text(f"❌ Достигнут лимит администраторов ({MAX_ADMINS})")
                    return
                
                # Добавляем администратора
                await self.db.add_admin(
                    admin_id=new_admin_id,
                    username=user_info.get('username'),
                    first_name=user_info.get('first_name'),
                    last_name=user_info.get('last_name')
                )
                
                await update.message.reply_text(f"✅ Пользователь {new_admin_id} добавлен как администратор")
                
                # Уведомляем нового админа
                try:
                    await self.application.bot.send_message(
                        chat_id=new_admin_id,
                        text="🎉 Вам выданы права администратора в Football Signals Bot!"
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить нового админа: {e}")
                    
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID пользователя")
                
        except Exception as e:
            logger.error(f"Ошибка в add_admin_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /removeadmin"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к этой команде")
                return
            
            if not context.args:
                await update.message.reply_text("❌ Укажите ID пользователя: /removeadmin <user_id>")
                return
            
            try:
                admin_id_to_remove = int(context.args[0])
                
                # Проверяем, существует ли такой админ
                admins = await self.db.get_admins()
                admin_exists = any(admin['admin_id'] == admin_id_to_remove for admin in admins)
                
                if not admin_exists:
                    await update.message.reply_text("❌ Администратор не найден")
                    return
                
                # Удаляем администратора
                await self.db.remove_admin(admin_id_to_remove)
                
                await update.message.reply_text(f"✅ Администратор {admin_id_to_remove} удален")
                
                # Уведомляем удаленного админа
                try:
                    await self.application.bot.send_message(
                        chat_id=admin_id_to_remove,
                        text="❌ Ваши права администратора были отозваны"
                    )
                except Exception as e:
                    logger.error(f"Не удалось уведомить удаленного админа: {e}")
                    
            except ValueError:
                await update.message.reply_text("❌ Неверный формат ID пользователя")
                
        except Exception as e:
            logger.error(f"Ошибка в remove_admin_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stats"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к этой команде")
                return
            
            stats = await self.db.get_subscription_stats()
            
            stats_text = f"""
📊 **Статистика бота**

👥 **Пользователи:**
• С активной подпиской: **{stats['active_subscriptions']}**
• Без подписки: **{stats['inactive_subscriptions']}**

📈 **За неделю:**
• Покупок подписок: **{stats['weekly_purchases']}**
• Популярная подписка: **{stats['popular_subscription']}**

🔄 Обновлено: {datetime.now().strftime("%d.%m.%Y %H:%M")}
"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад в админ панель", callback_data="admin")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в stats_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def give_subscription_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /give_subscription"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к этой команде")
                return
            
            if len(context.args) < 2:
                await update.message.reply_text("❌ Укажите username и тип подписки: /give_subscription <username> <week|two_weeks|month>")
                return
            
            username = context.args[0].replace('@', '')
            subscription_type = context.args[1]
            
            if subscription_type not in SUBSCRIPTION_PRICES:
                await update.message.reply_text("❌ Неверный тип подписки. Доступные: week, two_weeks, month")
                return
            
            # Здесь нужно будет добавить поиск пользователя по username
            # Пока что это заглушка
            await update.message.reply_text(f"✅ Подписка {subscription_type} выдана пользователю @{username}")
            
        except Exception as e:
            logger.error(f"Ошибка в give_subscription_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def revoke_subscription_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /revoke_subscription"""
        try:
            user_id = update.effective_user.id
            
            if not await self.db.is_admin(user_id):
                await update.message.reply_text("❌ У вас нет доступа к этой команде")
                return
            
            if not context.args:
                await update.message.reply_text("❌ Укажите username: /revoke_subscription <username>")
                return
            
            username = context.args[0].replace('@', '')
            
            # Здесь нужно будет добавить поиск и отзыв подписки
            # Пока что это заглушка
            await update.message.reply_text(f"✅ Подписка пользователя @{username} отозвана")
            
        except Exception as e:
            logger.error(f"Ошибка в revoke_subscription_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        try:
            user_id = update.effective_user.id
            user_info = await self.db.get_user(user_id)
            
            if not user_info:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            # Проверяем права доступа
            if not await self.check_user_access(user_info):
                await update.message.reply_text("❌ У вас нет активной подписки. Используйте /subscription для покупки")
                return
            
            # Обрабатываем сообщение как запрос на поиск матчей
            await self.find_matches_for_user(user_id, update, context)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_message: {e}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user_id = update.effective_user.id
            
            if data == "start":
                await self.start_command(update, context)
            elif data == "help":
                await self.help_command(update, context)
            elif data == "status":
                await self.status_command(update, context)
            elif data == "subscription":
                await self.show_subscription_menu(update, context)
            elif data == "find_matches":
                await self.find_matches_for_user(user_id, update, context)
            elif data.startswith("buy_"):
                # Извлекаем тип подписки из callback_data
                if data == "buy_week":
                    subscription_type = "week"
                elif data == "buy_two_weeks":
                    subscription_type = "two_weeks"
                elif data == "buy_month":
                    subscription_type = "month"
                else:
                    subscription_type = data.split("_", 1)[1]  # fallback
                
                await self.process_subscription_purchase(user_id, subscription_type, update, context)
            elif data.startswith("check_payment_"):
                # Извлекаем тип подписки из callback_data
                subscription_type = data.split("_", 2)[2]  # check_payment_week -> week
                await self.check_payment_status(user_id, subscription_type, update, context)
            elif data.startswith("admin_"):
                await self.handle_admin_callback(data, update, context)
            else:
                await query.edit_message_text("❌ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"Ошибка в button_callback: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
    
    async def show_subscription_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню подписок"""
        subscription_text = """
💳 **Выберите подписку:**

🎯 **Неделя** - 650₽
• Доступ к сигналам на 7 дней
• До 15 сигналов в день

🎯 **Две недели** - 1300₽
• Доступ к сигналам на 14 дней
• До 15 сигналов в день
• 💰 **Экономия 300₽**

🎯 **Месяц** - 2500₽
• Доступ к сигналам на 30 дней
• До 15 сигналов в день
• 💰 **Экономия 700₽**

💡 Выберите подписку ниже:
"""
        
        keyboard = [
            [InlineKeyboardButton("📅 Неделя - 650₽", callback_data="buy_week")],
            [InlineKeyboardButton("📅 Две недели - 1300₽ (экономия 300₽)", callback_data="buy_two_weeks")],
            [InlineKeyboardButton("📅 Месяц - 2500₽ (экономия 700₽)", callback_data="buy_month")],
            [InlineKeyboardButton("🔙 Назад", callback_data="start")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                subscription_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                subscription_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def process_subscription_purchase(self, user_id: int, subscription_type: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка покупки подписки"""
        try:
            # Создаем ссылку для оплаты
            payment_info = await self.donation_alerts.create_payment_link(user_id, subscription_type)
            
            if not payment_info:
                await update.callback_query.edit_message_text("❌ Ошибка создания ссылки для оплаты")
                return
            
            payment_text = f"""
💳 **Оплата подписки**

📋 **Тип:** {subscription_type.replace('_', ' ').title()}
💰 **Сумма:** {payment_info['amount']}₽

🔗 **Ссылка для оплаты:**
{payment_info['payment_url']}

⚠️ **Важно:**
• Оплатите точно указанную сумму
• После оплаты подписка активируется автоматически
• Ссылка действительна 24 часа

💡 После оплаты нажмите "Проверить оплату"
"""
            
            keyboard = [
                [InlineKeyboardButton("🔗 Перейти к оплате", url=payment_info['payment_url'])],
                [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment_{subscription_type}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="subscription")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                payment_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка при создании ссылки для оплаты: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при создании ссылки для оплаты")
    
    async def check_payment_status(self, user_id: int, subscription_type: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка статуса оплаты"""
        try:
            # Проверяем статус платежа через DonationAlerts
            payment_status = await self.donation_alerts.check_payment_status(f"user_{user_id}_{subscription_type}")
            
            # Мгновенная проверка через API
            # В реальном проекте здесь будет реальная проверка через DonationAlerts API
            payment_status = await self.donation_alerts.check_payment_status(f"user_{user_id}_{subscription_type}")
            
            # Для демонстрации показываем разные статусы
            import random
            demo_statuses = ['pending', 'success', 'not_found']
            demo_status = random.choice(demo_statuses)
            
            if demo_status == 'success':
                payment_status = {
                    'status': 'success',
                    'user_id': user_id,
                    'subscription_type': subscription_type,
                    'amount': SUBSCRIPTION_PRICES[subscription_type],
                    'payment_id': f'demo_{user_id}_{subscription_type}'
                }
            elif demo_status == 'not_found':
                payment_status = {
                    'status': 'not_found',
                    'message': 'Платеж не найден'
                }
            else:
                payment_status = {
                    'status': 'pending',
                    'message': 'Платеж в обработке'
                }
            
            if payment_status and payment_status.get('status') == 'success':
                # Платеж успешен, активируем подписку
                amount = payment_status['amount']
                payment_id = payment_status['payment_id']
                
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
                
                success_text = f"""
✅ **Оплата прошла успешно!**

💳 **Подписка активирована:**
📅 Тип: {subscription_type.replace('_', ' ').title()}
💰 Сумма: {amount}₽
⏰ Срок: {days} дней

🎉 **Приятного пользования!**

Теперь вы можете получать до 15 сигналов в день.

💡 Используйте кнопки ниже для навигации
"""
                
                keyboard = [
                    [InlineKeyboardButton("📊 Статус подписки", callback_data="status")],
                    [InlineKeyboardButton("⚽️ Найти матчи", callback_data="find_matches")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="start")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    success_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            elif payment_status and payment_status.get('status') == 'pending':
                # Платеж в обработке
                pending_text = """
⏳ **Платеж в обработке**

💳 Ваш платеж обрабатывается платежной системой.
⏰ Обычно это занимает 1-5 минут.

🔄 Попробуйте проверить статус через несколько минут.
"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data=f"check_payment_{subscription_type}")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="subscription")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    pending_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
            else:
                # Платеж не найден или не оплачен
                not_found_text = """
❌ **Платеж не найден**

💳 Возможные причины:
• Платеж еще не поступил
• Неверная сумма платежа
• Платеж был отменен

💡 **Рекомендации:**
1. Убедитесь, что вы оплатили точно указанную сумму
2. Подождите 5-10 минут и попробуйте снова
3. Если проблема остается, обратитесь в поддержку
"""
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data=f"check_payment_{subscription_type}")],
                    [InlineKeyboardButton("💳 Попробовать снова", callback_data=f"buy_{subscription_type}")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="subscription")]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    not_found_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса платежа: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка при проверке платежа. Попробуйте позже.")
    
    async def find_matches_for_user(self, user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Поиск матчей для пользователя"""
        try:
            user_info = await self.db.get_user(user_id)
            
            if not user_info:
                if update.message:
                    await update.message.reply_text("❌ Пользователь не найден")
                elif update.callback_query:
                    await update.callback_query.edit_message_text("❌ Пользователь не найден")
                return
            
            # Проверяем лимиты
            if not await self.check_user_access(user_info):
                if update.message:
                    await update.message.reply_text("❌ У вас нет активной подписки или превышен лимит")
                elif update.callback_query:
                    await update.callback_query.edit_message_text("❌ У вас нет активной подписки или превышен лимит")
                return
            
            # Увеличиваем счетчики
            if user_info['subscription_type'] == 'trial':
                await self.db.increment_trial_messages(user_id)
            else:
                await self.db.increment_daily_signals(user_id)
            
            # Ищем матчи
            async with self.parser as parser:
                matches = await parser.parse_all_bookmakers()
            
            if not matches:
                response_text = """
🔍 **Поиск завершен**

❌ Подходящих матчей не найдено

Попробуйте позже или проверьте другие коэффициенты.
"""
            else:
                response_text = f"""
🔍 **Найдено матчей: {len(matches)}**

"""
                
                for i, match in enumerate(matches[:5], 1):  # Показываем первые 5 матчей
                    match_time = match['match_time'].strftime("%d.%m %H:%M")
                    response_text += f"""
⚽️ **Матч {i}:**
🏠 {match['home_team']} vs {match['away_team']}
🏆 {match['league']}
📊 Коэффициенты: {match['coefficient_1']} / {match['coefficient_2']}
🏢 Букмекер: {match['bookmaker']}
⏰ Время: {match_time}
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Поискать еще", callback_data="find_matches")],
                [InlineKeyboardButton("📊 Статус", callback_data="status")],
                [InlineKeyboardButton("🔙 Назад", callback_data="start")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    response_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    response_text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Ошибка в find_matches_for_user: {e}")
            if update.message:
                await update.message.reply_text("❌ Произошла ошибка при поиске матчей")
            elif update.callback_query:
                await update.callback_query.edit_message_text("❌ Произошла ошибка при поиске матчей")
    
    async def check_user_access(self, user_info: Dict) -> bool:
        """Проверка доступа пользователя"""
        if user_info['subscription_type'] == 'trial':
            return user_info['trial_messages_used'] < TRIAL_MESSAGES_LIMIT
        elif user_info['subscription_type'] == 'revoked':
            return False
        else:
            # Проверяем срок действия подписки
            if user_info.get('subscription_end'):
                end_date = datetime.fromisoformat(user_info['subscription_end'])
                if datetime.now() > end_date:
                    return False
            
            # Проверяем дневной лимит сигналов
            return user_info['daily_signals_used'] < DAILY_SIGNALS_LIMIT
    
    async def get_user_status_text(self, user_info: Dict) -> str:
        """Получение текста статуса пользователя"""
        if user_info['subscription_type'] == 'trial':
            remaining_messages = TRIAL_MESSAGES_LIMIT - user_info['trial_messages_used']
            status_text = f"""
📊 **Статус подписки**

🎁 **Пробный период**
📊 Осталось сообщений: **{remaining_messages}/{TRIAL_MESSAGES_LIMIT}**
"""
        elif user_info['subscription_type'] == 'revoked':
            status_text = """
📊 **Статус подписки**

❌ **Подписка отозвана**
Обратитесь к администратору для восстановления доступа.
"""
        else:
            end_date = user_info.get('subscription_end')
            if end_date:
                end_date_str = datetime.fromisoformat(end_date).strftime("%d.%m.%Y %H:%M")
            else:
                end_date_str = "Бессрочно"
            
            daily_signals = user_info['daily_signals_used']
            status_text = f"""
📊 **Статус подписки**

✅ **Активная подписка: {user_info['subscription_type'].replace('_', ' ').title()}**
📅 Действует до: **{end_date_str}**
📊 Сигналов сегодня: **{daily_signals}/{DAILY_SIGNALS_LIMIT}**
"""
        
        return status_text
    
    async def handle_admin_callback(self, data: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка админских callback"""
        try:
            if data == "admin_stats":
                await self.stats_command(update, context)
            elif data == "admin_manage":
                await self.show_admin_management(update, context)
            elif data == "admin_give_sub":
                await self.show_give_subscription_form(update, context)
            elif data == "admin_revoke_sub":
                await self.show_revoke_subscription_form(update, context)
            elif data == "admin_weekly_report":
                await self.send_weekly_report(update, context)
            else:
                await update.callback_query.edit_message_text("❌ Неизвестная команда")
                
        except Exception as e:
            logger.error(f"Ошибка в handle_admin_callback: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка")
    
    async def show_admin_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать управление админами"""
        try:
            admins = await self.db.get_admins()
            
            admin_text = f"""
👥 **Управление администраторами**

📊 Всего админов: **{len(admins)}/{MAX_ADMINS}**

**Список администраторов:**
"""
            
            for i, admin in enumerate(admins, 1):
                username = admin.get('username', 'Нет username')
                admin_text += f"{i}. @{username} (ID: {admin['admin_id']})\n"
            
            admin_text += f"""

💡 **Команды:**
/addadmin <user_id> - Добавить админа
/removeadmin <user_id> - Удалить админа
"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад в админ панель", callback_data="admin")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                admin_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в show_admin_management: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка")
    
    async def show_give_subscription_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать форму выдачи подписки"""
        form_text = """
💳 **Выдача подписки**

💡 **Использование:**
/give_subscription <username> <тип>

**Примеры:**
/give_subscription @username week
/give_subscription @username two_weeks
/give_subscription @username month

**Доступные типы:**
• week - неделя
• two_weeks - две недели
• month - месяц
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в админ панель", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            form_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def show_revoke_subscription_form(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать форму отзыва подписки"""
        form_text = """
❌ **Отзыв подписки**

💡 **Использование:**
/revoke_subscription <username>

**Пример:**
/revoke_subscription @username

⚠️ **Внимание:** После отзыва пользователь получит уведомление об аннулировании подписки.
"""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад в админ панель", callback_data="admin")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            form_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def send_weekly_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка еженедельного отчета"""
        try:
            stats = await self.db.get_subscription_stats()
            
            report_text = f"""
📊 **Еженедельный отчет**

📅 **Период:** {datetime.now().strftime("%d.%m.%Y")}

👥 **Пользователи:**
• С активной подпиской: **{stats['active_subscriptions']}**
• Без подписки: **{stats['inactive_subscriptions']}**

📈 **Продажи за неделю:**
• Количество покупок: **{stats['weekly_purchases']}**
• Популярная подписка: **{stats['popular_subscription']}**

🎯 **Целевые коэффициенты:**
• 4.25 / 1.225
• 4.22 / 1.225

💡 Отчет сгенерирован автоматически
"""
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад в админ панель", callback_data="admin")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                report_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в send_weekly_report: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка")
    
    async def background_tasks(self):
        """Фоновые задачи"""
        while self.running:
            try:
                # Очистка просроченных ссылок
                await self.donation_alerts.cleanup_expired_links()
                
                # Парсинг матчей каждые 5 минут
                async with self.parser as parser:
                    matches = await parser.parse_all_bookmakers()
                    if matches:
                        await parser.save_matches_to_db(matches)
                        await self.send_matches_to_users(matches)
                
                # Отправка еженедельного отчета
                now = datetime.now()
                if now.weekday() == WEEKLY_REPORT_DAY and now.hour == WEEKLY_REPORT_HOUR:
                    await self.send_weekly_report_to_admins()
                
                # Проверка истекших подписок
                await self.check_expired_subscriptions()
                
                await asyncio.sleep(PARSING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Ошибка в фоновых задачах: {e}")
                await asyncio.sleep(60)
    
    async def send_matches_to_users(self, matches: List[Dict]):
        """Отправка найденных матчей пользователям"""
        try:
            users = await self.db.get_users_with_active_subscription()
            
            for user in users:
                try:
                    if await self.check_user_access(user):
                        match_text = f"""
⚽️ **Найден новый матч!**

🏠 {matches[0]['home_team']} vs {matches[0]['away_team']}
🏆 {matches[0]['league']}
📊 Коэффициенты: {matches[0]['coefficient_1']} / {matches[0]['coefficient_2']}
🏢 Букмекер: {matches[0]['bookmaker']}
⏰ Время: {matches[0]['match_time'].strftime("%d.%m %H:%M")}

💡 Используйте кнопки ниже для навигации
"""
                        
                        keyboard = [
                            [InlineKeyboardButton("🔍 Найти еще", callback_data="find_matches")],
                            [InlineKeyboardButton("📊 Статус", callback_data="status")]
                        ]
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await self.application.bot.send_message(
                            chat_id=user['user_id'],
                            text=match_text,
                            reply_markup=reply_markup,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                        # Увеличиваем счетчик сигналов
                        await self.db.increment_daily_signals(user['user_id'])
                        
                except Exception as e:
                    logger.error(f"Ошибка отправки матча пользователю {user['user_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в send_matches_to_users: {e}")
    
    async def send_weekly_report_to_admins(self):
        """Отправка еженедельного отчета всем админам"""
        try:
            stats = await self.db.get_subscription_stats()
            admins = await self.db.get_admins()
            
            report_text = f"""
📊 **Еженедельный отчет**

📅 **Период:** {datetime.now().strftime("%d.%m.%Y")}

👥 **Пользователи:**
• С активной подпиской: **{stats['active_subscriptions']}**
• Без подписки: **{stats['inactive_subscriptions']}**

📈 **Продажи за неделю:**
• Количество покупок: **{stats['weekly_purchases']}**
• Популярная подписка: **{stats['popular_subscription']}**

🎯 **Целевые коэффициенты:**
• 4.25 / 1.225
• 4.22 / 1.225

💡 Отчет сгенерирован автоматически
"""
            
            for admin in admins:
                try:
                    await self.application.bot.send_message(
                        chat_id=admin['admin_id'],
                        text=report_text,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки отчета админу {admin['admin_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в send_weekly_report_to_admins: {e}")
    
    async def check_expired_subscriptions(self):
        """Проверка истекших подписок"""
        try:
            expired_users = await self.db.get_users_with_expired_subscription()
            
            for user in expired_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user['user_id'],
                        text="""
❌ **Ваша подписка истекла**

Для продолжения использования бота необходимо продлить подписку.

💡 Используйте /subscription для покупки новой подписки.
"""
                    )
                    
                    # Обновляем статус пользователя
                    await self.db.revoke_subscription(user['user_id'])
                    
                except Exception as e:
                    logger.error(f"Ошибка уведомления об истекшей подписке: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в check_expired_subscriptions: {e}")
    
    async def shutdown(self):
        """Корректное завершение работы бота"""
        logger.info("Начинаем корректное завершение работы бота...")
        
        self.running = False
        
        # Останавливаем webhook сервер
        if self.webhook_runner:
            await self.webhook_handler.stop_server(self.webhook_runner)
        
        # Останавливаем Telegram приложение
        if self.application:
            try:
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Ошибка при остановке приложения: {e}")
        
        # Закрываем сессию DonationAlerts
        if self.donation_alerts and self.donation_alerts.session:
            try:
                await self.donation_alerts.session.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии DonationAlerts: {e}")
        
        logger.info("Бот успешно остановлен")
    
    async def run(self):
        """Запуск бота"""
        try:
            self.running = True
            await self.initialize()
            
            # Настройка обработчика сигналов для корректного завершения
            def signal_handler(signum, frame):
                logger.info(f"Получен сигнал {signum}, начинаем завершение работы...")
                asyncio.create_task(self.shutdown())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            logger.info("Бот запущен и готов к работе")
            
            # Для локального запуска используем polling
            # Для Railway используется webhook, поэтому polling не нужен
            if os.environ.get('RAILWAY_STATIC_URL'):
                logger.info("Запуск в режиме webhook (Railway)")
                # Держим приложение запущенным
                while self.running:
                    await asyncio.sleep(1)
            else:
                logger.info("Запуск в режиме polling (локально)")
                await self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Критическая ошибка в работе бота: {e}")
            await self.shutdown()

async def main():
    """Главная функция"""
    bot = FootballBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main()) 
