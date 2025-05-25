#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Digest Script - Codzienne podsumowanie dnia
Wysyła spersonalizowane podsumowanie dnia na email o 7:45
"""

import os
import sys
import json
import random
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import time
from typing import Dict, List, Optional, Any

# Importy dla integracji z zewnętrznymi usługami
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openai
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_digest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Stałe konfiguracyjne
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
MAX_RETRIES = 3
RETRY_DELAY = 2  # sekundy


class DailyDigestError(Exception):
    """Wyjątek dla błędów w Daily Digest"""
    pass


class APIIntegration:
    """Klasa do zarządzania integracjami z zewnętrznymi API"""
    
    def __init__(self):
        self.errors = []
    
    def retry_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Wykonuje operację z mechanizmem retry"""
        for attempt in range(MAX_RETRIES):
            try:
                result = operation_func(*args, **kwargs)
                logger.info(f"{operation_name} - sukces w próbie {attempt + 1}")
                return result
            except Exception as e:
                logger.warning(f"{operation_name} - błąd w próbie {attempt + 1}: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    error_msg = f"{operation_name} - wszystkie {MAX_RETRIES} próby nieudane: {str(e)}"
                    self.errors.append(error_msg)
                    logger.error(error_msg)
                    return None


class GoogleCalendarIntegration(APIIntegration):
    """Integracja z Google Calendar"""
    
    def __init__(self):
        super().__init__()
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Autentykacja z Google Calendar API"""
        creds = None
        token_path = 'token.json'
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if os.path.exists(credentials_path):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    logger.error("Brak pliku credentials.json dla Google Calendar")
                    return
            
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia serwisu Google Calendar: {e}")
    
    def get_today_events(self) -> List[Dict[str, Any]]:
        """Pobiera wydarzenia z kalendarza na dziś"""
        if not self.service:
            return []
        
        def _get_events():
            # Zamiast pojedynczego ID, używamy listy ID kalendarzy
            calendar_ids_str = os.getenv('GOOGLE_CALENDAR_IDS', 'primary')
            # Dzielimy string z ID kalendarzy po przecinku
            calendar_ids = [cal_id.strip() for cal_id in calendar_ids_str.split(',')]
            
            # Dziś od 00:00 do 23:59
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
            
            formatted_events = []
            # Iterujemy po wszystkich kalendarzach
            for calendar_id in calendar_ids:
                try:
                    # Pobierz informacje o kalendarzu, aby uzyskać jego nazwę
                    calendar_info = self.service.calendars().get(calendarId=calendar_id).execute()
                    calendar_name = calendar_info.get('summary', calendar_id)
                    
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=today_start.isoformat() + 'Z',
                        timeMax=today_end.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    events = events_result.get('items', [])
                    logger.info(f"Pobrano {len(events)} wydarzeń z kalendarza {calendar_name}")
                    
                    for event in events:
                        start_time = event['start'].get('dateTime', event['start'].get('date'))
                        summary = event.get('summary', 'Brak tytułu')
                        location = event.get('location', '')
                        # Usuwamy pole description zgodnie z żądaniem
                        
                        # Formatowanie czasu z uwzględnieniem strefy czasowej Polski
                        if 'T' in start_time:  # DateTime format
                            # Parsuj czas do obiektu datetime
                            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                            
                            # Konwertuj do czasu polskiego (dodaj 1 lub 2 godziny, zależnie od czasu letniego/zimowego)
                            # Prosta metoda - dodaj odpowiednią liczbę godzin
                            # Sprawdź, czy mamy czas letni czy zimowy
                            # W Polsce czas letni jest od ostatniej niedzieli marca do ostatniej niedzieli października
                            year = start_dt.year
                            is_summer_time = False
                            
                            # Znajdź ostatnią niedzielę marca
                            march_last_day = datetime(year, 3, 31)
                            march_last_sunday = march_last_day - timedelta(days=march_last_day.weekday() + 1 if march_last_day.weekday() < 6 else 0)
                            
                            # Znajdź ostatnią niedzielę października
                            october_last_day = datetime(year, 10, 31)
                            october_last_sunday = october_last_day - timedelta(days=october_last_day.weekday() + 1 if october_last_day.weekday() < 6 else 0)
                            
                            # Sprawdź, czy jesteśmy w okresie czasu letniego
                            if march_last_sunday <= start_dt.replace(tzinfo=None) < october_last_sunday:
                                is_summer_time = True
                            
                            # Dodaj odpowiednią liczbę godzin
                            if is_summer_time:
                                start_dt = start_dt + timedelta(hours=2)  # Czas letni w Polsce to UTC+2
                            else:
                                start_dt = start_dt + timedelta(hours=1)  # Czas zimowy w Polsce to UTC+1
                                
                            time_str = start_dt.strftime('%H:%M')
                        else:  # Date format (cały dzień)
                            time_str = 'Cały dzień'
                        
                        formatted_events.append({
                            'time': time_str,
                            'title': summary,
                            'location': location,
                            'calendar_name': calendar_name  # Przekazujemy nazwę kalendarza zamiast ID
                        })
                except Exception as e:
                    error_msg = f"Błąd podczas pobierania wydarzeń z kalendarza {calendar_id}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
            
            # Sortowanie wszystkich wydarzeń według czasu
            formatted_events.sort(key=lambda event: '00:00' if event['time'] == 'Cały dzień' else event['time'])
            
            return formatted_events
        
        return self.retry_operation("Google Calendar", _get_events) or []


class WeatherIntegration(APIIntegration):
    """Integracja z OpenWeatherMap API"""
    
    def __init__(self):
        super().__init__()
        self.api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        self.city = os.getenv('WEATHER_CITY', 'Warsaw')
    
    def get_weather_forecast(self) -> Dict[str, Any]:
        """Pobiera prognozę pogody na dziś"""
        if not self.api_key:
            self.errors.append("Brak klucza API dla OpenWeatherMap")
            return {}
        
        def _get_weather():
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.city,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'pl'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'description': data['weather'][0]['description'].capitalize(),
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'],
                'city': data['name']
            }
        
        return self.retry_operation("OpenWeatherMap", _get_weather) or {}


class NotionIntegration(APIIntegration):
    """Integracja z Notion API"""
    
    def __init__(self):
        super().__init__()
        self.token = os.getenv('NOTION_TOKEN')
        self.database_id = os.getenv('NOTION_DATABASE_ID')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def get_articles_not_started(self) -> List[Dict[str, Any]]:
        """Pobiera artykuły ze statusem 'Not started' i zmienia ich status na 'Done'."""
        if not self.token or not self.database_id:
            self.errors.append("Brak tokenu lub ID bazy danych Notion")
            return []
        
        def _get_articles():
            # Pobierz artykuły ze statusem "Not started"
            query_url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
            
            query_data = {
                    "filter": {
                        "property": "Status",
                        "select": {
                        "equals": "Not started"
                        }
                    }
            }
            
            response = requests.post(query_url, headers=self.headers, json=query_data, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            all_articles = []
            for result in data.get('results', []):
                # Pobierz dane artykułu
                properties = result['properties']
                
                name = ''
                if 'Name' in properties and properties['Name']['type'] == 'title':
                    name = ''.join([text['plain_text'] for text in properties['Name']['title']])
                
                link = ''
                if 'Link' in properties and properties['Link']['type'] == 'url':
                    link = properties['Link']['url'] or ''
                
                author = ''
                if 'Author' in properties:
                    if properties['Author']['type'] == 'rich_text':
                        author = ''.join([text['plain_text'] for text in properties['Author']['rich_text']])
                    elif properties['Author']['type'] == 'select':
                        author = properties['Author']['select']['name'] if properties['Author']['select'] else ''
                
                all_articles.append({
                    'name': name,
                    'link': link,
                    'author': author,
                    'page_id': result['id']
                })
            
            selected_articles = []
            if len(all_articles) > 3:
                selected_articles = random.sample(all_articles, 3)
            else:
                selected_articles = all_articles
            
            # Zmień status wybranych artykułów na "Done"
            self._update_article_status(selected_articles)
            
            return selected_articles
        
        return self.retry_operation("Notion", _get_articles) or []
    
    def _update_article_status(self, articles: List[Dict[str, Any]]) -> None:
        """Zmienia status artykułów na 'Done'."""
        for article in articles:
            page_id = article.get('page_id')
            if not page_id:
                continue
                
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            update_data = {
                "properties": {
                    "Status": {
                        "select": {
                            "name": "Done"
                        }
                    }
                }
            }
            
            try:
                response = requests.patch(update_url, headers=self.headers, json=update_data, timeout=10)
                response.raise_for_status()
                logger.info(f"Zmieniono status artykułu '{article['name']}' na 'Done'")
            except Exception as e:
                error_msg = f"Błąd podczas aktualizacji statusu artykułu '{article['name']}': {str(e)}"
                logger.error(error_msg)
                self.errors.append(error_msg)


class QuotesManager:
    """Zarządza cytatami, generując je dynamicznie przez AI."""
    
    def __init__(self):
        # Usunięto inicjalizację z pliku quotes.json
        # self.quotes_file = quotes_file
        # self.quotes = self._load_quotes()
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        pass

    # Usunięto metodę _load_quotes, ponieważ nie jest już potrzebna
    # def _load_quotes(self) -> List[Dict[str, str]]:
    #     """Ładuje cytaty z pliku JSON"""
    #     try:
    #         with open(self.quotes_file, 'r', encoding='utf-8') as f:
    #             return json.load(f)
    #     except FileNotFoundError:
    #         logger.error(f"Nie znaleziono pliku {self.quotes_file}")
    #         return []
    #     except json.JSONDecodeError:
    #         logger.error(f"Błąd parsowania pliku {self.quotes_file}")
    #         return []
    
    def get_random_quote(self) -> Dict[str, str]:
        """Generuje losowy motywacyjny cytat na dziś przy użyciu AI."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1-nano", # Uwzględniono zmianę modelu dokonaną przez użytkownika
                messages=[
                    {
                        "role": "system",
                        "content": """Jesteś ekspertem od generowania krótkich, inspirujących cytatów. 
                                    Odpowiedz tylko samym cytatem, jego autorem i źródłem (autor i źródło mają być autentyczne).
                                    Format odpowiedzi powinien być JSON: {"quote": "Treść cytatu", "author": "Autor cytatu", "source": "Źródło/Książka"}."""
                    },
                    {
                        "role": "user",
                        "content": "Podaj mi motywacyjny cytat na dzisiejszy dzień."
                    }
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            quote_data_str = response.choices[0].message.content.strip()
            
            # Próba sparsowania JSONa
            try:
                quote_data = json.loads(quote_data_str)
                if isinstance(quote_data, dict) and 'quote' in quote_data and 'author' in quote_data:
                    # Upewnij się, że source istnieje, nawet jeśli jest pusty
                    quote_data.setdefault('source', 'Nieznane źródło') 
                    logger.info(f"Wygenerowano cytat AI: \"{quote_data['quote']}\" - {quote_data['author']}")
                    return quote_data
                else:
                    logger.warning(f"AI zwróciło niepoprawny format JSON dla cytatu: {quote_data_str}")
            except json.JSONDecodeError:
                logger.warning(f"Nie udało się sparsować JSON z odpowiedzi AI dla cytatu: {quote_data_str}")

            # Jeśli AI nie zwróciło poprawnego JSONa, spróbuj wyciągnąć dane heurystycznie
            # (To jest uproszczone, można by tu dodać bardziej zaawansowane parsowanie)
            # Na razie, jeśli JSON się nie powiedzie, użyjemy domyślnego.

        except Exception as e:
            logger.error(f"Błąd podczas generowania cytatu przez AI: {e}")

        # Domyślny cytat w przypadku błędu lub niepoprawnej odpowiedzi AI
        logger.warning("Używam domyślnego cytatu z powodu problemu z AI.")
        return {
            'quote': 'Każdy dzień to nowa szansa, aby być lepszym niż wczoraj.',
            'author': 'Chatbot',
            'source': 'Mądrość cyfrowa'
        }


class AIContentGenerator:
    """Generuje spersonalizowaną treść przy użyciu AI"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def generate_personalized_content(self, data: Dict[str, Any]) -> str:
        """Generuje spersonalizowaną treść na podstawie danych"""
        try:
            prompt = self._create_prompt(data)
            
            response = self.client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[
                    {
                        "role": "system",
                        "content": """Jesteś asystentem do tworzenia codziennych podsumowań. 
                        Twoim zadaniem jest stworzenie przyjaznego, ale profesjonalnego podsumowania dnia w języku polskim.
                        Używaj luźnego, ale nie przesadnie potocznego tonu. 
                        Bądź pomocny i motywujący. Nie dodawaj zbędnych znaczników HTML - zostanie to użyte w szablonie HTML."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Błąd podczas generowania treści AI: {e}")
            return "Przepraszam, nie udało się wygenerować spersonalizowanej treści. Oto Twoje dane na dziś."
    
    def _create_prompt(self, data: Dict[str, Any]) -> str:
        """Tworzy prompt dla AI na podstawie danych"""
        events = data.get('events', [])
        weather = data.get('weather', {})
        articles = data.get('articles', [])
        quote = data.get('quote', {})
        
        prompt = f"""
        Stwórz krótkie (2-3 zdania), przyjazne wprowadzenie do dzisiejszego dnia w języku polskim.
        Weź pod uwagę:
        
        Wydarzenia na dziś: {len(events)} wydarzeń zaplanowanych
        Pogoda: {weather.get('description', 'brak danych')} {weather.get('temperature', 'N/A')}°C
        Artykuły do przeczytania: {len(articles)} artykułów
        Cytat dnia: "{quote.get('quote', 'Brak cytatu')}" - {quote.get('author', 'Nieznany')}
        
        Stwórz motywujące wprowadzenie, które łączy te elementy w spójną całość.
        """
        
        return prompt


class EmailSender:
    """Zarządza wysyłaniem e-maili"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = os.getenv('GMAIL_EMAIL')
        self.password = os.getenv('GMAIL_APP_PASSWORD')
        self.recipient = os.getenv('RECIPIENT_EMAIL')
    
    def send_daily_digest(self, content: Dict[str, Any]):
        """Wysyła dzienny digest na e-mail"""
        try:
            # Załaduj szablon HTML
            template_path = 'email_template.html'
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            # Wypełnij szablon danymi
            html_content = self._fill_template(template, content)
            
            # Utwórz wiadomość
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📅 Daily Digest - {datetime.now().strftime('%d.%m.%Y')}"
            msg['From'] = formataddr(('Daily Digest', self.email))
            msg['To'] = self.recipient
            
            # Dodaj treść HTML
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Wyślij e-mail
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
            
            logger.info("E-mail został wysłany pomyślnie")
            
        except Exception as e:
            logger.error(f"Błąd podczas wysyłania e-maila: {e}")
            raise
    
    def _fill_template(self, template: str, content: Dict[str, Any]) -> str:
        """Wypełnia szablon HTML danymi"""
        # Generuj sekcje HTML
        events_html = self._generate_events_html(content.get('events', []))
        weather_html = self._generate_weather_html(content.get('weather', {}))
        articles_html = self._generate_articles_html(content.get('articles', []))
        quote_html = self._generate_quote_html(content.get('quote', {}))
        errors_html = self._generate_errors_html(content.get('errors', []))
        ai_intro = content.get('ai_intro', 'Oto Twoje podsumowanie na dziś!')
        
        # Zastąp placeholdery w szablonie
        filled_template = template.replace('{{AI_INTRO}}', ai_intro)
        filled_template = filled_template.replace('{{EVENTS_SECTION}}', events_html)
        filled_template = filled_template.replace('{{WEATHER_SECTION}}', weather_html)
        filled_template = filled_template.replace('{{ARTICLES_SECTION}}', articles_html)
        filled_template = filled_template.replace('{{QUOTE_SECTION}}', quote_html)
        filled_template = filled_template.replace('{{ERRORS_SECTION}}', errors_html)
        filled_template = filled_template.replace('{{DATE}}', datetime.now().strftime('%d.%m.%Y'))
        
        return filled_template
    
    def _generate_events_html(self, events: List[Dict[str, Any]]) -> str:
        """Generuje HTML dla sekcji wydarzeń"""
        if not events:
            return '<p style="color: #666;">Brak zaplanowanych wydarzeń na dziś.</p>'
        
        html = ''
        for event in events:
            # Dodaj informację o kalendarzu, jeśli jest dostępna i nie jest 'primary'
            calendar_info = ''
            if 'calendar_name' in event and event['calendar_name'] != 'primary':
                calendar_info = f'<div style="color: #777; font-size: 12px; margin-top: 2px;">Kalendarz: {event["calendar_name"]}</div>'
            
            html += f'''
            <div style="margin-bottom: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 8px;">
                <div style="font-weight: 600; color: #007AFF;">{event['time']}</div>
                <div style="font-weight: 500; margin-top: 5px;">{event['title']}</div>
                {f'<div style="color: #666; font-size: 14px; margin-top: 3px;">📍 {event["location"]}</div>' if event.get('location') else ''}
                {calendar_info}
            </div>
            '''
        return html
    
    def _generate_weather_html(self, weather: Dict[str, Any]) -> str:
        """Generuje HTML dla sekcji pogody"""
        if not weather:
            return '<p style="color: #666;">Brak danych pogodowych.</p>'
        
        return f'''
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px;">
            <div style="font-size: 24px; font-weight: 600; color: #007AFF;">{weather.get('temperature', 'N/A')}°C</div>
            <div style="font-size: 16px; margin-top: 5px;">{weather.get('description', 'Brak opisu')}</div>
            <div style="font-size: 14px; color: #666; margin-top: 8px;">
                Odczuwalna: {weather.get('feels_like', 'N/A')}°C | 
                Wilgotność: {weather.get('humidity', 'N/A')}% | 
                Wiatr: {weather.get('wind_speed', 'N/A')} m/s
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 5px;">📍 {weather.get('city', 'Nieznane miasto')}</div>
        </div>
        '''
    
    def _generate_articles_html(self, articles: List[Dict[str, Any]]) -> str:
        """Generuje HTML dla sekcji artykułów"""
        if not articles:
            return '<p style="color: #666;">Brak nowych artykułów do przeczytania.</p>'
        
        html = ''
        for article in articles:
            link_html = f'<a href="{article["link"]}" style="color: #007AFF; text-decoration: none;">{article["name"]}</a>' if article['link'] else article['name']
            author_html = f'<div style="color: #666; font-size: 14px; margin-top: 3px;">Autor: {article["author"]}</div>' if article['author'] else ''
            
            html += f'''
            <div style="margin-bottom: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 8px;">
                <div style="font-weight: 500;">{link_html}</div>
                {author_html}
            </div>
            '''
        return html
    
    def _generate_quote_html(self, quote: Dict[str, str]) -> str:
        """Generuje HTML dla sekcji cytatu"""
        if not quote:
            return '<p style="color: #666;">Brak cytatu na dziś.</p>'
        
        return f'''
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007AFF;">
            <div style="font-style: italic; font-size: 16px; margin-bottom: 10px;">
                "{quote.get('quote', 'Brak cytatu')}"
            </div>
            <div style="font-weight: 500; color: #666;">
                — {quote.get('author', 'Nieznany autor')}
            </div>
            {f'<div style="font-size: 14px; color: #999; margin-top: 5px;">{quote.get("source", "")}</div>' if quote.get('source') else ''}
        </div>
        '''
    
    def _generate_errors_html(self, errors: List[str]) -> str:
        """Generuje HTML dla sekcji błędów"""
        if not errors:
            return ''
        
        html = '''
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <h3 style="margin: 0 0 10px 0; color: #856404;">⚠️ Uwagi systemowe</h3>
        '''
        
        for error in errors:
            html += f'<div style="color: #856404; font-size: 14px; margin-bottom: 5px;">• {error}</div>'
        
        html += '</div>'
        return html


def main():
    """Główna funkcja skryptu"""
    logger.info("=== Rozpoczynam generowanie daily digest ===")
    
    try:
        # Inicjalizacja integracji
        calendar = GoogleCalendarIntegration()
        weather = WeatherIntegration()
        notion = NotionIntegration()
        quotes = QuotesManager()
        ai_generator = AIContentGenerator()
        email_sender = EmailSender()
        
        # Zbieranie danych
        logger.info("Pobieranie danych...")
        
        events = calendar.get_today_events()
        logger.info(f"Pobrano {len(events)} wydarzeń z kalendarza")
        
        weather_data = weather.get_weather_forecast()
        logger.info(f"Pobrano dane pogodowe: {weather_data.get('description', 'brak')}")
        
        articles = notion.get_articles_not_started()
        logger.info(f"Pobrano {len(articles)} artykułów z Notion")
        
        quote = quotes.get_random_quote()
        logger.info(f"Wylosowano cytat: {quote.get('author', 'Nieznany')}")
        
        # Zbieranie wszystkich błędów
        all_errors = []
        all_errors.extend(calendar.errors)
        all_errors.extend(weather.errors)
        all_errors.extend(notion.errors)
        
        # Przygotowanie danych dla AI
        ai_data = {
            'events': events,
            'weather': weather_data,
            'articles': articles,
            'quote': quote
        }
        
        # Generowanie spersonalizowanej treści
        logger.info("Generowanie spersonalizowanej treści...")
        ai_intro = ai_generator.generate_personalized_content(ai_data)
        
        # Przygotowanie danych do wysłania
        email_content = {
            'ai_intro': ai_intro,
            'events': events,
            'weather': weather_data,
            'articles': articles,
            'quote': quote,
            'errors': all_errors
        }
        
        # Wysłanie e-maila
        logger.info("Wysyłanie e-maila...")
        email_sender.send_daily_digest(email_content)
        
        logger.info("=== Daily digest zakończony sukcesem ===")
        
    except Exception as e:
        logger.error(f"Krytyczny błąd w daily digest: {e}")
        
        # Spróbuj wysłać e-mail z informacją o błędzie
        try:
            error_content = {
                'ai_intro': f"Napotkano problemy podczas przygotowywania dzisiejszego podsumowania: {str(e)}",
                'events': [],
                'weather': {},
                'articles': [],
                'quote': {},
                'errors': [f"Krytyczny błąd: {str(e)}"]
            }
            
            email_sender = EmailSender()
            email_sender.send_daily_digest(error_content)
            
        except Exception as email_error:
            logger.error(f"Nie udało się wysłać e-maila z błędem: {email_error}")
        
        sys.exit(1)


if __name__ == "__main__":
    main() 