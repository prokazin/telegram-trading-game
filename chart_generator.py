import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
from datetime import datetime
import io
from typing import Optional, Tuple, List
from config import Config

class ChartGenerator:
    @staticmethod
    def create_price_chart(
        df: pd.DataFrame,
        symbol: str,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        current_price: Optional[float] = None
    ) -> io.BytesIO:
        """Создание графика цен с отметками"""
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Определяем цвет свечей
        colors = ['green' if close >= open else 'red' 
                 for close, open in zip(df['close'], df['open'])]
        
        # Рисуем свечи
        for idx, row in df.iterrows():
            color = colors[idx]
            
            # Тело свечи
            body_start = min(row['open'], row['close'])
            body_height = abs(row['close'] - row['open'])
            
            if body_height > 0:
                ax.add_patch(Rectangle(
                    (mdates.date2num(row['timestamp']) - 0.3, body_start),
                    0.6, body_height,
                    color=color, alpha=0.7
                ))
            
            # Тени свечи
            ax.plot(
                [mdates.date2num(row['timestamp']), mdates.date2num(row['timestamp'])],
                [row['low'], row['high']],
                color=color,
                linewidth=1
            )
        
        # Линии для отметок
        if entry_price:
            ax.axhline(y=entry_price, color='blue', linestyle='-', linewidth=2, alpha=0.7, label='Entry')
        
        if stop_loss:
            ax.axhline(y=stop_loss, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Stop Loss')
        
        if take_profit:
            ax.axhline(y=take_profit, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Take Profit')
        
        if current_price:
            ax.axhline(y=current_price, color='orange', linestyle='-', linewidth=1, alpha=0.5, label='Current')
        
        # Настройка осей
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d.%m'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        ax.set_title(f'{symbol} Price Chart', fontsize=14, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('Price (USDT)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Автоматическое масштабирование
        fig.tight_layout()
        
        # Сохранение в буфер
        buf = io.BytesIO()
        fig.savefig(buf, format='PNG', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
    
    @staticmethod
    def create_pnl_chart(pnl_history: List[float]) -> io.BytesIO:
        """Создание графика изменения PnL"""
        fig = Figure(figsize=(8, 4), dpi=100)
        ax = fig.add_subplot(111)
        
        dates = pd.date_range(end=datetime.now(), periods=len(pnl_history), freq='H')
        
        # График PnL
        ax.plot(dates, pnl_history, color='blue', linewidth=2, label='PnL')
        
        # Линия нуля
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        
        # Заливка положительной/отрицательной областей
        ax.fill_between(dates, pnl_history, 0, 
                       where=np.array(pnl_history) >= 0,
                       color='green', alpha=0.3)
        ax.fill_between(dates, pnl_history, 0,
                       where=np.array(pnl_history) < 0,
                       color='red', alpha=0.3)
        
        # Настройка осей
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_title('PnL History', fontsize=12, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('Profit/Loss (USDT)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format='PNG', dpi=100)
        buf.seek(0)
        plt.close(fig)
        
        return buf
