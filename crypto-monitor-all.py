import logging
from datetime import datetime
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class CryptoMonitor:
    def __init__(self, telegram_token, telegram_chat_id):
        # Configuração do logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Configurações Telegram
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.telegram_base_url = f"https://api.telegram.org/bot{telegram_token}"
        
        # Configurações do monitor
        self.base_url = "https://agile-cliffs-23967.herokuapp.com/binance"
        self.driver = None
        self.last_processed = set()  # Guarda apenas as últimas entradas
            
    def initialize_driver(self):
        """Inicializa o Chrome WebDriver"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 20)
            
            logging.info("WebDriver inicializado com sucesso")
            return True
        except Exception as e:
            logging.error(f"Erro ao inicializar WebDriver: {e}")
            return False
            
    def send_telegram_message(self, text):
        """Envia mensagem para o Telegram"""
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
            logging.error(f"Erro ao enviar mensagem Telegram: {e}")
            return False
            
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
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Pula o cabeçalho
            
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
                    
                    # Cria uma chave única para cada entrada
                    entry_key = f"{coin_data['coin']}_{coin_data['timestamp']}"
                    current_entries.add(entry_key)
                    
                    # Se é uma nova entrada que não vimos antes
                    if entry_key not in self.last_processed:
                        message = self.format_coin_message(coin_data)
                        self.send_telegram_message(message)
                        logging.info(f"Nova atualização: {coin_data['coin']}")
                        
                except Exception as e:
                    logging.error(f"Erro ao processar linha: {e}")
                    continue
            
            # Atualiza o conjunto de entradas processadas
            self.last_processed = current_entries
                    
        except Exception as e:
            logging.error(f"Erro ao verificar atualizações: {e}")
            return False
            
        return True
    
    def run(self):
        """Executa o monitor"""
        if not self.initialize_driver():
            return
            
        try:
            logging.info("Iniciando monitoramento...")
            self.driver.get(self.base_url)
            
            # Aguarda o carregamento inicial da página
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))
            
            while True:
                try:
                    self.check_updates()
                    time.sleep(10)  # Verifica a cada 10 segundos
                    
                except WebDriverException:
                    logging.error("Erro no WebDriver, tentando reconectar...")
                    self.driver.quit()
                    if not self.initialize_driver():
                        break
                    self.driver.get(self.base_url)
                    time.sleep(5)
                    
        except KeyboardInterrupt:
            logging.info("Monitoramento interrompido pelo usuário")
        except Exception as e:
            logging.error(f"Erro fatal: {e}")
        finally:
            if self.driver:
                self.driver.quit()
            logging.info("Monitoramento finalizado")

if __name__ == "__main__":
    # Configurações
    TELEGRAM_TOKEN = "8128618696:AAFYD-LPrR6jZXkkx4y7TnJoZqymjBeJqIg"
    TELEGRAM_CHAT_ID = "6347487922"
    
    # Iniciar o monitor
    monitor = CryptoMonitor(
        telegram_token=TELEGRAM_TOKEN,
        telegram_chat_id=TELEGRAM_CHAT_ID
    )
    
    monitor.run()
