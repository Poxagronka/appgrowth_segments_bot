# Dockerfile — образ для Fly.io
FROM python:3.11-slim

# Рабочая папка
WORKDIR /app

# Сразу устанавливаем все зависимости
RUN pip install --no-cache-dir \
  slack-bolt \
  Flask \
  python-dotenv \
  requests \
  beautifulsoup4

# Копируем код
COPY . .

# Запуск бота
CMD ["python3", "app.py"]
# Dockerfile — минимальный образ для Fly.io
FROM python:3.11-slim

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код
COPY . .

# Запускаем бота с python3
CMD ["python3", "app.py"]
