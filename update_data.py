#!/usr/bin/env python3
"""
Скрипт для обновления рыночных данных и обслуживания базы данных
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, SessionLocal, User, Position
from crypto_data import crypto_data
from utils import check_liquidations, calculate_rankings
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_market_data():
    """Обновление рыночных данных"""
    logger.info("🔄 Обновление рыночных данных...")
    
    try:
        crypto_data.update_prices()
        logger.info("✅ Цены обновлены")
        
        # Обновление PnL открытых позиций
        db = SessionLocal()
        positions = db.query(Position).filter(Position.is_open == True).all()
        
        updated_count = 0
        for position in positions:
            current_price = crypto_data.get_current_price(position.symbol)
            if current_price:
                position.current_price = current_price
                position.unrealized_pnl = crypto_data.calculate_pnl(
                    position.entry_price,
                    current_price,
                    position.amount,
                    position.leverage,
                    position.position_type.value
                )
                updated_count += 1
        
        db.commit()
        logger.info(f"✅ Обновлено {updated_count} позиций")
        
        # Проверка ликвидаций
        liquidated = check_liquidations(db, crypto_data)
        if liquidated:
            logger.info(f"⚠️ Ликвидировано {len(liquidated)} позиций")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении данных: {e}")

def cleanup_old_data(days: int = 30):
    """Очистка старых данных"""
    logger.info(f"🧹 Очистка данных старше {days} дней...")
    
    try:
        db = SessionLocal()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Закрытые позиции старше cutoff_date
        old_positions = db.query(Position).filter(
            Position.is_open == False,
            Position.closed_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for position in old_positions:
            db.delete(position)
            deleted_count += 1
        
        # Старые транзакции
        from models.transaction import Transaction
        old_transactions = db.query(Transaction).filter(
            Transaction.created_at < cutoff_date
        ).all()
        
        for transaction in old_transactions:
            db.delete(transaction)
            deleted_count += 1
        
        db.commit()
        logger.info(f"✅ Удалено {deleted_count} записей")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при очистке данных: {e}")

def update_rankings():
    """Обновление рейтингов"""
    logger.info("🏆 Обновление рейтингов...")
    
    try:
        db = SessionLocal()
        calculate_rankings(db)
        logger.info("✅ Рейтинги обновлены")
        db.close()
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении рейтингов: {e}")

def backup_database():
    """Резервное копирование базы данных"""
    logger.info("💾 Резервное копирование базы данных...")
    
    try:
        import shutil
        from config import Config
        
        db_path = Config.DATABASE_URL.replace('sqlite:///', '')
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ Резервная копия создана: {backup_path}")
        
        # Удаление старых бэкапов (оставляем последние 7)
        import glob
        backups = sorted(glob.glob(f"{db_path}.backup.*"), reverse=True)
        for old_backup in backups[7:]:
            os.remove(old_backup)
            logger.info(f"🗑️ Удален старый бэкап: {old_backup}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при создании бэкапа: {e}")

def main():
    """Основная функция"""
    logger.info("🛠️ Запуск обслуживания Trading Game Bot")
    
    # Инициализация базы данных
    init_db()
    
    # Выполняем задачи обслуживания
    update_market_data()
    update_rankings()
    cleanup_old_data(30)
    backup_database()
    
    logger.info("✅ Обслуживание завершено")

if __name__ == "__main__":
    main()
