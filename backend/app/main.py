from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import history, report, user_db
from app.advisor import analyze as analyze_anti_patterns
from app.explainer import answer_question, explain_step
from app.interpreter import InterpreterError, run
from app.parser import ParserError, parse
from app.practice import generate_practice_questions
from app.sql_console import SqlExecutionError, execute_sql
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

    # SQL Anti-Pattern Advisor: a static pass over the AST alone (see
    # app/advisor.py), computed here -- right after a successful parse,
    # reusing the `ast` this handler already has to build for the
    # frontend's flowchart -- rather than a separate "Analyze" endpoint.
    # Deliberately does not depend on `steps` below in any way: it would
    # be just as valid to compute even if interpretation then failed,
    # though today it's only returned alongside a successful run (see
    # HANDOFF.md for that scope note).
    issues = analyze_anti_patterns(ast)

    # The persistent, on-disk user database (see app/user_db.py) so
    # cursor statements query the same data the SQL Console reads and
    # writes -- closed again once this run finishes either way.
    conn = user_db.get_connection()
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
    # `issues` is the Anti-Pattern Advisor's findings for this same `ast`.
    return {"ast": ast, "steps": step_dicts, "issues": issues}


class ReportRequest(BaseModel):
    format: str  # "pdf" | "docx" | "txt"
    code: str
    params: dict = Field(default_factory=dict)
    name: str | None = None  # same meaning as DebugRequest.name -- sample name if loaded from one
    steps: list[dict]  # the exact DebugStep trace a prior /debug call already returned
    flowchartImage: str | None = None  # client-rasterized PNG of the Mermaid diagram (data URL or raw base64); PDF/DOCX only


@app.post("/debug/report")
def debug_report(request: ReportRequest):
    """Generate a downloadable report (PDF/Document/Text) from a debug
    run's data. Deliberately stateless and re-execution-free: the caller
    (the Debugger page, right after a /debug call) already has the full
    DebugStep trace in hand and sends it back here as-is -- this endpoint
    never re-parses or re-interprets the source, it only formats data the
    frontend already has. See app/report.py for the actual rendering."""
    if request.format not in ("pdf", "docx", "txt"):
        raise HTTPException(status_code=400, detail="format must be one of: pdf, docx, txt")
    if not request.steps:
        raise HTTPException(status_code=400, detail="steps must be a non-empty DebugStep list from a completed /debug run")

    procedure_name = history.derive_procedure_name(request.code, request.name)
    flowchart_png_bytes = report.decode_flowchart_image(request.flowchartImage)

    try:
        content, content_type, filename = report.generate_report(
            fmt=request.format,
            code=request.code,
            params=request.params,
            procedure_name=procedure_name,
            steps=request.steps,
            flowchart_png_bytes=flowchart_png_bytes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Could not generate the {request.format} report: {exc}"
        ) from exc

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SqlExecuteRequest(BaseModel):
    sql: str


@app.post("/sql/execute")
def sql_execute(request: SqlExecuteRequest):
    """SQL Console: run arbitrary SQL as-is against app.user_db's
    persistent database, straight through the sqlite3 driver -- NOT
    through this project's own tokenize/parse/interpret pipeline (see
    app/sql_console.py). Used by the frontend's merged SQL Console page
    (see frontend/src/pages/SqlConsolePage.jsx) whenever input doesn't
    parse as a procedure/function but looks like plain SQL, and directly
    by SqlStatement's own execution inside a procedure body (see
    app/interpreter.py's `_exec_sql_statement`, which calls the shared
    `execute_sql_on_connection` this endpoint's own `execute_sql` wraps,
    not this HTTP route itself). Returns column names + rows for a
    SELECT, or a rows-affected summary for a write/DDL statement. SQLite
    errors come back as a clean 400 message, never a raw traceback."""
    try:
        return execute_sql(request.sql)
    except SqlExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


class PracticeGenerateRequest(BaseModel):
    difficulty: str  # "easy" | "medium" | "hard"
    numQuestions: int = Field(ge=1, le=15)


@app.post("/practice/generate")
def practice_generate(request: PracticeGenerateRequest):
    """`numQuestions` Gemini-generated, competitive-exam-style
    multiple-choice questions at the requested difficulty, for the
    standalone AI Practice page. See app/practice.py for prompt/parsing
    details. Unlike the old /quiz/generate this replaces, a Gemini
    failure never surfaces as an error here -- app/practice.py always
    falls back to a hardcoded question bank, so this endpoint only ever
    500s on a genuine bug (a malformed difficulty already caught below)."""
    if request.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty must be 'easy', 'medium', or 'hard'")

    questions = generate_practice_questions(request.difficulty, request.numQuestions)
    return {"questions": questions}


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
