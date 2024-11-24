FROM python:3.9-slim

# Instala dependências necessárias
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    libxss1 \
    libappindicator1 \
    libindicator7 \
    xvfb \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Instala Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Inicia o script
CMD ["python", "main.py"]
