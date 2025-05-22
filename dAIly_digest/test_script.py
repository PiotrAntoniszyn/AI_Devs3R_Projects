#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script dla Daily Digest
Pozwala przetestować poszczególne komponenty przed pełnym uruchomieniem
"""

import os
import sys
from dotenv import load_dotenv

def test_env_variables():
    """Testuje czy wszystkie wymagane zmienne środowiskowe są ustawione"""
    print("🔧 Testowanie zmiennych środowiskowych...")
    
    load_dotenv()
    
    required_vars = [
        'GMAIL_EMAIL',
        'GMAIL_APP_PASSWORD', 
        'RECIPIENT_EMAIL',
        'OPENWEATHERMAP_API_KEY',
        'NOTION_TOKEN',
        'NOTION_DATABASE_ID',
        'OPENAI_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Brakujące zmienne środowiskowe:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    else:
        print("✅ Wszystkie wymagane zmienne środowiskowe są ustawione")
        return True

def test_files():
    """Testuje czy wszystkie wymagane pliki istnieją"""
    print("\n📁 Testowanie plików...")
    
    required_files = [
        'quotes.json',
        'email_template.html',
        '.env'
    ]
    
    optional_files = [
        'credentials.json'  # Potrzebny dla Google Calendar
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Brakujące wymagane pliki:")
        for file in missing_files:
            print(f"   - {file}")
    else:
        print("✅ Wszystkie wymagane pliki istnieją")
    
    # Sprawdź opcjonalne pliki
    for file in optional_files:
        if os.path.exists(file):
            print(f"✅ Znaleziono opcjonalny plik: {file}")
        else:
            print(f"⚠️  Brak opcjonalnego pliku: {file} (potrzebny dla Google Calendar)")
    
    return len(missing_files) == 0

def test_quotes():
    """Testuje czy plik z cytatami jest poprawny"""
    print("\n💭 Testowanie pliku cytatów...")
    
    try:
        import json
        with open('quotes.json', 'r', encoding='utf-8') as f:
            quotes = json.load(f)
        
        if not isinstance(quotes, list):
            print("❌ Plik quotes.json powinien zawierać listę")
            return False
        
        if len(quotes) == 0:
            print("❌ Plik quotes.json jest pusty")
            return False
        
        # Sprawdź strukturę pierwszego cytatu
        first_quote = quotes[0]
        required_keys = ['quote', 'author', 'source']
        
        for key in required_keys:
            if key not in first_quote:
                print(f"❌ Brak klucza '{key}' w cytatach")
                return False
        
        print(f"✅ Plik cytatów zawiera {len(quotes)} cytatów")
        print(f"   Przykład: \"{first_quote['quote'][:50]}...\" - {first_quote['author']}")
        return True
        
    except FileNotFoundError:
        print("❌ Nie znaleziono pliku quotes.json")
        return False
    except json.JSONDecodeError:
        print("❌ Błąd parsowania pliku quotes.json")
        return False
    except Exception as e:
        print(f"❌ Błąd podczas testowania cytatów: {e}")
        return False

def test_imports():
    """Testuje czy wszystkie wymagane biblioteki są zainstalowane"""
    print("\n📦 Testowanie zależności...")
    
    required_imports = [
        ('requests', 'requests'),
        ('google.auth', 'google-auth'),
        ('google_auth_oauthlib', 'google-auth-oauthlib'),
        ('googleapiclient', 'google-api-python-client'),
        ('openai', 'openai'),
        ('dotenv', 'python-dotenv')
    ]
    
    missing_imports = []
    
    for import_name, package_name in required_imports:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name}")
            missing_imports.append(package_name)
    
    if missing_imports:
        print(f"\n❌ Brakujące pakiety. Zainstaluj przez:")
        print(f"pip install {' '.join(missing_imports)}")
        return False
    else:
        print("✅ Wszystkie wymagane pakiety są zainstalowane")
        return True

def test_openai_connection():
    """Testuje połączenie z OpenAI API"""
    print("\n🤖 Testowanie połączenia z OpenAI...")
    
    try:
        import openai
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("❌ Brak klucza OPENAI_API_KEY")
            return False
        
        client = openai.OpenAI(api_key=api_key)
        
        # Próba prostego zapytania
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=5
        )
        
        print("✅ Połączenie z OpenAI działa")
        return True
        
    except Exception as e:
        print(f"❌ Błąd połączenia z OpenAI: {e}")
        return False

def test_weather_api():
    """Testuje połączenie z OpenWeatherMap API"""
    print("\n🌤️ Testowanie OpenWeatherMap API...")
    
    try:
        import requests
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        city = os.getenv('WEATHER_CITY', 'Warsaw')
        
        if not api_key:
            print("❌ Brak klucza OPENWEATHERMAP_API_KEY")
            return False
        
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city,
            'appid': api_key,
            'units': 'metric'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        temp = data['main']['temp']
        desc = data['weather'][0]['description']
        
        print(f"✅ OpenWeatherMap API działa")
        print(f"   {city}: {temp}°C, {desc}")
        return True
        
    except Exception as e:
        print(f"❌ Błąd połączenia z OpenWeatherMap: {e}")
        return False

def main():
    """Główna funkcja testowa"""
    print("🧪 === DAILY DIGEST TEST SUITE ===\n")
    
    tests = [
        ("Zmienne środowiskowe", test_env_variables),
        ("Pliki", test_files),
        ("Cytaty", test_quotes),
        ("Zależności Python", test_imports),
        ("OpenAI API", test_openai_connection),
        ("Weather API", test_weather_api)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Błąd podczas testu '{test_name}': {e}")
            results.append((test_name, False))
    
    # Podsumowanie
    print("\n" + "="*50)
    print("📊 PODSUMOWANIE TESTÓW")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nWynik: {passed}/{total} testów przeszło pomyślnie")
    
    if passed == total:
        print("\n🎉 Wszystkie testy przeszły! Możesz uruchomić daily_digest.py")
        return True
    else:
        print(f"\n⚠️  {total - passed} testów nie przeszło. Sprawdź konfigurację.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 