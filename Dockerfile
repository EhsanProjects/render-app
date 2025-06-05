FROM python:3.10-slim

# Install system dependencies and Chrome
RUN apt-get update && \
    apt-get install -y wget curl gnupg unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm ./google-chrome-stable_current_amd64.deb

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app/

RUN pip install --upgrade pip

RUN pip install -r requirements.txt


EXPOSE 8000
CMD ["gunicorn", "--timeout", "120", "-b", "0.0.0.0:10000", "flask_app:app"]

# CMD ["gunicorn", "flask_app:app", "--bind", "0.0.0.0:8000"]
