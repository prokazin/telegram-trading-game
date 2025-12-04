import unittest
from database import init_db, SessionLocal, User, Position
from crypto_data import CryptoData
from utils import validate_trade_amount, calculate_liquidation_price
from config import Config

class TestTradingGame(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестовой среды"""
        init_db()
        self.db = SessionLocal()
        self.crypto_data = CryptoData()
    
    def tearDown(self):
        """Очистка после тестов"""
        self.db.close()
    
    def test_initial_balance(self):
        """Проверка начального баланса"""
        user = User(
            telegram_id=123456,
            username="test_user",
            first_name="Test",
            last_name="User",
            balance=Config.INITIAL_BALANCE
        )
        self.db.add(user)
        self.db.commit()
        
        self.assertEqual(user.balance, 2000.0)
    
    def test_validate_trade_amount(self):
        """Проверка валидации суммы сделки"""
        # Тест с достаточным балансом
        self.assertTrue(validate_trade_amount(100, 1000, 2))
        
        # Тест с недостаточным балансом
        self.assertFalse(validate_trade_amount(1000, 100, 10))
        
        # Тест с минимальной суммой
        self.assertFalse(validate_trade_amount(5, 1000, 2))  # Меньше $10
        self.assertTrue(validate_trade_amount(10, 1000, 2))  # Ровно $10
    
    def test_liquidation_price_calculation(self):
        """Проверка расчета цены ликвидации"""
        # Тест для лонга
        entry_price = 50000
        leverage = 10
        position_type = 'long'
        margin = 100
        
        liq_price = self.crypto_data.calculate_liquidation_price(
            entry_price, leverage, position_type, margin
        )
        
        # Проверяем что цена ликвидации ниже цены входа
        self.assertLess(liq_price, entry_price)
        
        # Тест для шорта
        position_type = 'short'
        liq_price = self.crypto_data.calculate_liquidation_price(
            entry_price, leverage, position_type, margin
        )
        
        # Проверяем что цена ликвидации выше цены входа
        self.assertGreater(liq_price, entry_price)
    
    def test_pnl_calculation(self):
        """Проверка расчета PnL"""
        # Тест для лонга с прибылью
        entry_price = 50000
        current_price = 51000
        amount = 1
        leverage = 2
        position_type = 'long'
        
        pnl = self.crypto_data.calculate_pnl(
            entry_price, current_price, amount, leverage, position_type
        )
        
        # Расчет вручную: (51000 - 50000) * 1 * 2 = 2000
        self.assertEqual(pnl, 2000)
        
        # Тест для шорта с убытком
        position_type = 'short'
        pnl = self.crypto_data.calculate_pnl(
            entry_price, current_price, amount, leverage, position_type
        )
        
        # Расчет вручную: (50000 - 51000) * 1 * 2 = -2000
        self.assertEqual(pnl, -2000)
    
    def test_available_coins(self):
        """Проверка доступных монет"""
        self.assertIn('BTC/USDT', Config.AVAILABLE_COINS)
        self.assertIn('ETH/USDT', Config.AVAILABLE_COINS)
        self.assertIn('BNB/USDT', Config.AVAILABLE_COINS)
        self.assertEqual(len(Config.AVAILABLE_COINS), 3)
    
    def test_leverage_options(self):
        """Проверка доступных плечей"""
        self.assertIn(2, Config.LEVERAGE_OPTIONS)
        self.assertIn(5, Config.LEVERAGE_OPTIONS)
        self.assertIn(10, Config.LEVERAGE_OPTIONS)
    
    def test_max_open_positions(self):
        """Проверка максимального количества открытых позиций"""
        self.assertEqual(Config.MAX_OPEN_POSITIONS, 5)

if __name__ == '__main__':
    unittest.main()
