from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from database import get_db, User, Position, Order, OrderType, OrderSide, PositionType
from crypto_data import crypto_data
from keyboards import TradingKeyboards
from utils import validate_trade_amount, format_price
from datetime import datetime
import re

class TradingHandler:
    def __init__(self):
        self.temp_data = {}  # Временное хранение данных для многошаговых операций
    
    async def trade_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню торговли"""
        keyboard = TradingKeyboards.trade_menu()
        await update.callback_query.edit_message_text(
            text="📈 Выберите действие:",
            reply_markup=keyboard
        )
    
    async def select_coin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор монеты"""
        query = update.callback_query
        data = query.data
        
        if data.startswith('open_'):
            position_type = data.replace('open_', '')
            self.temp_data[query.from_user.id] = {'position_type': position_type}
            
            keyboard = TradingKeyboards.coins_menu('select_coin')
            await query.edit_message_text(
                text=f"Вы выбрали {position_type.upper()}\n\nВыберите монету:",
                reply_markup=keyboard
            )
    
    async def process_coin_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора монеты"""
        query = update.callback_query
        data = query.data
        
        if data.startswith('select_coin_'):
            symbol = data.replace('select_coin_', '')
            user_data = self.temp_data.get(query.from_user.id, {})
            user_data['symbol'] = symbol
            
            self.temp_data[query.from_user.id] = user_data
            
            current_price = crypto_data.get_current_price(symbol)
            price_text = format_price(current_price)
            
            keyboard = TradingKeyboards.leverage_menu(symbol, user_data['position_type'])
            await query.edit_message_text(
                text=f"📊 {symbol}\nТекущая цена: {price_text}\n\nВыберите плечо:",
                reply_markup=keyboard
            )
    
    async def process_leverage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора плеча"""
        query = update.callback_query
        data = query.data
        
        if data.startswith('lev_'):
            _, symbol, position_type, leverage_str = data.split('_')
            leverage = int(leverage_str)
            
            user_data = self.temp_data.get(query.from_user.id, {})
            user_data['leverage'] = leverage
            self.temp_data[query.from_user.id] = user_data
            
            current_price = crypto_data.get_current_price(symbol)
            price_text = format_price(current_price)
            
            keyboard = TradingKeyboards.order_type_menu(symbol, position_type, leverage)
            await query.edit_message_text(
                text=f"📊 {symbol}\nЦена: {price_text}\nПлечо: {leverage}x\n\nВыберите тип ордера:",
                reply_markup=keyboard
            )
    
    async def process_order_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка типа ордера"""
        query = update.callback_query
        data = query.data
        
        if data.startswith('market_'):
            _, symbol, position_type, leverage_str = data.split('_')
            leverage = int(leverage_str)
            
            user_data = {
                'symbol': symbol,
                'position_type': position_type,
                'leverage': leverage,
                'order_type': 'market'
            }
            self.temp_data[query.from_user.id] = user_data
            
            current_price = crypto_data.get_current_price(symbol)
            price_text = format_price(current_price)
            
            text = f"""
📊 Рыночный ордер

Монета: {symbol}
Направление: {position_type.upper()}
Плечо: {leverage}x
Текущая цена: {price_text}

Введите сумму в USDT (мин. $10):
Пример: 100 или 50.5
            """
            
            await query.edit_message_text(text=text)
            context.user_data['awaiting_amount'] = True
    
    async def process_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода суммы"""
        if not context.user_data.get('awaiting_amount'):
            return
        
        try:
            amount = float(update.message.text)
            user_id = update.effective_user.id
            user_data = self.temp_data.get(user_id, {})
            
            if not user_data:
                await update.message.reply_text("Сессия истекла. Начните заново.")
                return
            
            # Проверяем баланс пользователя
            db = next(get_db())
            db_user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if not db_user:
                await update.message.reply_text("Пользователь не найден. Используйте /start")
                return
            
            # Проверяем сумму
            if not validate_trade_amount(amount, db_user.balance, user_data['leverage']):
                await update.message.reply_text(
                    f"❌ Недостаточно средств или сумма меньше ${10}\n"
                    f"Ваш баланс: ${db_user.balance:.2f}\n"
                    f"Мин. сумма: ${10}"
                )
                return
            
            # Проверяем максимальное количество позиций
            open_positions = db.query(Position).filter(
                Position.user_id == db_user.id,
                Position.is_open == True
            ).count()
            
            if open_positions >= 5:
                await update.message.reply_text("❌ У вас уже 5 открытых позиций. Закройте некоторые.")
                return
            
            # Создаем позицию
            symbol = user_data['symbol']
            current_price = crypto_data.get_current_price(symbol)
            
            # Расчет маржи
            margin = amount * user_data['leverage'] / 10
            
            # Расчет цены ликвидации
            liquidation_price = crypto_data.calculate_liquidation_price(
                current_price,
                user_data['leverage'],
                user_data['position_type'],
                margin
            )
            
            position = Position(
                user_id=db_user.id,
                symbol=symbol,
                position_type=PositionType.LONG if user_data['position_type'] == 'long' else PositionType.SHORT,
                entry_price=current_price,
                current_price=current_price,
                amount=amount,
                leverage=user_data['leverage'],
                margin=margin,
                liquidation_price=liquidation_price,
                is_open=True,
                opened_at=datetime.utcnow()
            )
            
            # Обновляем баланс пользователя
            db_user.balance -= margin
            
            db.add(position)
            db.commit()
            
            # Форматируем цены
            entry_text = format_price(current_price)
            liq_text = format_price(liquidation_price)
            
            success_text = f"""
✅ Позиция открыта!

📊 Детали:
• Монета: {symbol}
• Направление: {user_data['position_type'].upper()}
• Плечо: {user_data['leverage']}x
• Сумма: ${amount:.2f}
• Цена входа: {entry_text}
• Маржа: ${margin:.2f}
• Ликвидация: {liq_text}

💰 Новый баланс: ${db_user.balance:.2f}
📈 Следите за позицией в разделе "Мои позиции"
            """
            
            await update.message.reply_text(success_text)
            
            # Сбрасываем состояние
            context.user_data['awaiting_amount'] = False
            if user_id in self.temp_data:
                del self.temp_data[user_id]
                
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректное число")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            context.user_data['awaiting_amount'] = False
    
    async def my_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать открытые позиции"""
        query = update.callback_query
        user_id = query.from_user.id
        
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not db_user:
            await query.answer("Пользователь не найден")
            return
        
        positions = db.query(Position).filter(
            Position.user_id == db_user.id,
            Position.is_open == True
        ).all()
        
        if not positions:
            text = "📭 У вас нет открытых позиций"
            keyboard = TradingKeyboards.back_button('trade')
        else:
            text = "📊 Ваши открытые позиции:\n\n"
            
            for pos in positions:
                pnl = crypto_data.calculate_pnl(
                    pos.entry_price,
                    pos.current_price,
                    pos.amount,
                    pos.leverage,
                    pos.position_type.value
                )
                
                pnl_percent = (pnl / pos.margin) * 100
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                
                text += f"""
{pos.symbol} {pos.position_type.value.upper()} {pos.leverage}x
{pnl_emoji} PnL: ${pnl:.2f} ({pnl_percent:+.1f}%)
💰 Маржа: ${pos.margin:.2f}
🎯 Вход: ${pos.entry_price:.2f}
📊 Текущая: ${pos.current_price:.2f}
🛑 Ликвидация: ${pos.liquidation_price:.2f}
                """
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data='back_trade')
            ]])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    def get_handlers(self):
        """Возвращает обработчики"""
        return [
            CallbackQueryHandler(self.trade_menu, pattern='^trade$'),
            CallbackQueryHandler(self.select_coin, pattern='^open_(long|short)$'),
            CallbackQueryHandler(self.process_coin_selection, pattern='^select_coin_'),
            CallbackQueryHandler(self.process_leverage, pattern='^lev_'),
            CallbackQueryHandler(self.process_order_type, pattern='^(market|limit)_'),
            CallbackQueryHandler(self.my_positions, pattern='^my_positions$'),
            CallbackQueryHandler(self.trade_menu, pattern='^back_trade$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_amount)
        ]
