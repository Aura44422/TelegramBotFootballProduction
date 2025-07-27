# 🚀 Развертывание на Railway

## 📋 Предварительные требования

1. **Telegram Bot Token** - получите у @BotFather
2. **DonationAlerts Token** - получите в личном кабинете DonationAlerts
3. **DonationAlerts URL** - ваша ссылка для донатов

## 🔧 Настройка Railway

### 1. Создание проекта
1. Зайдите на [Railway.app](https://railway.app)
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Подключите ваш GitHub репозиторий

### 2. Настройка переменных окружения
В Railway Dashboard перейдите в раздел "Variables" и добавьте:

```env
BOT_TOKEN=your_telegram_bot_token_here
DONATION_ALERTS_TOKEN=your_donation_alerts_token_here
DONATION_ALERTS_URL=https://www.donationalerts.com/r/your_username
```

### 3. Настройка Networking
1. Перейдите в раздел "Networking"
2. В поле "Port" введите: `8080`
3. Нажмите "Generate Domain"
4. Скопируйте полученный URL (например: `https://your-app-name.up.railway.app`)

### 4. Настройка DonationAlerts Webhook
1. Зайдите в личный кабинет DonationAlerts
2. Перейдите в "API" → "OAuth приложения"
3. Создайте новое приложение:
   - **Имя приложения**: `TelegramBotFootballProduction`
   - **URL перенаправления**: `https://your-app-name.up.railway.app/webhook/donation_alerts`
4. Скопируйте полученный токен и добавьте его в переменные Railway

## 🚀 Запуск

После настройки всех переменных:
1. Railway автоматически запустит приложение
2. Проверьте логи в разделе "Deployments"
3. Убедитесь, что нет ошибок

## 🔍 Проверка работы

1. **Проверка бота**: Отправьте `/start` вашему боту
2. **Проверка webhook**: Откройте `https://your-app-name.up.railway.app/health`
3. **Проверка логов**: Следите за логами в Railway Dashboard

## 🛠️ Устранение неполадок

### Ошибка "ImportError: cannot import name 'ParseMode'"
✅ **Исправлено**: Обновлен импорт в `main.py` и `webhook_handler.py`

### Ошибка "Container crashed"
1. Проверьте переменные окружения
2. Убедитесь, что все токены корректны
3. Проверьте логи в Railway Dashboard

### Webhook не работает
1. Убедитесь, что URL в DonationAlerts правильный
2. Проверьте, что порт 8080 открыт
3. Убедитесь, что домен Railway активен

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в Railway Dashboard
2. Убедитесь, что все переменные окружения настроены
3. Проверьте, что DonationAlerts webhook URL корректный

## 🔄 Обновления

Для обновления бота:
1. Запушьте изменения в GitHub
2. Railway автоматически перезапустит приложение
3. Проверьте логи на наличие ошибок 