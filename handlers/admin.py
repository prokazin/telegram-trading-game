from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from database import get_db, User, Position
from utils import calculate_rankings
from config import Config
import pandas as pd
import io

class AdminHandler:
    @staticmethod
    async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню администратора"""
        user_id = update.effective_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ У вас нет доступа к админ-панели")
            return
        
        text = """
⚙️ Панель администратора

Выберите действие:
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика бота", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Управление пользователями", callback_data='admin_users')],
            [InlineKeyboardButton("📈 Обновить рейтинги", callback_data='admin_update_ranks')],
            [InlineKeyboardButton("🔄 Пересчитать балансы", callback_data='admin_recalc_balances')],
            [InlineKeyboardButton("📤 Экспорт данных", callback_data='admin_export')],
            [InlineKeyboardButton("🔙 Назад", callback_data='back_main')]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    @staticmethod
    async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика бота"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await query.answer("⛔ Нет доступа")
            return
        
        db = next(get_db())
        
        # Собираем статистику
        total_users = db.query(User).count()
        active_users = db.query(User).filter(
            User.last_active >= datetime.utcnow() - timedelta(days=1)
        ).count()
        
        total_positions = db.query(Position).count()
        open_positions = db.query(Position).filter(Position.is_open == True).count()
        
        total_volume = db.query(Position).filter(Position.is_open == False).with_entities(
            db.func.sum(Position.amount * Position.entry_price * Position.leverage)
        ).scalar() or 0
        
        total_profit = db.query(User).with_entities(
            db.func.sum(User.total_profit)
        ).scalar() or 0
        
        stats_text = f"""
📊 Статистика бота:

👥 Пользователи:
• Всего: {total_users}
• Активных (24ч): {active_users}

📈 Торговля:
• Всего позиций: {total_positions}
• Открытых: {open_positions}
• Объем торгов: ${total_volume:,.2f}
• Общий PnL: ${total_profit:,.2f}

💼 Средние показатели:
• Средний баланс: ${(total_users > 0) and (db.query(db.func.avg(User.balance)).scalar() or 0):.2f}
• Средний винрейт: {(total_users > 0) and (db.query(db.func.avg(User.win_rate)).scalar() or 0):.1f}%
• Среднее плечо: {(open_positions > 0) and (db.query(db.func.avg(Position.leverage)).filter(Position.is_open == True).scalar() or 0):.1f}x
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data='admin_stats')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_menu')]
        ]
        
        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    @staticmethod
    async def admin_update_ranks(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обновление рейтингов"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await query.answer("⛔ Нет доступа")
            return
        
        db = next(get_db())
        
        # Обновляем рейтинги
        calculate_rankings(db)
        
        await query.answer("✅ Рейтинги обновлены")
    
    @staticmethod
    async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экспорт данных"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await query.answer("⛔ Нет доступа")
            return
        
        db = next(get_db())
        
        # Экспорт пользователей
        users = db.query(User).all()
        users_data = []
        for user in users:
            users_data.append({
                'ID': user.id,
                'Telegram ID': user.telegram_id,
                'Username': user.username,
                'Balance': user.balance,
                'Total Profit': user.total_profit,
                'Total Trades': user.total_trades,
                'Win Rate': user.win_rate,
                'Rank': user.rank,
                'Registered': user.registered_at,
                'Last Active': user.last_active
            })
        
        users_df = pd.DataFrame(users_data)
        
        # Экспорт позиций
        positions = db.query(Position).all()
        positions_data = []
        for pos in positions:
            positions_data.append({
                'ID': pos.id,
                'User ID': pos.user_id,
                'Symbol': pos.symbol,
                'Type': pos.position_type.value,
                'Leverage': pos.leverage,
                'Entry Price': pos.entry_price,
                'Current Price': pos.current_price,
                'Amount': pos.amount,
                'Margin': pos.margin,
                'Unrealized PnL': pos.unrealized_pnl,
                'Realized PnL': pos.realized_pnl,
                'Liquidation Price': pos.liquidation_price,
                'Stop Loss': pos.stop_loss,
                'Take Profit': pos.take_profit,
                'Is Open': pos.is_open,
                'Opened At': pos.opened_at,
                'Closed At': pos.closed_at
            })
        
        positions_df = pd.DataFrame(positions_data)
        
        # Создаем Excel файл с несколькими листами
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            users_df.to_excel(writer, sheet_name='Users', index=False)
            positions_df.to_excel(writer, sheet_name='Positions', index=False)
        
        output.seek(0)
        
        # Отправляем файл
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=output,
            filename='trading_game_data.xlsx',
            caption='📊 Экспорт данных бота'
        )
        
        await query.answer("Файл отправлен")
    
    @staticmethod
    def get_handlers():
        """Возвращает обработчики"""
        return [
            CommandHandler('admin', AdminHandler.admin_menu),
            CallbackQueryHandler(AdminHandler.admin_menu, pattern='^admin_menu$'),
            CallbackQueryHandler(AdminHandler.admin_stats, pattern='^admin_stats$'),
            CallbackQueryHandler(AdminHandler.admin_update_ranks, pattern='^admin_update_ranks$'),
            CallbackQueryHandler(AdminHandler.admin_export, pattern='^admin_export$')
        ]
