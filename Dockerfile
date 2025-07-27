FROM python:3.11-slim

# Устанавливаем системные зависимости для sqlite3 и сборки
RUN apt-get update && apt-get install -y libsqlite3-0 gcc build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "railway_start.py"] 