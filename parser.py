import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
from config import TARGET_COEFFICIENTS, REQUEST_TIMEOUT, MAX_RETRIES
from database import Database

logger = logging.getLogger(__name__)

class MatchParser:
    def __init__(self, database: Database):
        self.db = database
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def parse_all_bookmakers(self) -> List[Dict]:
        """Парсинг всех букмекеров"""
        all_matches = []
        
        # Список букмекеров для парсинга
        bookmakers = [
            {'name': '1xbet', 'url': 'https://1xbet.com/ru/live/football'},
            {'name': 'bet365', 'url': 'https://www.bet365.com/sport/football'},
            {'name': 'williamhill', 'url': 'https://sports.williamhill.com/betting/en-gb/football'},
            {'name': 'bwin', 'url': 'https://sports.bwin.com/en/sports/football-4'},
            {'name': 'unibet', 'url': 'https://www.unibet.com/sports/football'},
        ]
        
        tasks = []
        for bookmaker in bookmakers:
            task = asyncio.create_task(self.parse_bookmaker(bookmaker))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_matches.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Ошибка при парсинге: {result}")
        
        return all_matches
    
    async def parse_bookmaker(self, bookmaker: Dict) -> List[Dict]:
        """Парсинг конкретного букмекера"""
        matches = []
        
        try:
            if bookmaker['name'] == '1xbet':
                matches = await self.parse_1xbet(bookmaker['url'])
            elif bookmaker['name'] == 'bet365':
                matches = await self.parse_bet365(bookmaker['url'])
            elif bookmaker['name'] == 'williamhill':
                matches = await self.parse_williamhill(bookmaker['url'])
            elif bookmaker['name'] == 'bwin':
                matches = await self.parse_bwin(bookmaker['url'])
            elif bookmaker['name'] == 'unibet':
                matches = await self.parse_unibet(bookmaker['url'])
            
            logger.info(f"Найдено {len(matches)} матчей на {bookmaker['name']}")
            return matches
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге {bookmaker['name']}: {e}")
            return []
    
    async def parse_1xbet(self, url: str) -> List[Dict]:
        """Парсинг 1xbet"""
        matches = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Поиск матчей (примерная структура)
                    match_elements = soup.find_all('div', class_='c-events__item')
                    
                    for element in match_elements:
                        try:
                            match_data = await self.extract_match_data_1xbet(element)
                            if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                                matches.append(match_data)
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении данных матча 1xbet: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка при парсинге 1xbet: {e}")
        
        return matches
    
    async def parse_bet365(self, url: str) -> List[Dict]:
        """Парсинг bet365"""
        matches = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Поиск матчей (примерная структура)
                    match_elements = soup.find_all('div', class_='gl-Market_General')
                    
                    for element in match_elements:
                        try:
                            match_data = await self.extract_match_data_bet365(element)
                            if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                                matches.append(match_data)
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении данных матча bet365: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка при парсинге bet365: {e}")
        
        return matches
    
    async def parse_williamhill(self, url: str) -> List[Dict]:
        """Парсинг William Hill"""
        matches = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Поиск матчей (примерная структура)
                    match_elements = soup.find_all('div', class_='btmarket__selection')
                    
                    for element in match_elements:
                        try:
                            match_data = await self.extract_match_data_williamhill(element)
                            if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                                matches.append(match_data)
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении данных матча William Hill: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка при парсинге William Hill: {e}")
        
        return matches
    
    async def parse_bwin(self, url: str) -> List[Dict]:
        """Парсинг bwin"""
        matches = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Поиск матчей (примерная структура)
                    match_elements = soup.find_all('div', class_='market')
                    
                    for element in match_elements:
                        try:
                            match_data = await self.extract_match_data_bwin(element)
                            if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                                matches.append(match_data)
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении данных матча bwin: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка при парсинге bwin: {e}")
        
        return matches
    
    async def parse_unibet(self, url: str) -> List[Dict]:
        """Парсинг Unibet"""
        matches = []
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Поиск матчей (примерная структура)
                    match_elements = soup.find_all('div', class_='event')
                    
                    for element in match_elements:
                        try:
                            match_data = await self.extract_match_data_unibet(element)
                            if match_data and self.check_target_coefficients(match_data['coefficient_1'], match_data['coefficient_2']):
                                matches.append(match_data)
                        except Exception as e:
                            logger.error(f"Ошибка при извлечении данных матча Unibet: {e}")
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка при парсинге Unibet: {e}")
        
        return matches
    
    async def extract_match_data_1xbet(self, element) -> Optional[Dict]:
        """Извлечение данных матча из 1xbet"""
        try:
            # Примерная структура извлечения данных
            teams_element = element.find('div', class_='c-events__teams')
            if not teams_element:
                return None
            
            teams_text = teams_element.get_text(strip=True)
            teams = teams_text.split(' - ')
            if len(teams) != 2:
                return None
            
            home_team = teams[0].strip()
            away_team = teams[1].strip()
            
            # Извлечение коэффициентов
            coefficients = element.find_all('span', class_='c-bets__bet')
            if len(coefficients) < 2:
                return None
            
            coefficient_1 = float(coefficients[0].get_text(strip=True))
            coefficient_2 = float(coefficients[1].get_text(strip=True))
            
            # Извлечение времени матча
            time_element = element.find('div', class_='c-events__time')
            match_time = self.parse_match_time(time_element.get_text(strip=True)) if time_element else datetime.now() + timedelta(hours=1)
            
            # Извлечение лиги
            league_element = element.find('div', class_='c-events__league')
            league = league_element.get_text(strip=True) if league_element else 'Неизвестная лига'
            
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
            logger.error(f"Ошибка при извлечении данных 1xbet: {e}")
            return None
    
    async def extract_match_data_bet365(self, element) -> Optional[Dict]:
        """Извлечение данных матча из bet365"""
        try:
            # Аналогичная логика для bet365
            teams_element = element.find('span', class_='gl-ParticipantFixtureDetails_TeamName')
            if not teams_element:
                return None
            
            teams_text = teams_element.get_text(strip=True)
            teams = teams_text.split(' v ')
            if len(teams) != 2:
                return None
            
            home_team = teams[0].strip()
            away_team = teams[1].strip()
            
            # Извлечение коэффициентов
            coefficients = element.find_all('span', class_='gl-ParticipantOddsOnly_Odds')
            if len(coefficients) < 2:
                return None
            
            coefficient_1 = float(coefficients[0].get_text(strip=True))
            coefficient_2 = float(coefficients[1].get_text(strip=True))
            
            # Извлечение времени матча
            time_element = element.find('span', class_='gl-ParticipantFixtureDetails_BookCloses')
            match_time = self.parse_match_time(time_element.get_text(strip=True)) if time_element else datetime.now() + timedelta(hours=1)
            
            # Извлечение лиги
            league_element = element.find('span', class_='gl-ParticipantFixtureDetails_LeagueName')
            league = league_element.get_text(strip=True) if league_element else 'Неизвестная лига'
            
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
            logger.error(f"Ошибка при извлечении данных bet365: {e}")
            return None
    
    async def extract_match_data_williamhill(self, element) -> Optional[Dict]:
        """Извлечение данных матча из William Hill"""
        # Аналогичная логика для William Hill
        return await self.extract_match_data_generic(element, 'williamhill')
    
    async def extract_match_data_bwin(self, element) -> Optional[Dict]:
        """Извлечение данных матча из bwin"""
        # Аналогичная логика для bwin
        return await self.extract_match_data_generic(element, 'bwin')
    
    async def extract_match_data_unibet(self, element) -> Optional[Dict]:
        """Извлечение данных матча из Unibet"""
        # Аналогичная логика для Unibet
        return await self.extract_match_data_generic(element, 'unibet')
    
    async def extract_match_data_generic(self, element, bookmaker: str) -> Optional[Dict]:
        """Универсальный метод извлечения данных матча"""
        try:
            # Поиск команд
            team_elements = element.find_all(['span', 'div'], class_=re.compile(r'.*team.*|.*participant.*', re.I))
            if len(team_elements) < 2:
                return None
            
            home_team = team_elements[0].get_text(strip=True)
            away_team = team_elements[1].get_text(strip=True)
            
            # Поиск коэффициентов
            coefficient_elements = element.find_all(['span', 'div'], class_=re.compile(r'.*odds.*|.*coefficient.*|.*price.*', re.I))
            if len(coefficient_elements) < 2:
                return None
            
            coefficient_1 = float(coefficient_elements[0].get_text(strip=True))
            coefficient_2 = float(coefficient_elements[1].get_text(strip=True))
            
            # Поиск времени
            time_element = element.find(['span', 'div'], class_=re.compile(r'.*time.*|.*date.*', re.I))
            match_time = self.parse_match_time(time_element.get_text(strip=True)) if time_element else datetime.now() + timedelta(hours=1)
            
            # Поиск лиги
            league_element = element.find(['span', 'div'], class_=re.compile(r'.*league.*|.*competition.*', re.I))
            league = league_element.get_text(strip=True) if league_element else 'Неизвестная лига'
            
            return {
                'home_team': home_team,
                'away_team': away_team,
                'league': league,
                'bookmaker': bookmaker,
                'coefficient_1': coefficient_1,
                'coefficient_2': coefficient_2,
                'match_time': match_time
            }
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении данных {bookmaker}: {e}")
            return None
    
    def check_target_coefficients(self, coef1: float, coef2: float) -> bool:
        """Проверка соответствия коэффициентов целевым значениям"""
        for target_coef1, target_coef2 in TARGET_COEFFICIENTS:
            # Допустимая погрешность ±0.05
            if (abs(coef1 - target_coef1) <= 0.05 and abs(coef2 - target_coef2) <= 0.05):
                return True
        return False
    
    def parse_match_time(self, time_str: str) -> datetime:
        """Парсинг времени матча"""
        try:
            # Различные форматы времени
            time_formats = [
                '%H:%M',
                '%d.%m.%Y %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M'
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
            logger.error(f"Ошибка при парсинге времени: {e}")
            return datetime.now() + timedelta(hours=1)
    
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