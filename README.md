# Biblioteka

A simple book blog built with FastAPI. Pages are rendered on the server with Jinja2, the user interface is in Polish, and the whole site works without JavaScript.

## Features

- a book list and a details page for each book,
- adding and editing books, with form validation,
- registration, login and logout (passwords hashed with scrypt, sessions in an `httponly` cookie),
- an account page (`/kabinet`) where users can change their email address,
- book covers drawn with CSS gradients, and a dark mode through `prefers-color-scheme`.

## Tech stack

- Python 3.13, [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
- Jinja2 (templates in `templates/`)
- SQLite through the standard `sqlite3` module, with no ORM

## Getting started

On Windows, in PowerShell, from the project directory:

```powershell
# Create a virtual environment
py -3.13 -m venv .venv

# Install dependencies
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Start the dev server at http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

On Linux and macOS, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

The `books.db` database file is created on first start and filled with sample books.

## Project structure

```
main.py           routes, form validation, Jinja2 setup
database.py       data access (sqlite3), schema and sample data
templates/        HTML templates (base.html, _macros.html and the pages)
css/style.css     the only stylesheet
requirements.txt  dependencies
```

## Main routes

| Route | Description |
| --- | --- |
| `/` | book list |
| `/books/{id}` | book details |
| `/books/{id}/edit` | edit a book |
| `/books/new` | add a book (login required) |
| `/rejestracja`, `/logowanie` | register, log in |
| `/kabinet` | account page |
| `/o-firmie` | about page |
