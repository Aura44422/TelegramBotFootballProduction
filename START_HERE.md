# 🚀 Football Signals Bot - Начало работы

## 🎯 Что это?

**Football Signals Bot** - полнофункциональный Telegram бот для поиска футбольных матчей с коэффициентами **4.25/1.225** или **4.22/1.225**.

## ⚡ Быстрый старт (5 минут)

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка токенов
```bash
cp .env.example .env
```

Отредактируйте `.env`:
```env
BOT_TOKEN=ваш_токен_бота_от_botfather
DONATION_ALERTS_TOKEN=ваш_токен_donation_alerts
DONATION_ALERTS_URL=https://www.donationalerts.com/r/ваш_username
```

### 3. Запуск
```bash
python run.py
```

### 4. Настройка админа
1. Найдите свой ID: @userinfobot
2. Отправьте боту: `/addadmin ВАШ_ID`
3. Проверьте: `/admin`

## ✅ Готово!

Бот работает и готов к использованию!

---

## 📋 Что умеет бот?

### 🎁 Пробный период
- 3 бесплатных сообщения для новых пользователей
- Автоматическая активация

### 💳 Система подписок
- **Неделя** - 650₽
- **Две недели** - 1300₽ (экономия 300₽)
- **Месяц** - 2500₽ (экономия 700₽)
- До 15 сигналов в день

### 🔧 Админ панель
- Управление администраторами (до 5 человек)
- Выдача и отзыв подписок
- Статистика пользователей
- Еженедельные отчеты

### ⚽️ Парсинг букмекеров
- 1xbet, bet365, William Hill, bwin, Unibet
- Автоматический поиск каждые 5 минут
- Уведомления о найденных матчах

### 💰 Платежи
- Интеграция с DonationAlerts
- Автоматическая обработка платежей
- Уникальные ссылки для каждого пользователя

---

## 📚 Документация

- **README.md** - Полная документация
- **DEPLOYMENT.md** - Развертывание на сервере
- **PROJECT_INFO.md** - Техническая информация
- **test_bot.py** - Тестирование функций

---

## 🛠️ Команды бота

### Для пользователей:
- `/start` - Запуск бота
- `/help` - Справка
- `/status` - Статус подписки
- `/subscription` - Управление подпиской

### Для администраторов:
- `/admin` - Админ панель
- `/addadmin <user_id>` - Добавить администратора
- `/removeadmin <user_id>` - Удалить администратора
- `/stats` - Статистика
- `/give_subscription <username> <type>` - Выдать подписку
- `/revoke_subscription <username>` - Отозвать подписку

---

## 🔧 Тестирование

Запустите тесты перед использованием:
```bash
python test_bot.py
```

---

## 🚨 Важно!

1. **Настройте токены** в файле `.env`
2. **Добавьте себя как админа** после первого запуска
3. **Проверьте webhook URL** в настройках DonationAlerts
4. **Мониторьте логи** для отладки

---

## 📞 Поддержка

При проблемах:
1. Проверьте логи в `bot.log`
2. Убедитесь в правильности настроек
3. Запустите тесты: `python test_bot.py`

---

**Удачного использования! 🚀** 