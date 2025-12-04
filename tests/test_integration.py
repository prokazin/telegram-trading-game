import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Chat, User as TelegramUser
from telegram.ext import CallbackContext
from handlers.trading import TradingHandler
from database import SessionLocal, User, Position
from crypto_data import CryptoData

class TestTradingIntegration(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестовой среды"""
        self.db = SessionLocal()
        self.handler = TradingHandler()
        
        # Создаем тестового пользователя
        self.test_user = User(
            telegram_id=999999,
            username="test_user",
            first_name="Test",
            last_name="User",
            balance=2000.0
        )
        self.db.add(self.test_user)
        self.db.commit()
        
        # Мок для update и context
        self.update = AsyncMock(spec=Update)
        self.context = AsyncMock(spec=CallbackContext)
        
        # Мок для callback query
        self.callback_query = AsyncMock()
        self.callback_query.from_user.id = 999999
        self.callback_query.data = ''
        self.callback_query.edit_message_text = AsyncMock()
        self.callback_query.answer = AsyncMock()
        
        self.update.callback_query = self.callback_query
    
    def tearDown(self):
        """Очистка после тестов"""
        self.db.query(Position).delete()
        self.db.query(User).delete()
        self.db.commit()
        self.db.close()
    
    @patch('handlers.trading.crypto_data')
    async def test_open_position_flow(self, mock_crypto_data):
        """Тест полного цикла открытия позиции"""
        # Мок текущей цены
        mock_crypto_data.get_current_price.return_value = 50000.0
        
        # Мок расчета ликвидации
        mock_crypto_data.calculate_liquidation_price.return_value = 45000.0
        
        # Тестируем выбор монеты
        self.callback_query.data = 'open_long'
        await self.handler.select_coin(self.update, self.context)
        
        # Проверяем что сообщение обновилось
        self.callback_query.edit_message_text.assert_called()
        
        # Тестируем выбор плеча
        self.callback_query.data = 'lev_BTC/USDT_long_10'
        await self.handler.process_leverage(self.update, self.context)
        
        # Тестируем выбор типа ордера
        self.callback_query.data = 'market_BTC/USDT_long_10'
        await self.handler.process_order_type(self.update, self.context)
        
        # Проверяем что запросили ввод суммы
        self.callback_query.edit_message_text.assert_called()
        
        # Тестируем обработку ввода суммы
        self.context.user_data['awaiting_amount'] = True
        
        # Создаем мок для сообщения
        message = AsyncMock()
        message.text = "100"
        self.update.message = message
        self.update.effective_user.id = 999999
        
        # Мок для базы данных
        with patch('handlers.trading.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            # Мок для query
            mock_query = MagicMock()
            mock_db.query.return_value = mock_query
            
            # Мок для пользователя
            mock_user = self.test_user
            mock_query.filter.return_value.first.return_value = mock_user
            
            # Мок для позиций
            mock_query.filter.return_value.count.return_value = 0
            
            await self.handler.process_amount(self.update, self.context)
            
            # Проверяем что позиция была создана
            self.assertTrue(mock_db.add.called)
            self.assertTrue(mock_db.commit.called)
    
    def test_temp_data_storage(self):
        """Тест временного хранения данных"""
        user_id = 123456
        test_data = {
            'position_type': 'long',
            'symbol': 'BTC/USDT',
            'leverage': 10
        }
        
        # Сохраняем данные
        self.handler.temp_data[user_id] = test_data
        
        # Получаем данные
        retrieved_data = self.handler.temp_data.get(user_id)
        
        self.assertEqual(retrieved_data, test_data)
        
        # Удаляем данные
        del self.handler.temp_data[user_id]
        
        self.assertNotIn(user_id, self.handler.temp_data)
    
    def test_position_count_limit(self):
        """Тест лимита открытых позиций"""
        user_id = 999999
        
        # Создаем 5 позиций
        for i in range(5):
            position = Position(
                user_id=self.test_user.id,
                symbol=f"BTC/USDT",
                position_type="long",
                entry_price=50000.0,
                current_price=50000.0,
                amount=100.0,
                leverage=2,
                margin=20.0,
                liquidation_price=45000.0,
                is_open=True
            )
            self.db.add(position)
        
        self.db.commit()
        
        # Проверяем количество открытых позиций
        positions = self.db.query(Position).filter(
            Position.user_id == self.test_user.id,
            Position.is_open == True
        ).count()
        
        self.assertEqual(positions, 5)

# Для запуска асинхронных тестов
if __name__ == '__main__':
    asyncio.run(unittest.main())
