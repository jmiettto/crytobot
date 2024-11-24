from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import logging.handlers
import time
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
import requests
import talib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def setup_logging(filename: str = 'trading.log') -> None:
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    file_handler = logging.handlers.RotatingFileHandler(
        filename, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

@dataclass
class MarketState:
    symbol: str
    start_time: datetime
    current_price: float
    highest_price: float = 0.0
    lowest_price: float = float('inf')
    volume_profile: List[float] = None
    entry_points: List[float] = None
    stop_loss: float = 0.0
    take_profit: float = 0.0
    signal_type: str = ""  # 'LONG' or 'SHORT'
    entry_triggered: bool = False
    is_active: bool = True

@dataclass
class TradingSignal:
    symbol: str
    price: float
    entry: float
    stop_loss: float
    take_profit: float
    signal_type: str
    confidence: float
    timestamp: datetime
    indicators: Dict[str, float]

class TelegramBot:
    """Enhanced Telegram bot with reliable messaging and retries"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        
        # Verify bot credentials on initialization
        self.verify_bot()
        
    def verify_bot(self) -> None:
        """Verify bot credentials and permissions"""
        try:
            response = self.session.get(f"{self.base_url}/getMe", timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('ok'):
                raise ValueError(f"Bot verification failed: {data.get('description')}")
                
            logging.info(f"Bot verified: @{data['result']['username']}")
            
            # Test message permissions
            test_msg = "🤖 Bot initialized and ready"
            self.send_message(test_msg)
            
        except Exception as e:
            logging.error(f"Bot verification failed: {str(e)}")
            raise

    def send_message(self, text: str, retries: int = 3, parse_mode: str = "HTML") -> bool:
        """Send message with retry mechanism"""
        for attempt in range(retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode
                    },
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok'):
                    raise ValueError(f"Message send failed: {data.get('description')}")
                    
                logging.info(f"Message sent successfully (length: {len(text)})")
                return True
                
            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    delay = 2 ** attempt
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error("Max retries reached")
                    return False
                    
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                return False

class MarketAnalyzer:
    def __init__(self):
        self.RSI_PERIOD = 14
        self.RSI_OVERSOLD = 30
        self.RSI_OVERBOUGHT = 70
        self.EMA_SHORT = 9
        self.EMA_MEDIUM = 21
        self.EMA_LONG = 50
        self.VOLUME_THRESHOLD = 1.5

    def calculate_indicators(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Calculate technical indicators"""
        try:
            close = df['close'].astype(float).values
            high = df['high'].astype(float).values
            low = df['low'].astype(float).values
            volume = df['volume'].astype(float).values

            indicators = {}
            
            # EMAs
            indicators['EMA_short'] = talib.EMA(close, timeperiod=self.EMA_SHORT)
            indicators['EMA_medium'] = talib.EMA(close, timeperiod=self.EMA_MEDIUM)
            indicators['EMA_long'] = talib.EMA(close, timeperiod=self.EMA_LONG)
            
            # RSI
            indicators['RSI'] = talib.RSI(close, timeperiod=self.RSI_PERIOD)
            
            # MACD
            macd, signal, _ = talib.MACD(close)
            indicators['MACD'] = macd
            indicators['MACD_signal'] = signal
            
            # Bollinger Bands
            upper, middle, lower = talib.BBANDS(close)
            indicators['BB_upper'] = upper
            indicators['BB_middle'] = middle
            indicators['BB_lower'] = lower
            
            # ATR
            indicators['ATR'] = talib.ATR(high, low, close)

            return indicators
            
        except Exception as e:
            logging.error(f"Error calculating indicators: {str(e)}")
            return {}

    def analyze_market(self, df: pd.DataFrame, indicators: Dict[str, np.ndarray]) -> Optional[TradingSignal]:
        """Analyze market conditions and generate signals"""
        try:
            if not indicators:
                return None

            current_price = float(df['close'].iloc[-1])
            symbol = df['symbol'].iloc[0]

            # Get current indicator values
            rsi = indicators['RSI'][-1]
            macd = indicators['MACD'][-1]
            macd_signal = indicators['MACD_signal'][-1]
            atr = indicators['ATR'][-1]

            # Check for long signal
            if (indicators['EMA_short'][-1] > indicators['EMA_medium'][-1] and
                rsi < self.RSI_OVERBOUGHT and
                macd > macd_signal):

                return TradingSignal(
                    symbol=symbol,
                    price=current_price,
                    entry=current_price,
                    stop_loss=current_price - (2 * atr),
                    take_profit=current_price + (3 * atr),
                    signal_type="LONG",
                    confidence=0.8,
                    timestamp=datetime.now(),
                    indicators={
                        'RSI': rsi,
                        'MACD': macd,
                        'BB_upper': indicators['BB_upper'][-1],
                        'BB_lower': indicators['BB_lower'][-1]
                    }
                )

            # Check for short signal
            elif (indicators['EMA_short'][-1] < indicators['EMA_medium'][-1] and
                  rsi > self.RSI_OVERSOLD and
                  macd < macd_signal):

                return TradingSignal(
                    symbol=symbol,
                    price=current_price,
                    entry=current_price,
                    stop_loss=current_price + (2 * atr),
                    take_profit=current_price - (3 * atr),
                    signal_type="SHORT",
                    confidence=0.8,
                    timestamp=datetime.now(),
                    indicators={
                        'RSI': rsi,
                        'MACD': macd,
                        'BB_upper': indicators['BB_upper'][-1],
                        'BB_lower': indicators['BB_lower'][-1]
                    }
                )

            return None

        except Exception as e:
            logging.error(f"Error analyzing market: {str(e)}")
            return None

class TradingNotifier:
    def __init__(self, token: str, chat_id: str):
        self.bot = TelegramBot(token, chat_id)
        self.last_notification = {}
        self.MIN_NOTIFICATION_INTERVAL = 300  # 5 minutes

    def send_signal(self, signal: TradingSignal) -> bool:
        """Send trading signal with rate limiting"""
        if self._can_send_notification(signal.symbol):
            message = self._format_signal(signal)
            success = self.bot.send_message(message)
            if success:
                self.last_notification[signal.symbol] = datetime.now()
            return success
        return False

    def _format_signal(self, signal: TradingSignal) -> str:
        """Format trading signal message"""
        emoji = "🚀" if signal.signal_type == "LONG" else "🔻"
        confidence_stars = "⭐" * int(signal.confidence * 5)
        
        return (
            f"{emoji} <b>Trading Signal - {signal.symbol}</b>\n\n"
            f"📊 Type: {signal.signal_type}\n"
            f"💰 Price: {signal.price:.8f}\n"
            f"✅ Entry: {signal.entry:.8f}\n"
            f"🛑 Stop Loss: {signal.stop_loss:.8f}\n"
            f"🎯 Take Profit: {signal.take_profit:.8f}\n"
            f"📈 Confidence: {confidence_stars} ({signal.confidence:.2%})\n\n"
            f"📊 Indicators:\n"
            f"RSI: {signal.indicators['RSI']:.2f}\n"
            f"MACD: {signal.indicators['MACD']:.8f}\n"
            f"BB Upper: {signal.indicators['BB_upper']:.8f}\n"
            f"BB Lower: {signal.indicators['BB_lower']:.8f}\n\n"
            f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _can_send_notification(self, symbol: str) -> bool:
        """Check if enough time has passed since last notification"""
        if symbol not in self.last_notification:
            return True
        time_since_last = (datetime.now() - self.last_notification[symbol]).total_seconds()
        return time_since_last >= self.MIN_NOTIFICATION_INTERVAL

    def cleanup_old_notifications(self, max_age: int = 3600) -> None:
        """Clean up old notification history"""
        cutoff = datetime.now()
        self.last_notification = {
            symbol: timestamp
            for symbol, timestamp in self.last_notification.items()
            if (cutoff - timestamp).total_seconds() < max_age
        }

class CryptoMonitor:
    def __init__(self, notifier: TradingNotifier):
        setup_logging()
        self.notifier = notifier
        self.analyzer = MarketAnalyzer()
        self.monitored_pairs = {}
        self.last_update = {}
        self.initialize_driver()
        
    def initialize_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)
        self.wait = WebDriverWait(self.driver, 20)

    def get_binance_data(self, symbol: str, interval: str = '5m', limit: int = 100) -> Optional[pd.DataFrame]:
        try:
            url = "https://api.binance.com/api/v3/klines"
            response = requests.get(url, params={
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignored'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['symbol'] = symbol
            return df.sort_values('timestamp')
            
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
        
    def process_market_data(self, symbol: str) -> None:
        df = self.get_binance_data(symbol)
        if df is None:
            return
            
        indicators = self.analyzer.calculate_indicators(df)
        signal = self.analyzer.analyze_market(df, indicators)
        
        if signal and signal.confidence > 0.6:
            self.notifier.send_signal(signal)
            
            if symbol not in self.monitored_pairs:
                self.monitored_pairs[symbol] = MarketState(
                    symbol=symbol,
                    start_time=datetime.now(),
                    current_price=signal.price,
                    entry_points=[signal.entry],
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    signal_type=signal.signal_type
                )

    def check_market_updates(self) -> None:
        """Check for market updates in the webpage"""
        try:
            table = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))
            rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 2:
                    symbol = f"{cols[0].text}USDT"
                    pings = int(cols[1].text)
                    
                    if pings >= 4:
                        self.process_market_data(symbol)
            
            # Clean up old notifications
            self.notifier.cleanup_old_notifications()
                    
        except Exception as e:
            logging.error(f"Error checking market updates: {str(e)}")
            raise

    def run(self) -> None:
        """Main execution loop"""
        try:
            self.driver.get("https://agile-cliffs-23967.herokuapp.com/binance")
            self.notifier.bot.send_message("🤖 Trading Bot Started")
            
            while True:
                try:
                    self.check_market_updates()
                    time.sleep(60)  # Wait 60 seconds between checks
                    
                except Exception as e:
                    logging.error(f"Error in main loop: {str(e)}")
                    time.sleep(5)  # Short delay before retry
                    
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
        except Exception as e:
            logging.error(f"Fatal error in run method: {str(e)}")
            raise
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()

    def __del__(self):
        """Cleanup method"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")
# Main execution
if __name__ == "__main__":
    try:
        # Configure logging
        setup_logging()
        
        # Telegram credentials
        TELEGRAM_TOKEN = "8128618696:AAFYD-LPrR6jZXkkx4y7TnJoZqymjBeJqIg"
        TELEGRAM_CHAT_ID = "6347487922"
        
        # Initialize the notification system
        notifier = TradingNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        
        # Initialize and run the monitor
        monitor = CryptoMonitor(notifier)
        monitor.run()
        
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error occurred: {str(e)}")
        raise
