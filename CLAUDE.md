# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Windows, PowerShell, run from the repository root. The global `python` is only a Microsoft Store alias, so call the virtualenv's interpreter directly.

```powershell
# Install dependencies (Python 3.13 venv in .venv)
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Run the dev server at http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The project has no test suite, linter, or build step, and is not a git repository.

## Architecture

A server-rendered FastAPI book blog with Polish-language UI. There is no JSON API and no JavaScript.

- `main.py` holds the routes, form validation, and Jinja2 setup. It calls `database.py` for all data access.
- `database.py` uses the stdlib `sqlite3` directly, with no ORM. Each function opens and closes its own connection. Use `with closing(connect()) as connection, connection:` for writes, because the second `connection` commits the transaction.
- `books.db` is created on startup by `init_db()`, which adds `SAMPLE_BOOKS` only when the table is empty. `SCHEMA` uses `CREATE TABLE IF NOT EXISTS` and there are no migrations, so a column change needs an `ALTER TABLE` or a deleted `books.db`.
- `templates/` extends `base.html`. Shared `cover` and `stars` macros are in `_macros.html`.
- `css/style.css` is the only stylesheet, served from the `/css` mount. Colours are `:root` custom properties, overridden for dark mode under `prefers-color-scheme`.

## Conventions

- Book routes use `{book_id:int}` so a non-numeric id gets the HTML 404 page. The global `StarletteHTTPException` handler renders `error.html`, and FastAPI's default JSON validation error would otherwise appear.
- The edit form follows POST/redirect/GET. On success it returns a 303 to `/books/{id}?saved=1`, which shows the saved notice. On failure it re-renders `edit.html` with status 422, an `errors` dict keyed by field name, and the submitted values.
- Form fields are declared as `str = Form("")` and validated by hand in `edit_submit`, so errors appear in the form rather than as a JSON 422. As a result `book.year` and `book.rating` may be strings when `edit.html` is re-rendered.
- A route that can return either a template or a redirect needs `response_model=None`, because FastAPI rejects a `HTMLResponse | RedirectResponse` return annotation at startup.
- Book covers have no image files. They are CSS gradients whose colour comes from the `hue` Jinja filter applied to the title.
- Description paragraphs are separated by a blank line. `edit_submit` normalizes `\r\n` to `\n`, and `book.html` splits on `\n\n`.
