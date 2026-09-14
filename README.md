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

- **Two ways to write a procedure**, both first-class:
  1. A bare statement body, no wrapper at all — the original, and still
     permanent, form. Every History entry saved before `CREATE PROCEDURE`
     support existed is stored exactly this way and keeps working forever.
  2. `CREATE PROCEDURE name(params) BEGIN ... END` — params are
     `[IN | OUT | INOUT] name TYPE`, mode defaults to `IN` when omitted.
     `IN`/`INOUT` values come from the caller (the same mechanism a bare
     body's externally-referenced variables already use); `OUT` auto-seeds
     to `null` if the caller didn't supply one. Every variable in the trace
     carries an `isOutput` flag, `true` only for a declared `OUT`/`INOUT`
     param, so its final value is identifiable as this procedure's output.
- **Functions**: `CREATE FUNCTION name(params) RETURNS type BEGIN ...
  END` — params are plain `name TYPE`, no mode. `RETURN expr;` is a
  statement like any other (valid inside `IF`/`WHILE` too); executing one
  stops the function immediately — no statement after it ever runs, even
  later ones in the same block — and its DebugStep carries a `returnValue`
  field. A function body that completes without ever executing a `RETURN`
  is a clear `InterpreterError`, never a silent `null`.
- **Variables**: `DECLARE name TYPE [DEFAULT expr];`, `SET name = expr;`
- **Control flow**: `IF ... THEN ... [ELSE ...] END IF;`,
  `WHILE ... DO ... END WHILE;`, `CASE ... WHEN ... THEN ... [ELSE ...]
  END CASE;` (both the simple `CASE expr WHEN val THEN ...` and searched
  `CASE WHEN cond THEN ...` forms), and `[label:] LOOP ... END LOOP
  [label];` with `LEAVE [label];` to exit it — `LOOP` has no condition
  of its own (unlike `WHILE`), so `LEAVE` is the only way out; an
  optional label lets a `LEAVE` deep inside nested loops name *which*
  enclosing one to break, not just the innermost.
- **Procedure calls**: `CALL name(arg1, arg2, ...);` (a procedure calling
  another procedure, including itself) and, inside an expression,
  `name(arg1, ...)` to call a `CREATE FUNCTION` and use its `RETURN`ed
  value — see `backend/app/parser.py`'s module docstring for the full
  design (scope isolation, recursion, the call-depth guard).
- **Expressions**: `+ - * /`, comparisons `> < = !=`, string/number
  literals, parentheses — no `>=`/`<=`
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
- **User-created tables**: `CREATE TABLE name (col TYPE [NOT NULL]
  [PRIMARY KEY], ...);`, `INSERT INTO name [(col, ...)] VALUES (expr,
  ...);`, `UPDATE name SET col = expr [, col = expr]* [WHERE expr];`,
  `DELETE FROM name [WHERE expr];`. `TYPE` is unvalidated, same as a
  `DECLARE`'s own type; `NOT NULL`/`PRIMARY KEY` ARE enforced at
  runtime. A table's rows are simulated entirely in memory for the life
  of one run (never real SQLite, and never queryable from a cursor's
  `SELECT` — see "Cursors" below, which still only ever sees the fixed
  `products` table). `WHERE` is one ordinary expression (no `AND`/`OR`
  chaining, same limit an `IF`/`WHILE` condition already has) that can
  reference both a row's own columns and any variable already in
  scope. `NULL` is also a new expression literal, most useful as an
  explicit `INSERT` value.

Not supported at all: `ELSEIF` chaining (nest another `IF` inside the
`ELSE` instead), `>=`/`<=`, cursor parameters, transactions, `AND`/`OR`
in an expression (including a table's own `WHERE`), and anything not
listed above. The in-app **Theory** tab documents each supported piece
with a runnable example; the sample library's **ComputeTax** procedure
demonstrates a declared `OUT` param, **ProductPriceTotal** /
**SafeAverageWithHandlers** are runnable demonstrations of cursors and
exception handling respectively, and **ManageInventory** demonstrates
`CREATE TABLE`/`INSERT`/`UPDATE`/`DELETE` together against one
user-created table. All samples use the full `CREATE PROCEDURE(...)
BEGIN...END` wrapper — a deliberate choice for consistency with the
syntax the Theory tab teaches, made once `CREATE PROCEDURE` support
existed and migrating was a pure find-and-replace; see
`frontend/src/samples.js`'s header comment for the full rationale. The
bare, wrapper-less form isn't gone — it's simply no longer what any
*sample* demonstrates, since it's the backward-compatibility path, not
the recommended way to write a new one.
