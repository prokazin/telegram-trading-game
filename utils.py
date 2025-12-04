from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from models.user import User
from models.position import Position
import numpy as np
from config import Config

def format_price(price: float) -> str:
    """Форматирование цены"""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.2f}"
    else:
        return f"${price:.4f}"

def format_percentage(value: float) -> str:
    """Форматирование процентов"""
    return f"{value:+.2f}%"

def calculate_rankings(db) -> List[Dict]:
    """Расчет рейтинга игроков"""
    users = db.query(User).filter(User.total_trades > 0).all()
    
    ranked_users = []
    for user in users:
        # Расчет рейтингового очка (можно настроить формулу)
        score = (
            user.total_profit * 0.5 +
            user.win_rate * 1000 +
            user.total_trades * 10
        )
        
        ranked_users.append({
            'user': user,
            'score': score
        })
    
    # Сортировка по рейтингу
    ranked_users.sort(key=lambda x: x['score'], reverse=True)
    
    # Обновление рангов
    for i, item in enumerate(ranked_users, 1):
        item['user'].rank = i
    
    db.commit()
    
    return ranked_users[:20]  # Топ 20

def check_liquidations(db, crypto_data):
    """Проверка ликвидаций позиций"""
    positions = db.query(Position).filter(Position.is_open == True).all()
    liquidated = []
    
    for position in positions:
        current_price = crypto_data.get_current_price(position.symbol)
        
        if position.position_type == 'long':
            if current_price <= position.liquidation_price:
                # Ликвидация лонга
                position.is_open = False
                position.closed_at = datetime.utcnow()
                position.current_price = current_price
                position.realized_pnl = -position.margin  # Потеря всей маржи
                liquidated.append(position)
                
                # Обновление баланса пользователя
                position.user.balance = max(0, position.user.balance + position.realized_pnl)
                
        else:  # short
            if current_price >= position.liquidation_price:
                # Ликвидация шорта
                position.is_open = False
                position.closed_at = datetime.utcnow()
                position.current_price = current_price
                position.realized_pnl = -position.margin  # Потеря всей маржи
                liquidated.append(position)
                
                # Обновление баланса пользователя
                position.user.balance = max(0, position.user.balance + position.realized_pnl)
        
        # Обновление текущей цены и PnL
        position.current_price = current_price
        position.unrealized_pnl = crypto_data.calculate_pnl(
            position.entry_price,
            current_price,
            position.amount,
            position.leverage,
            position.position_type.value
        )
    
    db.commit()
    return liquidated

def calculate_portfolio_stats(user_id: int, db) -> Dict[str, Any]:
    """Расчет статистики портфеля"""
    positions = db.query(Position).filter(
        Position.user_id == user_id,
        Position.is_open == True
    ).all()
    
    total_value = 0
    total_pnl = 0
    total_margin = 0
    
    for position in positions:
        total_value += position.amount * position.current_price * position.leverage
        total_pnl += position.unrealized_pnl
        total_margin += position.margin
    
    return {
        'total_value': total_value,
        'total_pnl': total_pnl,
        'total_margin': total_margin,
        'open_positions': len(positions),
        'average_leverage': np.mean([p.leverage for p in positions]) if positions else 0
    }

def validate_trade_amount(amount: float, user_balance: float, leverage: int) -> bool:
    """Проверка суммы сделки"""
    margin_required = amount * leverage / 10  # Упрощенная формула
    return margin_required <= user_balance and amount >= Config.MIN_TRADE_AMOUNT

def format_time_delta(dt: datetime) -> str:
    """Форматирование разницы во времени"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "just now"
