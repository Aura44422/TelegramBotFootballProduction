# 🚀 Инструкции по развертыванию Football Signals Bot

## 📋 Предварительные требования

### Системные требования
- Python 3.8 или выше
- 2GB RAM минимум
- 1GB свободного места на диске
- Стабильное интернет-соединение

### Необходимые аккаунты
1. **Telegram Bot Token** - получите у @BotFather
2. **DonationAlerts аккаунт** - зарегистрируйтесь на donationalerts.com
3. **Хостинг/VPS** (рекомендуется для продакшена)

## 🔧 Пошаговая установка

### Шаг 1: Подготовка окружения

#### На Windows:
```bash
# Установка Python (если не установлен)
# Скачайте с python.org

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt
```

#### На Linux/Mac:
```bash
# Установка Python
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 2: Настройка переменных окружения

1. Скопируйте файл с переменными:
```bash
cp .env.example .env
```

2. Отредактируйте файл `.env`:
```env
# Токен Telegram бота (получите у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Токен DonationAlerts (получите в личном кабинете)
DONATION_ALERTS_TOKEN=your_donation_alerts_token_here

# Базовая ссылка DonationAlerts
DONATION_ALERTS_URL=https://www.donationalerts.com/r/your_username
```

### Шаг 3: Получение токенов

#### Telegram Bot Token:
1. Напишите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота
   - Введите username бота (должен заканчиваться на 'bot')
4. Скопируйте полученный токен в `.env`

#### DonationAlerts Token:
1. Зарегистрируйтесь на [donationalerts.com](https://donationalerts.com)
2. Войдите в личный кабинет
3. Перейдите в раздел "API"
4. Создайте новый токен
5. Скопируйте токен в `.env`

### Шаг 4: Первый запуск

```bash
# Активируйте виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Запуск бота
python run.py
```

### Шаг 5: Настройка первого администратора

1. Найдите свой Telegram ID через @userinfobot
2. Отправьте боту команду: `/addadmin YOUR_TELEGRAM_ID`
3. Проверьте доступ к админ панели: `/admin`

## 🌐 Продакшен развертывание

### Вариант 1: VPS (рекомендуется)

#### Настройка сервера:
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python и зависимостей
sudo apt install python3 python3-pip python3-venv nginx supervisor

# Создание пользователя для бота
sudo useradd -m -s /bin/bash botuser
sudo su - botuser

# Клонирование проекта
git clone <your-repo-url> /home/botuser/football-bot
cd /home/botuser/football-bot

# Настройка виртуального окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
nano .env  # Отредактируйте файл
```

#### Настройка Supervisor:
```bash
# Создание конфигурации supervisor
sudo nano /etc/supervisor/conf.d/football-bot.conf
```

Содержимое файла:
```ini
[program:football-bot]
command=/home/botuser/football-bot/venv/bin/python /home/botuser/football-bot/run.py
directory=/home/botuser/football-bot
user=botuser
autostart=true
autorestart=true
stderr_logfile=/var/log/football-bot.err.log
stdout_logfile=/var/log/football-bot.out.log
environment=PATH="/home/botuser/football-bot/venv/bin"
```

```bash
# Перезапуск supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start football-bot
```

#### Настройка Nginx (для webhook'ов):
```bash
sudo nano /etc/nginx/sites-available/football-bot
```

Содержимое файла:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/football-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Вариант 2: Docker

#### Создание Dockerfile:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "run.py"]
```

#### Создание docker-compose.yml:
```yaml
version: '3.8'

services:
  football-bot:
    build: .
    container_name: football-bot
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DONATION_ALERTS_TOKEN=${DONATION_ALERTS_TOKEN}
      - DONATION_ALERTS_URL=${DONATION_ALERTS_URL}
    volumes:
      - ./data:/app/data
    ports:
      - "8080:8080"
```

#### Запуск:
```bash
docker-compose up -d
```

## 🔒 Настройка безопасности

### Firewall:
```bash
# Настройка UFW
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### SSL сертификат (Let's Encrypt):
```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com

# Автоматическое обновление
sudo crontab -e
# Добавьте строку:
0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Мониторинг

### Логи:
```bash
# Просмотр логов бота
tail -f /var/log/football-bot.out.log

# Просмотр ошибок
tail -f /var/log/football-bot.err.log

# Логи supervisor
sudo supervisorctl status football-bot
```

### Системный мониторинг:
```bash
# Установка htop
sudo apt install htop

# Мониторинг ресурсов
htop
```

## 🔄 Обновления

### Автоматические обновления:
```bash
# Создание скрипта обновления
nano /home/botuser/update-bot.sh
```

Содержимое скрипта:
```bash
#!/bin/bash
cd /home/botuser/football-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart football-bot
```

```bash
# Делаем скрипт исполняемым
chmod +x /home/botuser/update-bot.sh

# Добавляем в cron для автоматических обновлений
crontab -e
# Добавьте строку для обновления каждый день в 3:00:
0 3 * * * /home/botuser/update-bot.sh
```

## 🚨 Устранение неполадок

### Бот не запускается:
1. Проверьте токены в `.env`
2. Проверьте логи: `tail -f /var/log/football-bot.err.log`
3. Проверьте статус: `sudo supervisorctl status football-bot`

### Не работают платежи:
1. Проверьте токен DonationAlerts
2. Проверьте webhook URL в настройках DonationAlerts
3. Проверьте логи webhook'ов

### Парсинг не работает:
1. Проверьте интернет-соединение
2. Проверьте доступность сайтов букмекеров
3. Проверьте логи парсера

### Высокая нагрузка на CPU:
1. Увеличьте интервал парсинга в `config.py`
2. Оптимизируйте запросы к базе данных
3. Рассмотрите возможность масштабирования

## 📈 Масштабирование

### Для большого количества пользователей:
1. Используйте PostgreSQL вместо SQLite
2. Настройте Redis для кэширования
3. Используйте несколько экземпляров бота
4. Настройте балансировщик нагрузки

### Мониторинг производительности:
```bash
# Установка мониторинга
sudo apt install htop iotop nethogs

# Мониторинг в реальном времени
htop
iotop
nethogs
```

## 🔧 Дополнительные настройки

### Настройка резервного копирования:
```bash
# Создание скрипта бэкапа
nano /home/botuser/backup-bot.sh
```

Содержимое скрипта:
```bash
#!/bin/bash
BACKUP_DIR="/home/botuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /home/botuser/football-bot/bot_database.db $BACKUP_DIR/bot_database_$DATE.db
cp /home/botuser/football-bot/.env $BACKUP_DIR/env_$DATE.backup

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.backup" -mtime +7 -delete
```

```bash
# Делаем скрипт исполняемым
chmod +x /home/botuser/backup-bot.sh

# Добавляем в cron для ежедневных бэкапов
crontab -e
# Добавьте строку:
0 2 * * * /home/botuser/backup-bot.sh
```

---

## ✅ Проверка работоспособности

После установки проверьте:

1. ✅ Бот отвечает на команду `/start`
2. ✅ Админ панель доступна (`/admin`)
3. ✅ Парсинг работает (проверьте логи)
4. ✅ Платежи обрабатываются (тестовый платеж)
5. ✅ Webhook'и работают (проверьте `/health`)

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в `/var/log/football-bot.err.log`
2. Убедитесь в правильности настроек
3. Проверьте документацию в README.md
4. Обратитесь к системному администратору

---

**Удачного развертывания! 🚀** 