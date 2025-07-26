import os
from dotenv import load_dotenv

load_dotenv()

# Основные настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
DONATION_ALERTS_TOKEN = os.getenv('DONATION_ALERTS_TOKEN')
DONATION_ALERTS_URL = os.getenv('DONATION_ALERTS_URL')

# Настройки базы данных
DATABASE_PATH = 'bot_database.db'

# Настройки подписок
SUBSCRIPTION_PRICES = {
    'week': 650,
    'two_weeks': 1300,
    'month': 2500
}

# Настройки пробного периода
TRIAL_MESSAGES_LIMIT = 3

# Настройки сигналов
DAILY_SIGNALS_LIMIT = 15

# Целевые коэффициенты для поиска
TARGET_COEFFICIENTS = [
    (4.25, 1.225),
    (4.22, 1.225)
]

# Настройки парсинга
PARSING_INTERVAL = 300  # 5 минут
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Настройки админ-панели
MAX_ADMINS = 5

# Настройки отчетов
WEEKLY_REPORT_DAY = 0  # Понедельник
WEEKLY_REPORT_HOUR = 9  # 9:00

# Настройки логирования
LOG_LEVEL = 'INFO'
LOG_FILE = 'bot.log' 