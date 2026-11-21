FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcb-dri3-0 \
    libdrm2 libgbm1 libasound2 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium
COPY . .
CMD ["python", "bot.py"]
