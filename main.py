import logging
from datetime import datetime
import time
import os
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException

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
            
    def initialize_driver(self):
        """Inicializa o Chrome WebDriver com configurações para servidor"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--single-process')
            chrome_options.binary_location = "/usr/bin/google-chrome"
            
            # Removida a referência ao Service, deixando o Selenium gerenciar automaticamente
            self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            
            logging.info("WebDriver inicializado com sucesso")
            return True
            
        except Exception as e:
            logging.error(f"Erro ao inicializar WebDriver: {str(e)}")
            if self.driver:
                self.driver.quit()
            return False
            
    def send_telegram_message(self, text):
        """Envia mensagem para o Telegram com retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = f"{self.telegram_base_url}/sendMessage"
                data = {
                    "chat_id": self.telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                
                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Erro ao enviar mensagem Telegram: {e}")
                    return False
                time.sleep(2 ** attempt)
            
    def format_coin_message(self, coin_data):
        """Formata a mensagem com os dados da moeda"""
        return (
            f"🪙 <b>{coin_data['coin']}</b>\n"
            f"📊 Pings: {coin_data['pings']}\n"
            f"💰 Vol BTC: {coin_data['net_vol_btc']}\n"
            f"📈 Vol %: {coin_data['net_vol_percent']}%\n"
            f"📊 Vol Total: {coin_data['recent_total_vol_btc']} BTC\n"
            f"📊 Vol Recente %: {coin_data['recent_vol_percent']}%\n"
            f"💹 Vol Net: {coin_data['recent_net_vol']}\n"
            f"⏰ {coin_data['timestamp']}"
        )
    
    def check_updates(self):
        """Verifica todas as atualizações na página"""
        try:
            table = self.driver.find_element(By.CLASS_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]
            
            current_entries = set()
            
            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 8:
                        continue
                        
                    coin_data = {
                        'coin': cols[0].text,
                        'pings': int(cols[1].text),
                        'net_vol_btc': float(cols[2].text),
                        'net_vol_percent': float(cols[3].text.strip('%')),
                        'recent_total_vol_btc': float(cols[4].text),
                        'recent_vol_percent': float(cols[5].text.strip('%')),
                        'recent_net_vol': float(cols[6].text),
                        'timestamp': cols[7].text
                    }
                    
                    entry_key = f"{coin_data['coin']}_{coin_data['timestamp']}"
                    current_entries.add(entry_key)
                    
                    if entry_key not in self.last_processed:
                        message = self.format_coin_message(coin_data)
                        self.send_telegram_message(message)
                        logging.info(f"Nova atualização: {coin_data['coin']}")
                        
                except Exception as e:
                    logging.error(f"Erro ao processar linha: {e}")
                    continue
            
            self.last_processed = current_entries
                    
        except Exception as e:
            logging.error(f"Erro ao verificar atualizações: {e}")
            return False
            
        return True
    
    def run(self):
        """Executa o monitor com proteção contra erros"""
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries:
            try:
                if not self.initialize_driver():
                    retry_count += 1
                    time.sleep(60)
                    continue
                    
                logging.info("Iniciando monitoramento...")
                self.driver.get(self.base_url)
                
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))
                retry_count = 0
                
                while True:
                    try:
                        self.check_updates()
                        time.sleep(10)
                        
                    except WebDriverException:
                        logging.error("Erro no WebDriver, tentando reconectar...")
                        raise
                        
            except Exception as e:
                logging.error(f"Erro no loop principal: {e}")
                retry_count += 1
                
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                
                if retry_count < max_retries:
                    sleep_time = min(300, 60 * retry_count)
                    logging.info(f"Tentando reconexão em {sleep_time} segundos...")
                    time.sleep(sleep_time)
                else:
                    logging.error("Número máximo de tentativas excedido")
                    break
                    
        logging.info("Monitoramento finalizado")

if __name__ == "__main__":
    monitor = CryptoMonitor()
    monitor.run()
