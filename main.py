import logging
from datetime import datetime
import time
import os
import requests
from flask import Flask
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

app = Flask(__name__)

class CryptoMonitor:
    def __init__(self):
        # Configuração do logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Configurações do Telegram
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_base_url = f"https://api.telegram.org/bot{self.telegram_token}"
        
        # Configurações do monitor
        self.base_url = "https://agile-cliffs-23967.herokuapp.com/binance"
        self.driver = None
        self.last_processed = set()
        
    # [Todo o resto dos métodos da classe continua igual...]
    [Métodos anteriores aqui]

monitor = CryptoMonitor()

def run_bot():
    monitor.run()

@app.route('/')
def home():
    return 'Bot is running!'

if __name__ == "__main__":
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
