# Base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    unzip \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable to use Chromium
ENV CHROME_BIN=/usr/bin/chromium

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app files
COPY . /app
WORKDIR /app

# Expose the port and set the command
EXPOSE 10000
CMD ["gunicorn", "--timeout", "120", "-b", "0.0.0.0:10000", "flask_app:app"]

# CMD ["gunicorn", "flask_app:app", "--bind", "0.0.0.0:8000"]
