import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        
    async def init_database(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    subscription_type TEXT DEFAULT 'trial',
                    subscription_end TIMESTAMP,
                    trial_messages_used INTEGER DEFAULT 0,
                    daily_signals_used INTEGER DEFAULT 0,
                    last_signal_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Таблица администраторов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    admin_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица подписок
            await db.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    subscription_type TEXT,
                    amount REAL,
                    payment_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица найденных матчей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    home_team TEXT,
                    away_team TEXT,
                    league TEXT,
                    bookmaker TEXT,
                    coefficient_1 REAL,
                    coefficient_2 REAL,
                    match_time TIMESTAMP,
                    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_sent BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Таблица отправленных сигналов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sent_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    match_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (match_id) REFERENCES matches (id)
                )
            ''')
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление нового пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM users WHERE user_id = ?
            ''', (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def update_user_subscription(self, user_id: int, subscription_type: str, days: int):
        """Обновление подписки пользователя"""
        end_date = datetime.now() + timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users 
                SET subscription_type = ?, subscription_end = ?, daily_signals_used = 0
                WHERE user_id = ?
            ''', (subscription_type, end_date, user_id))
            await db.commit()
    
    async def revoke_subscription(self, user_id: int):
        """Отзыв подписки пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users 
                SET subscription_type = 'revoked', subscription_end = NULL
                WHERE user_id = ?
            ''', (user_id,))
            await db.commit()
    
    async def increment_trial_messages(self, user_id: int):
        """Увеличение счетчика использованных пробных сообщений"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE users 
                SET trial_messages_used = trial_messages_used + 1
                WHERE user_id = ?
            ''', (user_id,))
            await db.commit()
    
    async def increment_daily_signals(self, user_id: int):
        """Увеличение счетчика использованных сигналов за день"""
        today = datetime.now().date()
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, нужно ли сбросить счетчик
            await db.execute('''
                UPDATE users 
                SET daily_signals_used = CASE 
                    WHEN last_signal_date != ? THEN 1
                    ELSE daily_signals_used + 1
                END,
                last_signal_date = ?
                WHERE user_id = ?
            ''', (today, today, user_id))
            await db.commit()
    
    async def add_admin(self, admin_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Добавление администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR IGNORE INTO admins (admin_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (admin_id, username, first_name, last_name))
            await db.commit()
    
    async def remove_admin(self, admin_id: int):
        """Удаление администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM admins WHERE admin_id = ?', (admin_id,))
            await db.commit()
    
    async def get_admins(self) -> List[Dict]:
        """Получение списка всех администраторов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM admins') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT 1 FROM admins WHERE admin_id = ?', (user_id,)) as cursor:
                return await cursor.fetchone() is not None
    
    async def add_subscription_record(self, user_id: int, subscription_type: str, amount: float, payment_id: str):
        """Добавление записи о подписке"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO subscriptions (user_id, subscription_type, amount, payment_id)
                VALUES (?, ?, ?, ?)
            ''', (user_id, subscription_type, amount, payment_id))
            await db.commit()
    
    async def add_match(self, home_team: str, away_team: str, league: str, bookmaker: str, 
                       coefficient_1: float, coefficient_2: float, match_time: datetime):
        """Добавление найденного матча"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO matches (home_team, away_team, league, bookmaker, coefficient_1, coefficient_2, match_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (home_team, away_team, league, bookmaker, coefficient_1, coefficient_2, match_time))
            await db.commit()
    
    async def get_unsent_matches(self) -> List[Dict]:
        """Получение неотправленных матчей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM matches 
                WHERE is_sent = FALSE AND match_time > datetime('now')
                ORDER BY match_time ASC
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def mark_match_sent(self, match_id: int):
        """Отметка матча как отправленного"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('UPDATE matches SET is_sent = TRUE WHERE id = ?', (match_id,))
            await db.commit()
    
    async def add_sent_signal(self, user_id: int, match_id: int):
        """Добавление записи об отправленном сигнале"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO sent_signals (user_id, match_id)
                VALUES (?, ?)
            ''', (user_id, match_id))
            await db.commit()
    
    async def get_subscription_stats(self) -> Dict:
        """Получение статистики подписок"""
        async with aiosqlite.connect(self.db_path) as db:
            # Общее количество пользователей с активной подпиской
            async with db.execute('''
                SELECT COUNT(*) as count FROM users 
                WHERE subscription_type != 'trial' AND subscription_type != 'revoked'
                AND (subscription_end IS NULL OR subscription_end > datetime('now'))
            ''') as cursor:
                active_subscriptions = (await cursor.fetchone())[0]
            
            # Общее количество пользователей без подписки
            async with db.execute('''
                SELECT COUNT(*) as count FROM users 
                WHERE subscription_type = 'trial' OR subscription_type = 'revoked'
                OR (subscription_end IS NOT NULL AND subscription_end <= datetime('now'))
            ''') as cursor:
                inactive_subscriptions = (await cursor.fetchone())[0]
            
            # Количество покупок на этой неделе
            week_ago = datetime.now() - timedelta(days=7)
            async with db.execute('''
                SELECT COUNT(*) as count FROM subscriptions 
                WHERE created_at >= ?
            ''', (week_ago,)) as cursor:
                weekly_purchases = (await cursor.fetchone())[0]
            
            # Самая популярная подписка на этой неделе
            async with db.execute('''
                SELECT subscription_type, COUNT(*) as count 
                FROM subscriptions 
                WHERE created_at >= ?
                GROUP BY subscription_type 
                ORDER BY count DESC 
                LIMIT 1
            ''', (week_ago,)) as cursor:
                row = await cursor.fetchone()
                popular_subscription = row[0] if row else 'Нет данных'
            
            return {
                'active_subscriptions': active_subscriptions,
                'inactive_subscriptions': inactive_subscriptions,
                'weekly_purchases': weekly_purchases,
                'popular_subscription': popular_subscription
            }
    
    async def get_users_with_active_subscription(self) -> List[Dict]:
        """Получение пользователей с активной подпиской"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM users 
                WHERE subscription_type != 'trial' AND subscription_type != 'revoked'
                AND (subscription_end IS NULL OR subscription_end > datetime('now'))
                AND is_active = TRUE
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_users_with_expired_subscription(self) -> List[Dict]:
        """Получение пользователей с истекшей подпиской"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM users 
                WHERE subscription_end IS NOT NULL AND subscription_end <= datetime('now')
                AND is_active = TRUE
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows] 