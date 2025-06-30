FROM python:3.11-slim

WORKDIR /app

# Устанавливаем необходимые пакеты для сборки и компиляции
RUN apt-get update && apt-get install -y gcc build-essential libffi-dev python3-dev

# Обновляем pip до последней версии
RUN pip install --upgrade pip

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Запускаем главный файл бота
CMD ["python", "main.py"]
