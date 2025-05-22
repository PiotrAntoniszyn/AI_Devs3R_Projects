# 📅 Daily Digest - Automatyczne codzienne podsumowanie

Skrypt w Pythonie, który codziennie o 7:45 wysyła spersonalizowane podsumowanie dnia na e-mail, zawierające:
- Wydarzenia z Google Calendar
- Prognozę pogody z OpenWeatherMap
- Artykuły z Notion (ze zmianą statusu)
- Losowy cytat dnia
- Treść wygenerowaną przez AI (GPT-4)

## ✨ Funkcje

- 🗓️ **Integracja z Google Calendar** - pobiera wydarzenia na dziś
- 🌤️ **Prognoza pogody** - aktualne dane z OpenWeatherMap API
- 📚 **Zarządzanie artykułami** - pobiera z Notion i zmienia status na "Done"
- 💭 **Cytaty dnia** - losowy cytat z bazy 30+ inspirujących cytatów
- 🤖 **AI Content Generation** - spersonalizowana treść generowana przez GPT-4
- 📧 **Piękny HTML e-mail** - nowoczesny szablon w stylu Apple
- 🔄 **Retry mechanism** - 3 próby dla każdego API
- 📝 **Pełne logowanie** - szczegółowe logi błędów i działań
- ⏰ **Gotowy do cron** - łatwa automatyzacja na serwerze VPS

## 🚀 Szybkie uruchomienie

### 1. Instalacja zależności

```bash
# Sklonuj projekt
cd dAIly_digest

# Zainstaluj zależności Python
pip install -r requirements.txt
```

### 2. Konfiguracja

1. **Skopiuj plik konfiguracyjny:**
   ```bash
   cp env_example.txt .env
   ```

2. **Wypełnij zmienne środowiskowe w `.env`:**

#### 📧 Gmail Configuration
- Włącz 2FA w swoim koncie Gmail
- Wygeneruj hasło aplikacji: https://support.google.com/accounts/answer/185833
- Wprowadź dane w `.env`:
  ```
  GMAIL_EMAIL=twoj.email@gmail.com
  GMAIL_APP_PASSWORD=twoje hasło aplikacji
  RECIPIENT_EMAIL=odbiorca@gmail.com
  ```

#### 📅 Google Calendar API
1. Przejdź do [Google Cloud Console](https://console.cloud.google.com/)
2. Utwórz nowy projekt lub wybierz istniejący
3. Włącz Google Calendar API
4. Utwórz credentials (OAuth 2.0)
5. Pobierz plik `credentials.json` i umieść w folderze projektu
6. Wprowadź w `.env`:
   ```
   GOOGLE_CREDENTIALS_PATH=credentials.json
   GOOGLE_CALENDAR_ID=primary
   ```

#### 🌤️ OpenWeatherMap API
1. Zarejestruj się na https://openweathermap.org/api
2. Pobierz darmowy klucz API
3. Wprowadź w `.env`:
   ```
   OPENWEATHERMAP_API_KEY=twój_klucz_api
   WEATHER_CITY=Warsaw
   ```

#### 📚 Notion API
1. Utwórz nową integrację: https://developers.notion.com/docs/getting-started
2. Skopiuj token integracji
3. Udostępnij swoją bazę danych integracji
4. Skopiuj ID bazy danych (z URL)
5. Wprowadź w `.env`:
   ```
   NOTION_TOKEN=secret_twój_token
   NOTION_DATABASE_ID=id_twojej_bazy
   ```

   **Struktura bazy Notion:**
   - `Name` (Title) - nazwa artykułu
   - `Link` (URL) - link do artykułu
   - `Author` (Text/Select) - autor artykułu
   - `Status` (Select) - status z opcjami "Not started" i "Done"

#### 🤖 OpenAI API
1. Utwórz konto na https://platform.openai.com/
2. Wygeneruj klucz API
3. Wprowadź w `.env`:
   ```
   OPENAI_API_KEY=sk-twój_klucz_api
   ```

### 3. Pierwsze uruchomienie

```bash
# Testowe uruchomienie
python daily_digest.py
```

Przy pierwszym uruchomieniu:
- Google Calendar otworzy przeglądarkę do autoryzacji
- Skrypt utworzy plik `token.json` z tokenem dostępu
- Zostanie wygenerowany plik `daily_digest.log` z logami

## ⏰ Automatyzacja z cron

### Linux/macOS

1. **Otwórz crontab:**
   ```bash
   crontab -e
   ```

2. **Dodaj wpis dla codziennego uruchomienia o 7:45:**
   ```bash
   45 7 * * * cd /ścieżka/do/dAIly_digest && /usr/bin/python3 daily_digest.py >> cron.log 2>&1
   ```

3. **Alternatywnie, z użyciem venv:**
   ```bash
   45 7 * * * cd /ścieżka/do/dAIly_digest && /ścieżka/do/venv/bin/python daily_digest.py >> cron.log 2>&1
   ```

### Windows (Task Scheduler)

1. Otwórz Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 7:45 AM
4. Action: Start Program
   - Program: `python`
   - Arguments: `daily_digest.py`
   - Start in: `C:\ścieżka\do\dAIly_digest`

## 📁 Struktura plików

```
dAIly_digest/
├── daily_digest.py        # Główny skrypt
├── email_template.html    # Szablon HTML e-maila
├── quotes.json           # Baza cytatów
├── requirements.txt      # Zależności Python
├── env_example.txt       # Przykład konfiguracji
├── README.md            # Ta dokumentacja
├── .env                 # Twoja konfiguracja (do utworzenia)
├── credentials.json     # Google API credentials (do pobrania)
├── token.json          # Token Google (generowany automatycznie)
├── daily_digest.log    # Logi (generowane automatycznie)
└── cron.log            # Logi cron (opcjonalne)
```

## 🔧 Zaawansowana konfiguracja

### Dodawanie własnych cytatów

Edytuj plik `quotes.json`:
```json
{
    "quote": "Twój cytat",
    "author": "Autor",
    "source": "Źródło"
}
```

### Zmiana godziny wysyłania

Edytuj wpis w cron:
```bash
# 8:30 rano
30 8 * * *

# 18:00 wieczorem
0 18 * * *
```

### Logowanie

Skrypt automatycznie tworzy logi w:
- `daily_digest.log` - wszystkie akcje skryptu
- `cron.log` - output z cron (jeśli skonfigurowany)

Poziomy logowania: DEBUG, INFO, WARNING, ERROR

## 🚨 Rozwiązywanie problemów

### Błąd: "Brak pliku credentials.json"
- Pobierz credentials z Google Cloud Console
- Upewnij się, że plik jest w głównym folderze projektu

### Błąd: "GMAIL_APP_PASSWORD invalid"
- Użyj hasła aplikacji, nie hasła do konta
- Sprawdź czy masz włączone 2FA

### Błąd: "Notion database not found"
- Sprawdź czy integracja ma dostęp do bazy
- Zweryfikuj ID bazy danych w URL

### Błąd: "OpenAI API quota exceeded"
- Sprawdź limity na https://platform.openai.com/usage
- Rozważ upgrade planu lub zmniejsz częstotliwość

### E-mail nie dociera
- Sprawdź folder spam
- Zweryfikuj ustawienia SMTP
- Sprawdź logi: `daily_digest.log`

## 📊 Monitorowanie

### Sprawdzanie statusu cron
```bash
# Sprawdź czy cron działa
service cron status

# Zobacz ostatnie uruchomienia
grep CRON /var/log/syslog | tail -10

# Sprawdź logi aplikacji
tail -f daily_digest.log
```

### Sprawdzanie logów
```bash
# Ostatnie 20 linii logów
tail -20 daily_digest.log

# Na żywo
tail -f daily_digest.log

# Błędy
grep ERROR daily_digest.log
```

## 🔒 Bezpieczeństwo

- ❌ **NIE** umieszczaj kluczy API w kodzie
- ✅ Używaj pliku `.env` dla wszystkich sekretów
- ✅ Dodaj `.env` do `.gitignore`
- ✅ Regularnie rotuj klucze API
- ✅ Używaj kont z minimalnymi uprawnieniami

## 📄 Licencja

Ten projekt jest dostępny na licencji MIT. Możesz go swobodnie używać, modyfikować i dystrybuować.

## 🤝 Wsparcie

W przypadku problemów:
1. Sprawdź logi w `daily_digest.log`
2. Zweryfikuj konfigurację w `.env`
3. Sprawdź czy wszystkie API są aktywne
4. Przetestuj każdą integrację osobno

---

**Miłego automatyzowania! 🚀** 