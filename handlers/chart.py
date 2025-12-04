from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from crypto_data import crypto_data
from chart_generator import ChartGenerator
from keyboards import TradingKeyboards
from database import get_db, Position
from utils import format_price
import io

class ChartHandler:
    @staticmethod
    async def chart_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню графиков"""
        query = update.callback_query
        
        text = """
📊 Анализ графиков

Выберите монету для просмотра графика:
        """
        
        keyboard = TradingKeyboards.coins_menu('chart')
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
    
    @staticmethod
    async def show_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать график"""
        query = update.callback_query
        
        if query.data.startswith('chart_'):
            _, symbol, timeframe = query.data.split('_')
            
            # Получаем исторические данные
            df = crypto_data.get_historical_data(symbol, timeframe)
            
            if df.empty:
                await query.answer("Не удалось получить данные")
                return
            
            # Получаем текущую цену
            current_price = crypto_data.get_current_price(symbol)
            
            # Проверяем есть ли у пользователя открытая позиция по этой монете
            db = next(get_db())
            user_positions = db.query(Position).filter(
                Position.user_id == query.from_user.id,
                Position.symbol == symbol,
                Position.is_open == True
            ).first()
            
            entry_price = None
            stop_loss = None
            take_profit = None
            
            if user_positions:
                entry_price = user_positions.entry_price
                stop_loss = user_positions.stop_loss
                take_profit = user_positions.take_profit
            
            # Генерируем график
            chart_buffer = ChartGenerator.create_price_chart(
                df,
                symbol,
                entry_price,
                stop_loss,
                take_profit,
                current_price
            )
            
            # Подготавливаем текст
            price_text = format_price(current_price)
            
            chart_text = f"""
📊 {symbol}
Таймфрейм: {timeframe}
Текущая цена: {price_text}

            """
            
            if user_positions:
                pnl = crypto_data.calculate_pnl(
                    user_positions.entry_price,
                    current_price,
                    user_positions.amount,
                    user_positions.leverage,
                    user_positions.position_type.value
                )
                
                pnl_percent = (pnl / user_positions.margin) * 100 if user_positions.margin > 0 else 0
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                
                chart_text += f"""
{pnl_emoji} Ваш PnL: ${pnl:.2f} ({pnl_percent:+.1f}%)
🎯 Ваш вход: ${user_positions.entry_price:.2f}
                """
            
            # Отправляем график
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=chart_buffer,
                caption=chart_text
            )
            
            # Показываем меню выбора таймфрейма
            keyboard = TradingKeyboards.timeframe_menu(symbol)
            await query.edit_message_text(
                text=f"Выберите таймфрейм для {symbol}:",
                reply_markup=keyboard
            )
    
    @staticmethod
    async def show_position_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать график для конкретной позиции"""
        query = update.callback_query
        
        if query.data.startswith('position_chart_'):
            position_id = int(query.data.replace('position_chart_', ''))
            
            db = next(get_db())
            position = db.query(Position).filter(
                Position.id == position_id,
                Position.user_id == query.from_user.id
            ).first()
            
            if not position:
                await query.answer("Позиция не найдена")
                return
            
            # Получаем данные для графика
            df = crypto_data.get_historical_data(position.symbol, '15m')
            
            if df.empty:
                await query.answer("Не удалось получить данные")
                return
            
            # Расчет PnL
            current_price = crypto_data.get_current_price(position.symbol)
            pnl = crypto_data.calculate_pnl(
                position.entry_price,
                current_price,
                position.amount,
                position.leverage,
                position.position_type.value
            )
            
            # Генерируем график
            chart_buffer = ChartGenerator.create_price_chart(
                df,
                position.symbol,
                position.entry_price,
                position.stop_loss,
                position.take_profit,
                current_price
            )
            
            # Подготавливаем текст
            pnl_percent = (pnl / position.margin) * 100 if position.margin > 0 else 0
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            chart_text = f"""
📊 {position.symbol} {position.position_type.value.upper()} {position.leverage}x

{pnl_emoji} PnL: ${pnl:.2f} ({pnl_percent:+.1f}%)
💰 Маржа: ${position.margin:.2f}
🎯 Вход: ${position.entry_price:.2f}
📊 Текущая: ${current_price:.2f}
🛑 Ликвидация: ${position.liquidation_price:.2f}
            """
            
            if position.stop_loss:
                chart_text += f"\n⛔ Стоп-лосс: ${position.stop_loss:.2f}"
            if position.take_profit:
                chart_text += f"\n🎯 Тейк-профит: ${position.take_profit:.2f}"
            
            # Отправляем график
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=chart_buffer,
                caption=chart_text
            )
            
            await query.answer("График отправлен")
    
    @staticmethod
    async def pnl_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """График истории PnL"""
        query = update.callback_query
        user_id = query.from_user.id
        
        db = next(get_db())
        
        # Получаем историю PnL пользователя
        positions = db.query(Position).filter(
            Position.user_id == user_id
        ).order_by(Position.opened_at).all()
        
        if not positions:
            await query.answer("Нет данных для графика")
            return
        
        # Собираем историю PnL
        pnl_history = []
        current_pnl = 0
        
        for pos in positions:
            if pos.is_open:
                pnl = crypto_data.calculate_pnl(
                    pos.entry_price,
                    crypto_data.get_current_price(pos.symbol),
                    pos.amount,
                    pos.leverage,
                    pos.position_type.value
                )
                current_pnl += pnl
            else:
                current_pnl += pos.realized_pnl
            
            pnl_history.append(current_pnl)
        
        # Генерируем график
        if len(pnl_history) < 2:
            pnl_history = [0, current_pnl]  # Минимум 2 точки
        
        chart_buffer = ChartGenerator.create_pnl_chart(pnl_history)
        
        # Отправляем график
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=chart_buffer,
            caption="📉 История вашего PnL"
        )
        
        await query.answer("График отправлен")
    
    @staticmethod
    def get_handlers():
        """Возвращает обработчики"""
        return [
            CallbackQueryHandler(ChartHandler.chart_menu, pattern='^chart$'),
            CallbackQueryHandler(ChartHandler.show_chart, pattern='^chart_'),
            CallbackQueryHandler(ChartHandler.show_position_chart, pattern='^position_chart_'),
            CallbackQueryHandler(ChartHandler.pnl_chart, pattern='^pnl_chart$'),
            CallbackQueryHandler(ChartHandler.chart_menu, pattern='^back_chart$')
        ]
