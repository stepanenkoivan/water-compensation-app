
# Используем официальный образ Python 3.12.4
FROM python:3.12.4-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY . .

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для Streamlit
EXPOSE 8501

# Запускаем приложение
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
