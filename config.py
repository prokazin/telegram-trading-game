import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot settings
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    
    # Trading settings
    INITIAL_BALANCE = 2000.0  # USD
    AVAILABLE_COINS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
    LEVERAGE_OPTIONS = [2, 5, 10]
    MAINTENANCE_MARGIN = 0.005  # 0.5% для ликвидации
    
    # Chart settings
    CHART_TIME_FRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
    DEFAULT_TIME_FRAME = '1h'
    CHART_PERIODS = 100
    
    # Game settings
    MIN_TRADE_AMOUNT = 10.0  # Минимальная сумма сделки
    UPDATE_INTERVAL = 60  # Обновление данных каждые 60 секунд
    MAX_OPEN_POSITIONS = 5  # Максимальное количество открытых позиций
    
    # Database
    DATABASE_URL = 'sqlite:///trading_game.db'
