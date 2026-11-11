import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "books.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    author      TEXT    NOT NULL,
    genre       TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    description TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT    NOT NULL
);
"""

SAMPLE_BOOKS = [
    (
        "Solaris",
        "Stanisław Lem",
        "Science fiction",
        1961,
        5,
        "Na stacji badawczej krążącej nad planetą pokrytą żywym oceanem naukowcy "
        "spotykają materialne ucieleśnienia własnych wspomnień.\n\n"
        "To opowieść o granicach poznania i o tym, że kontakt z czymś naprawdę "
        "obcym może okazać się niemożliwy.",
    ),
    (
        "Lalka",
        "Bolesław Prus",
        "Powieść realistyczna",
        1890,
        5,
        "Stanisław Wokulski, kupiec i dawny powstaniec, zdobywa majątek, by zbliżyć "
        "się do arystokratki Izabeli Łęckiej.\n\n"
        "W tle nieszczęśliwej miłości rozgrywa się szeroki portret Warszawy "
        "i społeczeństwa drugiej połowy XIX wieku.",
    ),
    (
        "Mistrz i Małgorzata",
        "Michaił Bułhakow",
        "Realizm magiczny",
        1967,
        5,
        "Do Moskwy przybywa tajemniczy profesor Woland ze swoją świtą, a miasto "
        "pogrąża się w chaosie.\n\n"
        "Satyra na radziecką rzeczywistość splata się tu z historią miłosną "
        "i opowieścią o Poncjuszu Piłacie.",
    ),
    (
        "Bieguni",
        "Olga Tokarczuk",
        "Proza współczesna",
        2007,
        4,
        "Fragmentaryczna powieść o podróżowaniu, ruchu i ludzkim ciele, złożona "
        "z krótkich opowieści, obserwacji i esejów.\n\n"
        "Kolejne wątki układają się w mapę świata, w którym nikt nie pozostaje "
        "długo w jednym miejscu.",
    ),
    (
        "Ostatnie życzenie",
        "Andrzej Sapkowski",
        "Fantasy",
        1993,
        4,
        "Zbiór opowiadań o wiedźminie Geralcie z Rivii, zabójcy potworów, który "
        "coraz częściej odkrywa, że najgroźniejsi bywają ludzie.\n\n"
        "Znane baśnie zostają tu przewrotnie opowiedziane na nowo.",
    ),
    (
        "Duma i uprzedzenie",
        "Jane Austen",
        "Powieść obyczajowa",
        1813,
        4,
        "Elżbieta Bennet i pan Darcy muszą przezwyciężyć własne pierwsze wrażenia "
        "i społeczne konwenanse.\n\n"
        "Błyskotliwa, ironiczna komedia o małżeństwie, pieniądzach i charakterze.",
    ),
]


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create the schema and add sample books to an empty database."""
    with closing(connect()) as connection, connection:
        connection.executescript(SCHEMA)
        count = connection.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        if count == 0:
            connection.executemany(
                "INSERT INTO books (title, author, genre, year, rating, description) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                SAMPLE_BOOKS,
            )


def get_books() -> list[sqlite3.Row]:
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT * FROM books ORDER BY updated_at DESC, id DESC"
        ).fetchall()


def get_book(book_id: int) -> sqlite3.Row | None:
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT * FROM books WHERE id = ?", (book_id,)
        ).fetchone()


def update_book(
    book_id: int,
    title: str,
    author: str,
    genre: str,
    year: int,
    rating: int,
    description: str,
) -> None:
    with closing(connect()) as connection, connection:
        connection.execute(
            """
            UPDATE books
            SET title = ?, author = ?, genre = ?, year = ?, rating = ?,
                description = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (title, author, genre, year, rating, description, book_id),
        )


def create_book(
    title: str, author: str, genre: str, year: int, rating: int, description: str
) -> int:
    """Add a book and return its id."""
    with closing(connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO books (title, author, genre, year, rating, description) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, author, genre, year, rating, description),
        )
        return cursor.lastrowid


def create_user(email: str, password_hash: str) -> int | None:
    """Add a user and return the id, or None if the email is already taken."""
    try:
        with closing(connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email: str) -> sqlite3.Row | None:
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    with closing(connect()) as connection:
        return connection.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def update_user_email(user_id: int, email: str) -> bool:
    """Change a user's email and return False if another account has it."""
    try:
        with closing(connect()) as connection, connection:
            connection.execute(
                "UPDATE users SET email = ?, updated_at = datetime('now') WHERE id = ?",
                (email, user_id),
            )
    except sqlite3.IntegrityError:
        return False
    return True


def create_session(token_hash: str, user_id: int, days: int) -> None:
    with closing(connect()) as connection, connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) "
            "VALUES (?, ?, datetime('now', ?))",
            (token_hash, user_id, f"+{days} days"),
        )


def get_session_user(token_hash: str) -> sqlite3.Row | None:
    with closing(connect()) as connection:
        return connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > datetime('now')
            """,
            (token_hash,),
        ).fetchone()


def delete_session(token_hash: str) -> None:
    with closing(connect()) as connection, connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
