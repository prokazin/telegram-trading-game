import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import init_db
from crypto_data import crypto_data
from utils import check_liquidations
from handlers.start import StartHandler
from handlers.trading import TradingHandler
from handlers.portfolio import PortfolioHandler
from handlers.chart import ChartHandler
from handlers.admin import AdminHandler
from config import Config
import asyncio
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None
        
    async def check_liquidations_task(self, context):
        """Фоновая задача проверки ликвидаций"""
        db = next(get_db())
        liquidated = check_liquidations(db, crypto_data)
        
        if liquidated:
            for position in liquidated:
                try:
                    # Уведомляем пользователя о ликвидации
                    await context.bot.send_message(
                        chat_id=position.user.telegram_id,
                        text=f"""
⚠️ ЛИКВИДАЦИЯ!

Ваша позиция была ликвидирована:

📊 {position.symbol} {position.position_type.value.upper()} {position.leverage}x
💰 Потеряно: ${position.margin:.2f}
🎯 Цена входа: ${position.entry_price:.2f}
📊 Цена ликвидации: ${position.liquidation_price:.2f}

💸 Новый баланс: ${position.user.balance:.2f}

⚠️ Снизьте плечо для уменьшения рисков!
                        """
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user about liquidation: {e}")
        
        # Перезапускаем задачу через 30 секунд
        await asyncio.sleep(30)
        asyncio.create_task(self.check_liquidations_task(context))
    
    async def update_prices_task(self, context):
        """Фоновая задача обновления цен"""
        while True:
            try:
                crypto_data.update_prices()
                
                # Обновляем PnL открытых позиций
                db = next(get_db())
                positions = db.query(Position).filter(Position.is_open == True).all()
                
                for position in positions:
                    current_price = crypto_data.get_current_price(position.symbol)
                    position.current_price = current_price
                    position.unrealized_pnl = crypto_data.calculate_pnl(
                        position.entry_price,
                        current_price,
                        position.amount,
                        position.leverage,
                        position.position_type.value
                    )
                
                db.commit()
                
            except Exception as e:
                logger.error(f"Error in update_prices_task: {e}")
            
            await asyncio.sleep(60)  # Обновляем каждую минуту
    
    def setup_handlers(self):
        """Настройка обработчиков"""
        # Создаем экземпляры хэндлеров
        start_handler = StartHandler()
        trading_handler = TradingHandler()
        portfolio_handler = PortfolioHandler()
        chart_handler = ChartHandler()
        admin_handler = AdminHandler()
        
        # Регистрируем обработчики
        self.application.add_handlers([
            # Команды
            *start_handler.get_handlers(),
            
            # Торговля
            *trading_handler.get_handlers(),
            
            # Портфель
            *portfolio_handler.get_handlers(),
            
            # Графики
            *chart_handler.get_handlers(),
            
            # Админ
            *admin_handler.get_handlers(),
            
            # Обработка кнопки назад для главного меню
            CallbackQueryHandler(start_handler.start, pattern='^back_main$'),
        ])
    
    async def post_init(self, application):
        """Выполняется после инициализации бота"""
        # Запускаем обновление цен
        crypto_data.start_updates()
        
        # Запускаем фоновые задачи
        asyncio.create_task(self.check_liquidations_task(application))
        asyncio.create_task(self.update_prices_task(application))
        
        logger.info("Bot initialized and background tasks started")
    
    async def post_stop(self, application):
        """Выполняется при остановке бота"""
        crypto_data.stop_updates()
        logger.info("Bot stopped")
    
    def run(self):
        """Запуск бота"""
        # Инициализация базы данных
        init_db()
        
        # Создание приложения
        self.application = Application.builder().token(self.token).post_init(self.post_init).post_stop(self.post_stop).build()
        
        # Настройка обработчиков
        self.setup_handlers()
        
        # Запуск бота
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    # Проверка токена
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Создание и запуск бота
    bot = TradingBot(Config.BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()
