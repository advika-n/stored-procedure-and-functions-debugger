# Stored Procedure and Functions Debugger

Monorepo with a Python (FastAPI) backend and a React (Vite) frontend.

```
.
├── backend/     FastAPI app, exposes GET /health
└── frontend/    React + Vite app, fetches /health on load
```

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Backend

```bash
cd backend
python -m venv .venv

# Activate the virtual environment
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Optional: enables Gemini-generated step explanations (POST /explain).
# Without this, /explain still works, just via a deterministic template
# fallback instead of a real LLM call.
cp .env.example .env   # then fill in GEMINI_API_KEY

uvicorn app.main:app --reload --port 8000
```

The API is now running at http://127.0.0.1:8000. Check it directly:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

## Frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173 (Vite may pick a different port if that
one is busy). It fetches `/health` on load and displays the backend's
response. During development, Vite proxies requests to `/health` through to
the backend at `http://127.0.0.1:8000` (see `frontend/vite.config.js`), and
the backend's CORS settings additionally allow direct calls from
`http://localhost:5173` (see `backend/app/main.py`).

## Running both

Start the backend first, then the frontend, in two terminals as shown above.
Once both are running, open the frontend URL in a browser — you should see
`{"status":"ok"}` displayed on the page.

## Supported grammar & scope

The interpreter runs a small procedural-SQL subset, not full MySQL/PL-SQL.
Supported:

- **Variables**: `DECLARE name TYPE [DEFAULT expr];`, `SET name = expr;`
- **Control flow**: `IF ... THEN ... [ELSE ...] END IF;`,
  `WHILE ... DO ... END WHILE;`
- **Expressions**: `+ - * /`, comparisons `> < = !=`, string/number
  literals, parentheses — no `>=`/`<=`, no procedure parameters
- **Cursors** (MySQL-style): `DECLARE cur CURSOR FOR SELECT ...;`,
  `OPEN`/`FETCH ... INTO ...`/`CLOSE`. The embedded `SELECT` is captured
  as raw text and run against SQLite as-is — it isn't parsed by this
  interpreter's own grammar, so only single-character comparisons
  (`= > < !=`) round-trip correctly inside its `WHERE` clause. Every
  `/debug` run gets a small, fixed, auto-seeded demo table for free —
  `products(name, price)`, 3 rows (Widget/10, Gadget/25, Gizmo/15) — see
  `backend/app/demo_db.py`. There's no schema-editing feature, so a
  cursor-based procedure you write yourself needs to query that same
  table. `cur%FOUND` / `cur%NOTFOUND` are also supported as a pragmatic,
  deliberately asymmetric reading of Oracle's cursor-attribute syntax —
  see `backend/app/interpreter.py`'s module docstring for exactly what
  each means and why.
- **Exception handling**: `DECLARE CONTINUE HANDLER FOR condition
  statement;` — exactly two conditions, **`NOT_FOUND`** (a `FETCH` past
  the last row) and **`DIVISION_BY_ZERO`**, nothing else. Only
  `CONTINUE` handlers (resume at the next statement) — no `EXIT`
  handlers, no `SQLEXCEPTION`/named conditions, no `BEGIN...END` handler
  bodies (a handler's action is one statement). `NOT_FOUND` is always
  non-fatal, handled or not; `DIVISION_BY_ZERO` only becomes non-fatal
  once a handler is actually registered for it — unhandled, it still
  aborts the run exactly as it always did.

Not supported at all: stored functions/`RETURN`, `CASE`, `LOOP`/`LEAVE`,
cursor parameters, transactions, and anything not listed above. The
in-app **Theory** tab documents each supported piece with a runnable
example; the sample library's **ProductPriceTotal** and
**SafeAverageWithHandlers** procedures are runnable demonstrations of
cursors and exception handling respectively.
