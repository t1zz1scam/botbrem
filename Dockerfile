FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y gcc build-essential libffi-dev python3-dev curl tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Обновляем pip
RUN pip install --upgrade pip

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Запускаем через uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
