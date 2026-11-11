import hashlib
import hmac
import re
import secrets
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

import database

BASE_DIR = Path(__file__).resolve().parent
MIN_YEAR = 1
MAX_YEAR = 2100
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 254
SESSION_DAYS = 30
SESSION_COOKIE = "session"
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
EMAIL_TAKEN = "Konto z tym adresem e-mail już istnieje."
EMAIL_INVALID = "Podaj poprawny adres e-mail."


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.init_db()
    yield


app = FastAPI(title="Biblioteka", lifespan=lifespan)
app.mount("/css", StaticFiles(directory=BASE_DIR / "css"), name="css")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request) -> sqlite3.Row | None:
    token = request.cookies.get(SESSION_COOKIE)
    return database.get_session_user(hash_token(token)) if token else None


def user_context(request: Request) -> dict[str, sqlite3.Row | None]:
    return {"current_user": current_user(request)}


templates = Jinja2Templates(
    directory=BASE_DIR / "templates", context_processors=[user_context]
)


def cover_hue(text: str) -> int:
    """Give each book a stable cover colour derived from its title."""
    return sum(ord(character) * 37 for character in text) % 360


templates.env.filters["hue"] = cover_hue


def find_book(book_id: int) -> dict:
    book = database.get_book(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono książki")
    return dict(book)


def parse_int(value: str, minimum: int, maximum: int) -> int | None:
    try:
        number = int(value)
    except ValueError:
        return None
    return number if minimum <= number <= maximum else None


EMPTY_BOOK = {
    "title": "",
    "author": "",
    "genre": "",
    "year": "",
    "rating": "",
    "description": "",
}


def validate_book(
    title: str, author: str, genre: str, year: str, rating: str, description: str
) -> tuple[dict, dict[str, str]]:
    """Clean the submitted book fields and return them with any errors.

    Without errors, year and rating are ints; otherwise they keep the
    submitted strings so the form can be re-rendered as typed.
    """
    title, author, genre = title.strip(), author.strip(), genre.strip()
    description = description.replace("\r\n", "\n").strip()
    parsed_year = parse_int(year, MIN_YEAR, MAX_YEAR)
    parsed_rating = parse_int(rating, 1, 5)

    errors: dict[str, str] = {}
    if not title:
        errors["title"] = "Podaj tytuł."
    if not author:
        errors["author"] = "Podaj autora."
    if not genre:
        errors["genre"] = "Podaj gatunek."
    if parsed_year is None:
        errors["year"] = f"Podaj rok od {MIN_YEAR} do {MAX_YEAR}."
    if parsed_rating is None:
        errors["rating"] = "Wybierz ocenę od 1 do 5."
    if not description:
        errors["description"] = "Dodaj opis."

    values = {
        "title": title,
        "author": author,
        "genre": genre,
        "year": year if errors else parsed_year,
        "rating": rating if errors else parsed_rating,
        "description": description,
    }
    return values, errors


def scrypt_digest(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"{salt.hex()}${scrypt_digest(password, salt).hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split("$")
    return hmac.compare_digest(
        scrypt_digest(password, bytes.fromhex(salt)), bytes.fromhex(digest)
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return len(email) <= MAX_EMAIL_LENGTH and bool(EMAIL_PATTERN.fullmatch(email))


def start_session(user_id: int) -> RedirectResponse:
    """Log the user in and send them to the account page."""
    token = secrets.token_urlsafe(32)
    database.create_session(hash_token(token), user_id, SESSION_DAYS)
    response = RedirectResponse("/kabinet", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "error.html", {"status": exc.status_code}, status_code=exc.status_code
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "index.html", {"books": database.get_books()}
    )


@app.get("/o-firmie", response_class=HTMLResponse)
def about(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "about.html", {})


@app.get("/books/{book_id:int}", response_class=HTMLResponse)
def book_detail(request: Request, book_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "book.html", {"book": find_book(book_id)}
    )


@app.get("/books/{book_id:int}/edit", response_class=HTMLResponse)
def edit_form(request: Request, book_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "edit.html", {"book": find_book(book_id), "errors": {}}
    )


@app.post("/books/{book_id:int}/edit", response_class=HTMLResponse, response_model=None)
def edit_submit(
    request: Request,
    book_id: int,
    title: str = Form(""),
    author: str = Form(""),
    genre: str = Form(""),
    year: str = Form(""),
    rating: str = Form(""),
    description: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    book = find_book(book_id)
    values, errors = validate_book(title, author, genre, year, rating, description)
    if errors:
        return templates.TemplateResponse(
            request,
            "edit.html",
            {"book": book | values, "errors": errors},
            status_code=422,
        )

    database.update_book(book_id, **values)
    return RedirectResponse(f"/books/{book_id}?saved=1", status_code=303)


@app.get("/books/new", response_class=HTMLResponse, response_model=None)
def new_book_form(request: Request) -> HTMLResponse | RedirectResponse:
    if current_user(request) is None:
        return RedirectResponse("/logowanie", status_code=303)
    return templates.TemplateResponse(
        request, "new.html", {"book": EMPTY_BOOK, "errors": {}}
    )


@app.post("/books/new", response_class=HTMLResponse, response_model=None)
def new_book_submit(
    request: Request,
    title: str = Form(""),
    author: str = Form(""),
    genre: str = Form(""),
    year: str = Form(""),
    rating: str = Form(""),
    description: str = Form(""),
) -> HTMLResponse | RedirectResponse:
    if current_user(request) is None:
        return RedirectResponse("/logowanie", status_code=303)

    values, errors = validate_book(title, author, genre, year, rating, description)
    if errors:
        return templates.TemplateResponse(
            request,
            "new.html",
            {"book": values, "errors": errors},
            status_code=422,
        )

    book_id = database.create_book(**values)
    return RedirectResponse(f"/books/{book_id}?added=1", status_code=303)


@app.get("/rejestracja", response_class=HTMLResponse, response_model=None)
def register_form(request: Request) -> HTMLResponse | RedirectResponse:
    if current_user(request):
        return RedirectResponse("/kabinet", status_code=303)
    return templates.TemplateResponse(
        request, "register.html", {"email": "", "errors": {}}
    )


@app.post("/rejestracja", response_class=HTMLResponse, response_model=None)
def register_submit(
    request: Request, email: str = Form(""), password: str = Form("")
) -> HTMLResponse | RedirectResponse:
    email = normalize_email(email)

    errors: dict[str, str] = {}
    if not is_valid_email(email):
        errors["email"] = EMAIL_INVALID
    if len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = f"Hasło musi mieć co najmniej {MIN_PASSWORD_LENGTH} znaków."
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = f"Hasło może mieć najwyżej {MAX_PASSWORD_LENGTH} znaków."

    user_id = None
    if not errors:
        user_id = database.create_user(email, hash_password(password))
        if user_id is None:
            errors["email"] = EMAIL_TAKEN

    if user_id is None:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"email": email, "errors": errors},
            status_code=422,
        )
    return start_session(user_id)


@app.get("/logowanie", response_class=HTMLResponse, response_model=None)
def login_form(request: Request) -> HTMLResponse | RedirectResponse:
    if current_user(request):
        return RedirectResponse("/kabinet", status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"email": "", "failed": False}
    )


@app.post("/logowanie", response_class=HTMLResponse, response_model=None)
def login_submit(
    request: Request, email: str = Form(""), password: str = Form("")
) -> HTMLResponse | RedirectResponse:
    email = normalize_email(email)
    user = database.get_user_by_email(email)
    if (
        user is None
        or len(password) > MAX_PASSWORD_LENGTH
        or not verify_password(password, user["password_hash"])
    ):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"email": email, "failed": True},
            status_code=422,
        )
    return start_session(user["id"])


@app.get("/kabinet", response_class=HTMLResponse, response_model=None)
def account(request: Request) -> HTMLResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/logowanie", status_code=303)
    return templates.TemplateResponse(
        request, "account.html", {"user": user, "email": user["email"], "errors": {}}
    )


@app.post("/kabinet/email", response_class=HTMLResponse, response_model=None)
def change_email(
    request: Request, email: str = Form("")
) -> HTMLResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/logowanie", status_code=303)

    email = normalize_email(email)
    errors: dict[str, str] = {}
    if not is_valid_email(email):
        errors["email"] = EMAIL_INVALID
    elif not database.update_user_email(user["id"], email):
        errors["email"] = EMAIL_TAKEN

    if errors:
        return templates.TemplateResponse(
            request,
            "account.html",
            {"user": user, "email": email, "errors": errors},
            status_code=422,
        )
    return RedirectResponse("/kabinet?saved=1", status_code=303)


@app.post("/wyloguj")
def logout(request: Request) -> RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        database.delete_session(hash_token(token))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
