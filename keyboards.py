from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import Config

class TradingKeyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [InlineKeyboardButton("📈 Торговать", callback_data='trade')],
            [InlineKeyboardButton("💰 Портфель", callback_data='portfolio')],
            [InlineKeyboardButton("📊 График", callback_data='chart')],
            [InlineKeyboardButton("🏆 Рейтинг", callback_data='leaderboard')],
            [InlineKeyboardButton("📋 История", callback_data='history')],
            [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def trade_menu() -> InlineKeyboardMarkup:
        """Меню торговли"""
        keyboard = [
            [InlineKeyboardButton("🟢 Открыть LONG", callback_data='open_long'),
             InlineKeyboardButton("🔴 Открыть SHORT", callback_data='open_short')],
            [InlineKeyboardButton("📊 Мои позиции", callback_data='my_positions'),
             InlineKeyboardButton("❌ Закрыть позицию", callback_data='close_position')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def coins_menu(action: str = 'trade') -> InlineKeyboardMarkup:
        """Выбор монеты"""
        keyboard = []
        for coin in Config.AVAILABLE_COINS:
            symbol = coin.split('/')[0]
            keyboard.append([InlineKeyboardButton(
                f"{symbol}", 
                callback_data=f"{action}_{coin}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_trade')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def leverage_menu(symbol: str, position_type: str) -> InlineKeyboardMarkup:
        """Выбор плеча"""
        keyboard = []
        for leverage in Config.LEVERAGE_OPTIONS:
            keyboard.append([InlineKeyboardButton(
                f"{leverage}x", 
                callback_data=f"lev_{symbol}_{position_type}_{leverage}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f'back_coins_{position_type}')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def order_type_menu(symbol: str, position_type: str, leverage: int) -> InlineKeyboardMarkup:
        """Тип ордера"""
        keyboard = [
            [InlineKeyboardButton("🎯 Рыночный ордер", 
             callback_data=f"market_{symbol}_{position_type}_{leverage}")],
            [InlineKeyboardButton("📊 Лимитный ордер", 
             callback_data=f"limit_{symbol}_{position_type}_{leverage}")],
            [InlineKeyboardButton("🔙 Назад", 
             callback_data=f'back_leverage_{symbol}_{position_type}')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def position_actions(position_id: int) -> InlineKeyboardMarkup:
        """Действия с позицией"""
        keyboard = [
            [InlineKeyboardButton("🛑 Установить SL/TP", 
             callback_data=f"set_sltp_{position_id}")],
            [InlineKeyboardButton("📊 Обновить график", 
             callback_data=f"update_chart_{position_id}")],
            [InlineKeyboardButton("❌ Закрыть позицию", 
             callback_data=f"close_{position_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_positions')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def timeframe_menu(symbol: str) -> InlineKeyboardMarkup:
        """Выбор таймфрейма для графика"""
        keyboard = []
        row = []
        for i, tf in enumerate(Config.CHART_TIME_FRAMES):
            row.append(InlineKeyboardButton(tf, callback_data=f"chart_{symbol}_{tf}"))
            if (i + 1) % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='back_main')])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def confirm_close(position_id: int) -> InlineKeyboardMarkup:
        """Подтверждение закрытия позиции"""
        keyboard = [
            [InlineKeyboardButton("✅ Да, закрыть", callback_data=f"confirm_close_{position_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_close_{position_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(to: str) -> InlineKeyboardMarkup:
        """Кнопка назад"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f'back_{to}')]]
        return InlineKeyboardMarkup(keyboard)
