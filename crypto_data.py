import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import threading
from config import Config

class CryptoData:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        self.prices = {}
        self.historical_data = {}
        self.update_thread = None
        self.running = False
        
    def start_updates(self):
        """Запуск потока обновления цен"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_prices_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def stop_updates(self):
        """Остановка обновления цен"""
        self.running = False
        
    def _update_prices_loop(self):
        """Цикл обновления цен"""
        while self.running:
            try:
                self.update_prices()
                time.sleep(Config.UPDATE_INTERVAL)
            except Exception as e:
                print(f"Error updating prices: {e}")
                time.sleep(30)
                
    def update_prices(self):
        """Обновление текущих цен"""
        for symbol in Config.AVAILABLE_COINS:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                self.prices[symbol] = ticker['last']
            except Exception as e:
                print(f"Error fetching price for {symbol}: {e}")
                
    def get_current_price(self, symbol: str) -> float:
        """Получение текущей цены"""
        return self.prices.get(symbol, 0.0)
    
    def get_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Получение исторических данных"""
        try:
            cache_key = f"{symbol}_{timeframe}"
            
            if cache_key not in self.historical_data or \
               (datetime.now() - self.historical_data[cache_key]['timestamp']).seconds > 300:
                
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Добавляем симуляцию случайных колебаний для более реалистичной игры
                noise = np.random.normal(0, 0.001, len(df))
                df['close'] = df['close'] * (1 + noise)
                
                self.historical_data[cache_key] = {
                    'data': df,
                    'timestamp': datetime.now()
                }
            
            return self.historical_data[cache_key]['data'].copy()
            
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            # Возвращаем фиктивные данные если API недоступно
            return self._generate_mock_data(symbol, timeframe, limit)
    
    def _generate_mock_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Генерация моковых данных если API недоступно"""
        base_prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 2400,
            'BNB/USDT': 300
        }
        
        base_price = base_prices.get(symbol, 100)
        dates = pd.date_range(end=datetime.now(), periods=limit, freq=timeframe.replace('m', 'T').replace('h', 'H'))
        
        np.random.seed(hash(symbol) % 10000)
        returns = np.random.randn(limit) * 0.02
        prices = base_price * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.randn(limit) * 0.01),
            'high': prices * (1 + np.abs(np.random.randn(limit) * 0.02)),
            'low': prices * (1 - np.abs(np.random.randn(limit) * 0.02)),
            'close': prices,
            'volume': np.random.randint(1000, 100000, limit)
        })
        
        return df
    
    def calculate_liquidation_price(self, entry_price: float, leverage: int, position_type: str, margin: float) -> float:
        """Расчет цены ликвидации"""
        if position_type == 'long':
            return entry_price * (1 - (1 / leverage) + Config.MAINTENANCE_MARGIN)
        else:  # short
            return entry_price * (1 + (1 / leverage) - Config.MAINTENANCE_MARGIN)
    
    def calculate_pnl(self, entry_price: float, current_price: float, amount: float, leverage: int, position_type: str) -> float:
        """Расчет PnL"""
        if position_type == 'long':
            pnl = (current_price - entry_price) * amount * leverage
        else:  # short
            pnl = (entry_price - current_price) * amount * leverage
        return pnl

# Глобальный экземпляр
crypto_data = CryptoData()
