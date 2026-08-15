FROM python:3.10-slim
RUN apt-get update && apt-get install -y libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatk-bridge2.0-0 libgtk-3-0 fonts-liberation libappindicator3-1 xdg-utils && rm -rf /var/lib/apt/lists/*
RUN pip install playwright==1.42.0 && playwright install chromium
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot_render_final.py"]
