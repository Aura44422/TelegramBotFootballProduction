import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import re
from config import TARGET_COEFFICIENTS, REQUEST_TIMEOUT
from database import Database

logger = logging.getLogger(__name__)

class AdvancedMatchParser:
    def __init__(self, database: Database):
        self.db = database
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # API endpoints для различных букмекеров
        self.api_endpoints = {
            '1xbet': {
                'live': 'https://1xbet.com/api/live/football',
                'prematch': 'https://1xbet.com/api/prematch/football'
            },
            'bet365': {
                'live': 'https://www.bet365.com/api/live/football',
                'prematch': 'https://www.bet365.com/api/prematch/football'
            },
            'williamhill': {
                'live': 'https://sports.williamhill.com/api/live/football',
                'prematch': 'https://sports.williamhill.com/api/prematch/football'
            }
        }
    
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def parse_all_sources(self) -> List[Dict]:
        """Парсинг всех источников данных"""
        all_matches = []
        
        # Список источников для парсинга
        sources = [
            {'name': '1xbet', 'type': 'api'},
            {'name': 'bet365', 'type': 'api'},
            {'name': 'williamhill', 'type': 'api'},
            {'name': 'manual_scraping', 'type': 'scraping'}
        ]
        
        tasks = []
        for source in sources:
            if source['type'] == 'api':
                task = asyncio.create_task(self.parse_api_source(source['name']))
            else:
                task = asyncio.create_task(self.parse_scraping_source(source['name']))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_matches.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка при парсинге: {result}")
        
        # Удаляем дубликаты
        unique_matches = self.remove_duplicates(all_matches)
        
        logger.info(f"Всего найдено уникальных матчей: {len(unique_matches)}")
        return unique_matches
    
    async def parse_api_source(self, bookmaker: str) -> List[Dict]:
        """Парсинг через API букмекера"""
        matches = []
        
        try:
            if bookmaker == '1xbet':
                matches = await self.parse_1xbet_api()
            elif bookmaker == 'bet365':
                matches = await self.parse_bet365_api()
            elif bookmaker == 'williamhill':
                matches = await self.parse_williamhill_api()
            
            logger.info(f"Найдено {len(matches)} матчей через API {bookmaker}")
            return matches
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге API {bookmaker}: {e}")
            return []
    
    async def parse_1xbet_api(self) -> List[Dict]:
        """Парсинг API 1xbet"""
        matches = []
        
        try:
            # Попытка получить данные через API
            api_url = "https://1xbet.com/api/live/football"
            
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = await self.process_1xbet_data(data)
                else:
                    # Fallback на веб-скрапинг
                    matches = await self.scrape_1xbet_website()
                    
        except Exception as e:
            logger.error(f"Ошибка API 1xbet: {e}")
            # Fallback на веб-скрапинг
            matches = await self.scrape_1xbet_website()
        
        return matches
    
    async def parse_bet365_api(self) -> List[Dict]:
        """Парсинг API bet365"""
        matches = []
        
        try:
            # Попытка получить данные через API
            api_url = "https://www.bet365.com/api/live/football"
            
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = await self.process_bet365_data(data)
                else:
                    # Fallback на веб-скрапинг
                    matches = await self.scrape_bet365_website()
                    
        except Exception as e:
            logger.error(f"Ошибка API bet365: {e}")
            # Fallback на веб-скрапинг
            matches = await self.scrape_bet365_website()
        
        return matches
    
    async def parse_williamhill_api(self) -> List[Dict]:
        """Парсинг API William Hill"""
        matches = []
        
        try:
            # Попытка получить данные через API
            api_url = "https://sports.williamhill.com/api/live/football"
            
            async with self.session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = await self.process_williamhill_data(data)
                else:
                    # Fallback на веб-скрапинг
                    matches = await self.scrape_williamhill_website()
                    
        except Exception as e:
            logger.error(f"Ошибка API William Hill: {e}")
            # Fallback на веб-скрапинг
            matches = await self.scrape_williamhill_website()
        
        return matches
    
    async def process_1xbet_data(self, data: Dict) -> List[Dict]:
        """Обработка данных от API 1xbet"""
        matches = []
        
        try:
            # Примерная структура обработки данных
            if 'events' in data:
                for event in data['events']:
                    if event.get('sport') == 'football':
                        match_data = await self.extract_match_from_1xbet_event(event)
                        if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                            matches.append(match_data)
                            
        except Exception as e:
            logger.error(f"Ошибка обработки данных 1xbet: {e}")
        
        return matches
    
    async def process_bet365_data(self, data: Dict) -> List[Dict]:
        """Обработка данных от API bet365"""
        matches = []
        
        try:
            # Примерная структура обработки данных
            if 'events' in data:
                for event in data['events']:
                    if event.get('sport') == 'football':
                        match_data = await self.extract_match_from_bet365_event(event)
                        if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                            matches.append(match_data)
                            
        except Exception as e:
            logger.error(f"Ошибка обработки данных bet365: {e}")
        
        return matches
    
    async def process_williamhill_data(self, data: Dict) -> List[Dict]:
        """Обработка данных от API William Hill"""
        matches = []
        
        try:
            # Примерная структура обработки данных
            if 'events' in data:
                for event in data['events']:
                    if event.get('sport') == 'football':
                        match_data = await self.extract_match_from_williamhill_event(event)
                        if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                            matches.append(match_data)
                            
        except Exception as e:
            logger.error(f"Ошибка обработки данных William Hill: {e}")
        
        return matches
    
    async def extract_match_from_1xbet_event(self, event: Dict) -> Optional[Dict]:
        """Извлечение данных матча из события 1xbet"""
        try:
            # Примерная структура извлечения данных
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            league = event.get('league', 'Неизвестная лига')
            
            # Извлечение коэффициентов
            odds = event.get('odds', {})
            coefficient_1 = float(odds.get('home', 0))
            coefficient_2 = float(odds.get('away', 0))
            
            # Время матча
            match_time_str = event.get('start_time', '')
            match_time = self.parse_api_time(match_time_str)
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'bookmaker': '1xbet',
                'coefficient_1': coefficient_1,
                'coefficient_2': coefficient_2,
                'match_time': match_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных 1xbet: {e}")
            return None
    
    async def extract_match_from_bet365_event(self, event: Dict) -> Optional[Dict]:
        """Извлечение данных матча из события bet365"""
        try:
            # Примерная структура извлечения данных
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            league = event.get('competition', 'Неизвестная лига')
            
            # Извлечение коэффициентов
            odds = event.get('odds', {})
            coefficient_1 = float(odds.get('home', 0))
            coefficient_2 = float(odds.get('away', 0))
            
            # Время матча
            match_time_str = event.get('start_time', '')
            match_time = self.parse_api_time(match_time_str)
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'bookmaker': 'bet365',
                'coefficient_1': coefficient_1,
                'coefficient_2': coefficient_2,
                'match_time': match_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных bet365: {e}")
            return None
    
    async def extract_match_from_williamhill_event(self, event: Dict) -> Optional[Dict]:
        """Извлечение данных матча из события William Hill"""
        try:
            # Примерная структура извлечения данных
            home_team = event.get('home_team', '')
            away_team = event.get('away_team', '')
            league = event.get('competition', 'Неизвестная лига')
            
            # Извлечение коэффициентов
            odds = event.get('odds', {})
            coefficient_1 = float(odds.get('home', 0))
            coefficient_2 = float(odds.get('away', 0))
            
            # Время матча
            match_time_str = event.get('start_time', '')
            match_time = self.parse_api_time(match_time_str)
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'bookmaker': 'williamhill',
                'coefficient_1': coefficient_1,
                'coefficient_2': coefficient_2,
                'match_time': match_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных William Hill: {e}")
            return None
    
    async def parse_scraping_source(self, source_name: str) -> List[Dict]:
        """Парсинг через веб-скрапинг (fallback)"""
        matches = []
        
        try:
            if source_name == 'manual_scraping':
                # Используем базовый парсер как fallback
                from parser import MatchParser
                async with MatchParser(self.db) as parser:
                    matches = await parser.parse_all_bookmakers()
            
            logger.info(f"Найдено {len(matches)} матчей через скрапинг {source_name}")
            return matches
            
        except Exception as e:
            logger.error(f"Ошибка при скрапинге {source_name}: {e}")
            return []
    
    async def scrape_1xbet_website(self) -> List[Dict]:
        """Скрапинг сайта 1xbet (fallback)"""
        # Здесь будет реализация скрапинга сайта 1xbet
        return []
    
    async def scrape_bet365_website(self) -> List[Dict]:
        """Скрапинг сайта bet365 (fallback)"""
        # Здесь будет реализация скрапинга сайта bet365
        return []
    
    async def scrape_williamhill_website(self) -> List[Dict]:
        """Скрапинг сайта William Hill (fallback)"""
        # Здесь будет реализация скрапинга сайта William Hill
        return []
    
    def parse_api_time(self, time_str: str) -> datetime:
        """Парсинг времени из API"""
        try:
            # Различные форматы времени от API
            time_formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d %H:%M:%S',
                '%d.%m.%Y %H:%M',
                '%H:%M'
            ]
            
            for fmt in time_formats:
                try:
                    if fmt == '%H:%M':
                        # Если только время, добавляем сегодняшнюю дату
                        time_obj = datetime.strptime(time_str, fmt)
                        today = datetime.now().date()
                        return datetime.combine(today, time_obj.time())
                    else:
                        return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            # Если не удалось распарсить, возвращаем время через час
            return datetime.now() + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге времени API: {e}")
            return datetime.now() + timedelta(hours=1)
    
    def check_target_coefficients(self, coef1: float, coef2: float) -> bool:
        """Проверка соответствия коэффициентов целевым значениям"""
        for target_coef1, target_coef2 in TARGET_COEFFICIENTS:
            # Допустимая погрешность ±0.05
            if (abs(coef1 - target_coef1) <= 0.05 and abs(coef2 - target_coef2) <= 0.05):
                return True
        return False
    
    def remove_duplicates(self, matches: List[Dict]) -> List[Dict]:
        """Удаление дубликатов матчей"""
        unique_matches = []
        seen = set()
        
        for match in matches:
            # Создаем уникальный ключ для матча
            key = f"{match['home_team']}_{match['away_team']}_{match['bookmaker']}_{match['match_time'].strftime('%Y%m%d%H%M')}"
            
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches
    
    async def save_matches_to_db(self, matches: List[Dict]):
        """Сохранение найденных матчей в базу данных"""
        for match in matches:
            try:
                await self.db.add_match(
                    home_team=match['home_team'],
                    away_team=match['away_team'],
                    league=match['league'],
                    bookmaker=match['bookmaker'],
                    coefficient_1=match['coefficient_1'],
                    coefficient_2=match['coefficient_2'],
                    match_time=match['match_time']
                )
            except Exception as e:
                logger.error(f"Ошибка при сохранении матча в БД: {e}")
                continue 