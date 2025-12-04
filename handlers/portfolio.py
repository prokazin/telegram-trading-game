from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import get_db, User, Position, Transaction
from crypto_data import crypto_data
from keyboards import TradingKeyboards
from utils import calculate_portfolio_stats, format_time_delta, format_price, format_percentage
from datetime import datetime
import pandas as pd

class PortfolioHandler:
    @staticmethod
    async def portfolio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню портфеля"""
        query = update.callback_query
        user_id = query.from_user.id
        
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not db_user:
            await query.answer("Пользователь не найден")
            return
        
        # Расчет статистики портфеля
        stats = calculate_portfolio_stats(db_user.id, db)
        
        portfolio_text = f"""
💰 Ваш портфель:

💵 Баланс: ${db_user.balance:.2f}
📊 Общий PnL: ${db_user.total_profit:.2f}
📈 Винрейт: {db_user.win_rate:.1f}%

📈 Открытые позиции: {stats['open_positions']}
💼 Общая стоимость: ${stats['total_value']:.2f}
📉 Нереализованный PnL: ${stats['total_pnl']:.2f}
⚡ Среднее плечо: {stats['average_leverage']:.1f}x

Выберите действие:
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Детали позиций", callback_data='positions_detail')],
            [InlineKeyboardButton("📋 История сделок", callback_data='trade_history')],
            [InlineKeyboardButton("📉 График PnL", callback_data='pnl_chart')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
        ]
        
        await query.edit_message_text(
            text=portfolio_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def positions_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Детали позиций"""
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
        ).order_by(Position.opened_at.desc()).all()
        
        if not positions:
            text = "📭 У вас нет открытых позиций"
        else:
            text = "📊 Ваши открытые позиции:\n\n"
            
            for i, pos in enumerate(positions, 1):
                # Расчет текущего PnL
                pnl = crypto_data.calculate_pnl(
                    pos.entry_price,
                    pos.current_price,
                    pos.amount,
                    pos.leverage,
                    pos.position_type.value
                )
                
                pnl_percent = (pnl / pos.margin) * 100 if pos.margin > 0 else 0
                pnl_emoji = "🟢" if pnl >= 0 else "🔴"
                position_emoji = "🟢" if pos.position_type.value == 'long' else "🔴"
                time_open = format_time_delta(pos.opened_at)
                
                # Расчет до ликвидации
                if pos.position_type.value == 'long':
                    liq_distance = ((pos.current_price - pos.liquidation_price) / pos.current_price) * 100
                else:
                    liq_distance = ((pos.liquidation_price - pos.current_price) / pos.current_price) * 100
                
                text += f"""
{i}. {position_emoji} {pos.symbol} {pos.position_type.value.upper()} {pos.leverage}x
   {pnl_emoji} PnL: ${pnl:.2f} ({pnl_percent:+.1f}%)
   💰 Маржа: ${pos.margin:.2f}
   🎯 Вход: ${pos.entry_price:.2f}
   📊 Текущая: ${pos.current_price:.2f}
   ⚠️ До ликвидации: {liq_distance:.1f}%
   ⏰ Открыта: {time_open}
   
   ID: {pos.id}
                """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='positions_detail')],
            [InlineKeyboardButton("📈 График позиции", callback_data='position_chart')],
            [InlineKeyboardButton("🔙 Назад", callback_data='portfolio')]
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """История сделок"""
        query = update.callback_query
        user_id = query.from_user.id
        
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not db_user:
            await query.answer("Пользователь не найден")
            return
        
        # Получаем закрытые позиции
        closed_positions = db.query(Position).filter(
            Position.user_id == db_user.id,
            Position.is_open == False
        ).order_by(Position.closed_at.desc()).limit(20).all()
        
        # Получаем транзакции
        transactions = db.query(Transaction).filter(
            Transaction.user_id == db_user.id
        ).order_by(Transaction.created_at.desc()).limit(20).all()
        
        text = "📋 История сделок:\n\n"
        
        if not closed_positions and not transactions:
            text += "📭 История пуста"
        else:
            # Закрытые позиции
            if closed_positions:
                text += "🔒 Закрытые позиции:\n"
                for pos in closed_positions[:10]:  # Показываем последние 10
                    pnl_emoji = "🟢" if pos.realized_pnl >= 0 else "🔴"
                    position_emoji = "🟢" if pos.position_type.value == 'long' else "🔴"
                    time_closed = format_time_delta(pos.closed_at) if pos.closed_at else "N/A"
                    
                    text += f"""
{position_emoji} {pos.symbol} {pos.position_type.value.upper()} {pos.leverage}x
{pnl_emoji} PnL: ${pos.realized_pnl:.2f}
💰 Сумма: ${pos.amount:.2f}
⏰ Закрыта: {time_closed}
                    """
            
            # Транзакции
            if transactions:
                text += "\n💰 Транзакции:\n"
                for tx in transactions[:10]:
                    emoji = "🟢" if tx.amount >= 0 else "🔴"
                    tx_type = {
                        'trade': '📊 Торговля',
                        'fee': '💸 Комиссия',
                        'liquidation': '⚠️ Ликвидация'
                    }.get(tx.type, tx.type)
                    
                    text += f"""
{emoji} {tx_type}: ${tx.amount:+.2f}
Баланс: ${tx.balance_after:.2f}
                    """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='trade_history')],
            [InlineKeyboardButton("📤 Экспорт CSV", callback_data='export_history')],
            [InlineKeyboardButton("🔙 Назад", callback_data='portfolio')]
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def export_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экспорт истории в CSV"""
        query = update.callback_query
        user_id = query.from_user.id
        
        db = next(get_db())
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not db_user:
            await query.answer("Пользователь не найден")
            return
        
        # Получаем данные для экспорта
        positions = db.query(Position).filter(
            Position.user_id == db_user.id
        ).all()
        
        # Создаем DataFrame
        data = []
        for pos in positions:
            data.append({
                'ID': pos.id,
                'Symbol': pos.symbol,
                'Type': pos.position_type.value,
                'Leverage': pos.leverage,
                'Entry Price': pos.entry_price,
                'Exit Price': pos.current_price if not pos.is_open else None,
                'Amount': pos.amount,
                'Margin': pos.margin,
                'PnL': pos.realized_pnl if not pos.is_open else pos.unrealized_pnl,
                'Status': 'OPEN' if pos.is_open else 'CLOSED',
                'Opened At': pos.opened_at,
                'Closed At': pos.closed_at
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            await query.answer("Нет данных для экспорта")
            return
        
        # Сохраняем в CSV
        csv_data = df.to_csv(index=False)
        
        # Отправляем файл
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=io.BytesIO(csv_data.encode()),
            filename=f"trading_history_{user_id}.csv",
            caption="📊 Ваша история торговли"
        )
        
        await query.answer("Файл отправлен")
    
    @staticmethod
    def get_handlers():
        """Возвращает обработчики"""
        return [
            CallbackQueryHandler(PortfolioHandler.portfolio_menu, pattern='^portfolio$'),
            CallbackQueryHandler(PortfolioHandler.positions_detail, pattern='^positions_detail$'),
            CallbackQueryHandler(PortfolioHandler.trade_history, pattern='^trade_history$'),
            CallbackQueryHandler(PortfolioHandler.export_history, pattern='^export_history$'),
            CallbackQueryHandler(PortfolioHandler.portfolio_menu, pattern='^back_portfolio$')
        ]
