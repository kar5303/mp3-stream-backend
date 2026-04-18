FROM python:3.12-slim

# 安裝 ffmpeg（yt-dlp 轉 MP3 必要）
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 確保 yt-dlp 是最新版
RUN pip install --no-cache-dir --upgrade yt-dlp

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
