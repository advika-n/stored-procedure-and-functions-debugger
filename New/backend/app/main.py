from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import demo_db, history
from app.explainer import answer_question, explain_step
from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.tokenizer import TokenizerError, tokenize

app = FastAPI(title="Stored Procedure and Functions Debugger API")

# No eager history.init_db() call here on purpose -- app/history.py's
# _connect() creates the debug_history table lazily on first real use,
# so the SQLite file only ever appears at whichever DB_PATH is active
# when a request actually needs it (matters for test isolation, since
# tests monkeypatch DB_PATH before making any request).

# Allow the Vite dev server to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


class DebugRequest(BaseModel):
    code: str
    params: dict = Field(default_factory=dict)
    name: str | None = None  # e.g. the sample picker's name, if loaded from one


def _error_response(stage: str, message: str, line: int | None) -> HTTPException:
    """Build a 400 with a message and line number a client can act on."""
    return HTTPException(
        status_code=400,
        detail={"stage": stage, "message": message, "line": line},
    )


@app.post("/debug")
def debug(request: DebugRequest):
    """Run source through tokenize -> parse -> interpret and return the
    resulting DebugStep trace, or a 400 pinpointing where it broke."""
    try:
        tokens = tokenize(request.code)
    except TokenizerError as exc:
        raise _error_response("tokenize", str(exc), exc.line) from exc

    try:
        ast = parse(tokens)
    except ParserError as exc:
        raise _error_response("parse", str(exc), exc.line) from exc

    # A fresh, small demo database (see app/demo_db.py) so cursor
    # statements have something to query without a schema-authoring
    # feature -- closed again once this run finishes either way.
    conn = demo_db.create_demo_connection()
    try:
        steps = run(ast, request.params, db_connection=conn)
    except InterpreterError as exc:
        raise _error_response("interpret", str(exc), exc.line) from exc
    finally:
        conn.close()

    step_dicts = [step.to_dict() for step in steps]

    # Deliberate scope choice: only successful runs are saved to history.
    # A tokenize/parse/interpret failure returns above via _error_response
    # and never reaches this line, so nothing broken gets logged.
    history.save_run(
        code=request.code,
        params=request.params,
        steps=step_dicts,
        ast=ast,
        name=request.name,
    )

    # `ast` is included so the frontend can render a control-flow diagram
    # from the procedure's structure, independent of the linear step trace.
    return {"ast": ast, "steps": step_dicts}


class ExplainRequest(BaseModel):
    step: dict
    previousVariables: dict | None = None


@app.post("/explain")
def explain(request: ExplainRequest):
    """One plain-English sentence for a single DebugStep, backed by
    Gemini when available and a deterministic generator otherwise.
    Cached per (step, previousVariables) -- see app/explainer.py."""
    return explain_step(request.step, request.previousVariables)


class AskRequest(BaseModel):
    code: str
    step: dict
    question: str


@app.post("/ask")
def ask(request: AskRequest):
    """Answer a free-form question about the current debug state (e.g.
    "why did it take this branch"), grounded in the full procedure source
    plus the current step's line and variable state. Distinct from
    /explain: this is user-initiated and not cached, since each question
    is answered fresh. No template fallback -- an open-ended question has
    no sensible deterministic answer, so a Gemini failure surfaces as a
    502 the frontend can show as an error instead of a fabricated one."""
    try:
        answer = answer_question(request.code, request.step, request.question)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Couldn't reach Gemini to answer that question. Check that GEMINI_API_KEY is set and valid, then try again.",
        ) from exc
    return {"answer": answer}


@app.get("/history")
def get_history():
    """Summaries of the most recent successful runs (most recent
    first), capped at history.HISTORY_LIMIT."""
    return {"runs": history.list_runs()}


@app.get("/history/{run_id}")
def get_history_entry(run_id: int):
    """One saved run's full code, params, AST, and step trace, so the
    frontend can replay it without re-running the interpreter."""
    run = history.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No history entry with id {run_id}")
    return run


@app.delete("/history/{run_id}")
def delete_history_entry(run_id: int):
    deleted = history.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No history entry with id {run_id}")
    return {"deleted": run_id}


@app.delete("/history")
def clear_history():
    count = history.clear_all()
    return {"cleared": count}
