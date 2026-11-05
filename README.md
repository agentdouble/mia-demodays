# MIA demo days

MIA Recommander is a six-card arcade game, served at `/recommander`.
Fictional clients, a public trigram leaderboard and one round per trigram/browser session.
The original interface is preserved; the Claude artifacts database is replaced by a small
Python WSGI API and persistent SQLite. No LLM, analytics or external font request is needed.
The game viewport blocks scrolling and page zoom gestures; the complete console scales
to fit short screens and orientation changes. The separate data-information page remains
a normal document. Asset references are content-versioned so a new release refreshes the UI.

## Development

```sh
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.txt
export APP_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
export DATABASE_PATH="$PWD/data/mia.sqlite3"
export PUBLIC_ORIGIN=http://localhost:8080
.venv/bin/gunicorn --bind 127.0.0.1:8080 --workers 2 --threads 4 app.wsgi:application
```

Open `http://localhost:8080/recommander`. Tests: `python3 -m unittest discover -s tests -v`.

## Public boundary

- Server-selected rounds; sequential answers, scores and elapsed time calculated server-side.
- Atomic unique trigram claims and idempotent answer retries.
- HttpOnly/SameSite cookies, Secure in HTTPS, exact Origin and CSRF-token validation.
- Explicit public asset allowlist: no database, environment, source or admin route exposed.
- Bounded JSON bodies, strict schemas, parameterized queries and rate limits (including failed attempts).
- Self-hosted fonts, CSP, anti-framing, no analytics and no raw IP persisted by the app.
- SQLite WAL, bounded size, consistent backup command and 30-day game retention.

There is no identity verification or sophisticated bot detection. Clearing cookies or
using another browser is possible; this demonstration is not a prize competition platform.
Trigram uniqueness can produce collisions. Do not enter real client data.

The repository uses `dev` → `stg` → `prod`; `main` is retained as the original artifact.
Each completed code change is committed/pushed. Releases are explicit, not automatic on push.
