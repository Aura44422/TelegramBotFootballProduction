import aiohttp
import asyncio
import logging
import uuid
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from config import DONATION_ALERTS_TOKEN, DONATION_ALERTS_URL, SUBSCRIPTION_PRICES
from database import Database

logger = logging.getLogger(__name__)

class DonationAlerts:
    def __init__(self, database: Database):
        self.db = database
        self.token = DONATION_ALERTS_TOKEN
        self.base_url = DONATION_ALERTS_URL
        self.session = None
        self.payment_links = {}  # Кэш для хранения ссылок на оплату
        
    async def ensure_session(self):
        """Обеспечивает наличие активной сессии"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_unique_payment_link(self, user_id: int, subscription_type: str) -> str:
        """Генерация уникальной ссылки для оплаты"""
        unique_id = str(uuid.uuid4())
        payment_data = {
            'user_id': user_id,
            'subscription_type': subscription_type,
            'amount': SUBSCRIPTION_PRICES[subscription_type],
            'unique_id': unique_id,
            'created_at': datetime.now()
        }
        
        # Сохраняем данные платежа в кэше
        self.payment_links[unique_id] = payment_data
        
        # Генерируем уникальную ссылку
        if self.base_url.endswith('/'):
            payment_url = f"{self.base_url}{unique_id}"
        else:
            payment_url = f"{self.base_url}/{unique_id}"
        
        return payment_url
    
    async def create_payment_link(self, user_id: int, subscription_type: str) -> Dict:
        """Создание ссылки для оплаты"""
        try:
            if subscription_type not in SUBSCRIPTION_PRICES:
                raise ValueError(f"Неизвестный тип подписки: {subscription_type}")
            
            # Обеспечиваем наличие сессии
            await self.ensure_session()
            
            amount = SUBSCRIPTION_PRICES[subscription_type]
            payment_url = self.generate_unique_payment_link(user_id, subscription_type)
            
            # Для демонстрации возвращаем тестовую ссылку
            # В реальном проекте здесь будет API DonationAlerts
            return {
                'payment_url': payment_url,
                'amount': amount,
                'subscription_type': subscription_type,
                'external_id': f'user_{user_id}_{subscription_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            }
                    
        except Exception as e:
            logger.error(f"Ошибка при создании ссылки для оплаты: {e}")
            return None
    
    async def check_payment_status(self, unique_id: str) -> Optional[Dict]:
        """Проверка статуса платежа"""
        try:
            if unique_id not in self.payment_links:
                return None
            
            # Обеспечиваем наличие сессии
            await self.ensure_session()
            
            payment_data = self.payment_links[unique_id]
            
            # Проверяем платеж через API DonationAlerts
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            async with self.session.get(
                f'https://www.donationalerts.com/api/v1/alerts/donations/{payment_data["external_id"]}',
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Проверяем статус платежа
                    if data.get('status') == 'paid':
                        # Проверяем сумму платежа
                        paid_amount = float(data.get('amount', 0))
                        required_amount = payment_data['amount']
                        
                        if paid_amount >= required_amount:
                            return {
                                'status': 'success',
                                'user_id': payment_data['user_id'],
                                'subscription_type': payment_data['subscription_type'],
                                'amount': paid_amount,
                                'payment_id': data.get('id'),
                                'payment_data': data
                            }
                        else:
                            return {
                                'status': 'insufficient_amount',
                                'paid_amount': paid_amount,
                                'required_amount': required_amount
                            }
                    elif data.get('status') == 'pending':
                        return {'status': 'pending'}
                    else:
                        return {'status': 'failed'}
                else:
                    logger.error(f"Ошибка проверки статуса платежа: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса платежа: {e}")
            return None
    
    async def process_payment_webhook(self, webhook_data: Dict) -> Optional[Dict]:
        """Обработка webhook от DonationAlerts"""
        try:
            # Извлекаем данные из webhook
            payment_id = webhook_data.get('id')
            amount = float(webhook_data.get('amount', 0))
            external_id = webhook_data.get('external_id')
            status = webhook_data.get('status')
            
            if not external_id or status != 'paid':
                return None
            
            # Ищем соответствующий платеж в кэше
            for unique_id, payment_data in self.payment_links.items():
                if payment_data.get('external_id') == external_id:
                    # Проверяем сумму
                    required_amount = payment_data['amount']
                    
                    if amount >= required_amount:
                        # Удаляем из кэша
                        del self.payment_links[unique_id]
                        
                        return {
                            'status': 'success',
                            'user_id': payment_data['user_id'],
                            'subscription_type': payment_data['subscription_type'],
                            'amount': amount,
                            'payment_id': payment_id
                        }
                    else:
                        return {
                            'status': 'insufficient_amount',
                            'paid_amount': amount,
                            'required_amount': required_amount
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при обработке webhook: {e}")
            return None
    
    async def get_payment_history(self, user_id: int) -> List[Dict]:
        """Получение истории платежей пользователя"""
        try:
            # Получаем историю платежей из базы данных
            async with aiosqlite.connect(self.db.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT * FROM subscriptions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                ''', (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Ошибка при получении истории платежей: {e}")
            return []
    
    async def refund_payment(self, payment_id: str, reason: str = "Отмена подписки") -> bool:
        """Возврат платежа"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'reason': reason
            }
            
            async with self.session.post(
                f'https://www.donationalerts.com/api/v1/alerts/donations/{payment_id}/refund',
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    logger.info(f"Платеж {payment_id} успешно возвращен")
                    return True
                else:
                    logger.error(f"Ошибка возврата платежа: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при возврате платежа: {e}")
            return False
    
    async def cleanup_expired_links(self):
        """Очистка просроченных ссылок на оплату"""
        try:
            current_time = datetime.now()
            expired_links = []
            
            for unique_id, payment_data in self.payment_links.items():
                # Удаляем ссылки старше 24 часов
                if current_time - payment_data['created_at'] > timedelta(hours=24):
                    expired_links.append(unique_id)
            
            for unique_id in expired_links:
                del self.payment_links[unique_id]
                logger.info(f"Удалена просроченная ссылка: {unique_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке просроченных ссылок: {e}")
    
    def get_subscription_info(self, subscription_type: str) -> Dict:
        """Получение информации о подписке"""
        if subscription_type not in SUBSCRIPTION_PRICES:
            return None
        
        amount = SUBSCRIPTION_PRICES[subscription_type]
        
        info = {
            'type': subscription_type,
            'amount': amount,
            'currency': 'RUB'
        }
        
        # Добавляем информацию об экономии
        if subscription_type == 'two_weeks':
            info['savings'] = 300
            info['savings_text'] = 'Экономия 300₽'
        elif subscription_type == 'month':
            info['savings'] = 700
            info['savings_text'] = 'Экономия 700₽'
        else:
            info['savings'] = 0
            info['savings_text'] = ''
        
        return info 
