# Biblioteka

Prosty blog o książkach napisany w FastAPI. Strony są renderowane po stronie serwera (Jinja2), interfejs jest po polsku, a całość działa bez JavaScriptu.

## Funkcje

- lista książek i strona szczegółów każdej książki,
- dodawanie i edycja książek z walidacją formularza,
- rejestracja, logowanie i wylogowanie (hasła hashowane scryptem, sesje w ciasteczku `httponly`),
- panel konta (`/kabinet`) ze zmianą adresu e-mail,
- okładki generowane z gradientów CSS, tryb ciemny przez `prefers-color-scheme`.

## Technologie

- Python 3.13, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
- Jinja2 (szablony w `templates/`)
- SQLite przez standardowy moduł `sqlite3`, bez ORM

## Uruchomienie

Windows, PowerShell, z katalogu projektu:

```powershell
# Utworzenie środowiska wirtualnego
py -3.13 -m venv .venv

# Instalacja zależności
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Serwer deweloperski na http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Na Linuksie i macOS zamiast `.venv\Scripts\python.exe` użyj `.venv/bin/python`.

Plik bazy `books.db` tworzy się automatycznie przy pierwszym starcie i jest wypełniany przykładowymi książkami.

## Struktura projektu

```
main.py           trasy, walidacja formularzy, konfiguracja Jinja2
database.py       dostęp do danych (sqlite3), schemat i przykładowe dane
templates/        szablony HTML (base.html, _macros.html i strony)
css/style.css     jedyny arkusz stylów
requirements.txt  zależności
```

## Główne adresy

| Adres | Opis |
| --- | --- |
| `/` | lista książek |
| `/books/{id}` | szczegóły książki |
| `/books/{id}/edit` | edycja książki |
| `/books/new` | dodanie książki (wymaga logowania) |
| `/rejestracja`, `/logowanie` | konto użytkownika |
| `/kabinet` | panel konta |
| `/o-firmie` | o nas |
