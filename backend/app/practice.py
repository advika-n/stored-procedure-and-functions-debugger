"""Gemini-backed competitive-exam-style practice question generation for
the standalone /practice ("AI Practice") page.

Replaces the old app/quiz.py (deleted -- see HANDOFF.md), which powered a
standalone /quiz page that no longer exists. Distinct from the
in-debugger "Predict Mode" (SqlConsolePage.jsx, internally still named
"quiz-*" in its own CSS/state -- see that file's own comment) -- this
module has nothing to do with Predict Mode and Predict Mode depends on
nothing here.

Generates `numQuestions` (1-15) multiple-choice questions at a requested
difficulty ("easy" | "medium" | "hard"), styled like competitive/
placement exam questions (GATE DBMS PYQ style, campus placement SQL
rounds) about stored procedures, functions, cursors, exception handling,
and control flow in SQL/PL-SQL.

Reuses app/explainer.py's Gemini client wiring (_get_gemini_client,
_GEMINI_MODEL) rather than duplicating the client setup -- same pattern
app/quiz.py used to follow.

Gemini is instructed to return ONLY a JSON array (no markdown fences, no
preamble) of exactly `numQuestions` objects, each with exactly 4 options,
a 0-based `correctIndex`, and a short explanation. Parsing is defensive:
an accidental ```json fence (or bare ``` fence) is stripped before
json.loads, and a parse failure triggers exactly one retry with a
stricter, lower-temperature prompt -- same two-strikes pattern app/quiz.py
used, in practice Gemini complies with the raw-JSON instruction most of
the time but not always.

Unlike /quiz (which had no fallback and surfaced a 502 on any Gemini
failure), this endpoint always returns something: if both Gemini attempts
fail (missing/invalid key, network error, rate limit, still-unparseable
JSON after the retry, ...), `generate_practice_questions` falls back to a
hardcoded, hand-written question bank (mirrors the deterministic-template
fallback pattern app/explainer.py uses for /explain), split by difficulty,
and samples `numQuestions` from it -- with replacement if more are asked
for than the bank holds at that difficulty, since 15 questions could
exceed a single difficulty's bank size.
"""

from __future__ import annotations

import json
import random
import re

from google.genai import types

from app.explainer import _GEMINI_MODEL, _get_gemini_client

DIFFICULTIES = ("easy", "medium", "hard")

_JSON_SHAPE_INSTRUCTIONS = (
    "Respond with ONLY a valid JSON array -- no markdown code fences, no "
    "```json wrapper, no preamble or commentary before or after it. "
    "Output must be the raw JSON array and nothing else. Shape:\n"
    "[\n"
    "  {\n"
    '    "question": "...",\n'
    '    "options": ["...", "...", "...", "..."],\n'
    '    "correctIndex": 0,\n'
    '    "explanation": "..."\n'
    "  }\n"
    "]\n"
    "`correctIndex` is a 0-based index into `options` (0, 1, 2, or 3). "
    "Return exactly __COUNT__ question objects, each with exactly 4 "
    "options and exactly one correct answer."
)

_DIFFICULTY_GUIDANCE = {
    "easy": (
        "EASY difficulty: straightforward recall/definition-level questions "
        "(e.g. what a keyword does, the difference between a procedure and a "
        "function, basic cursor lifecycle) -- a student who has read the "
        "material once should be able to answer without tracing code."
    ),
    "medium": (
        "MEDIUM difficulty: requires connecting two concepts or tracing a "
        "short snippet (e.g. predicting a cursor's %NOTFOUND behavior, "
        "which handler catches a given condition, the output of a short "
        "IF/WHILE snippet) -- comparable to a typical campus placement "
        "written-round SQL question."
    ),
    "hard": (
        "HARD difficulty: GATE DBMS previous-year-question style -- subtle "
        "edge cases, tricky control-flow traces, scoping/parameter-passing "
        "gotchas (IN vs OUT vs INOUT), or a multi-step trace through nested "
        "handlers/loops that requires careful reasoning, not recall."
    ),
}

def _build_system_prompt(difficulty: str, count: int) -> str:
    return (
        "You write multiple-choice competitive-exam practice questions for a "
        "student preparing for GATE (DBMS section) and campus placement SQL "
        "rounds, on the topic of stored procedures, functions, cursors, "
        "exception handling, and control flow in procedural SQL / PL-SQL: "
        "IF/ELSE, WHILE/LOOP, cursors (DECLARE/OPEN/FETCH/CLOSE, "
        "%FOUND/%NOTFOUND), exception handling (DECLARE CONTINUE/EXIT "
        "HANDLER, NOT_FOUND, DIVISION_BY_ZERO), IN/OUT/INOUT parameters, "
        "and the difference between procedures and functions (RETURN "
        "values, RETURNS type). " + _DIFFICULTY_GUIDANCE[difficulty] + " "
        f"Write {count} questions, styled like real exam/placement-test "
        "questions -- clear stems, plausible distractors (wrong options "
        "should be believable mistakes, not obviously silly), a mix of the "
        "topics above rather than clustering on one. "
        + _JSON_SHAPE_INSTRUCTIONS.replace("__COUNT__", str(count))
    )


_PROMPT_TEMPLATE = "Generate the {count} practice question(s) now."

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _strip_json_fences(text: str) -> str:
    """Strip an accidental ```json ... ``` or bare ``` ... ``` wrapper.
    Gemini is explicitly told not to do this, but it does often enough in
    practice that the parser has to tolerate it rather than assume the
    instruction was followed."""
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1).strip() if match else stripped


def _parse_practice_json(text: str, expected_count: int) -> list[dict]:
    """Parse and validate Gemini's response into exactly `expected_count`
    well-formed question dicts. Raises ValueError/json.JSONDecodeError/
    TypeError/KeyError on anything malformed -- callers decide whether to
    retry, fall back, or give up."""
    data = json.loads(_strip_json_fences(text))
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of questions")
    if len(data) != expected_count:
        raise ValueError(f"Expected exactly {expected_count} questions, got {len(data)}")

    questions = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each question must be a JSON object")
        options = item["options"]
        correct_index = item["correctIndex"]
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError("Each question must have exactly 4 options")
        if not isinstance(correct_index, int) or not (0 <= correct_index < 4):
            raise ValueError("correctIndex must be an integer from 0 to 3")
        questions.append(
            {
                "question": str(item["question"]),
                "options": [str(option) for option in options],
                "correctIndex": correct_index,
                "explanation": str(item["explanation"]),
            }
        )
    return questions


def _generate_via_gemini(difficulty: str, num_questions: int) -> list[dict]:
    system_instruction = _build_system_prompt(difficulty, num_questions)
    prompt = _PROMPT_TEMPLATE.format(count=num_questions)
    # ~250 tokens/question (question + 4 options + explanation) is a
    # comfortable budget, same per-question ratio app/quiz.py used (2500
    # for 5 questions = 500/question; a little tighter here since this
    # can go up to 15 questions and JSON overhead doesn't scale linearly).
    max_output_tokens = max(500, num_questions * 350)

    client = _get_gemini_client()

    def call(text_prompt: str, temperature: float) -> str:
        response = client.models.generate_content(
            model=_GEMINI_MODEL,
            contents=text_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned no text content")
        return text

    text = call(prompt, temperature=0.8)
    try:
        return _parse_practice_json(text, num_questions)
    except (json.JSONDecodeError, ValueError, KeyError, TypeError):
        # One retry, with an explicit note about the previous failure and
        # temperature 0 for the most literal, least creative compliance --
        # same two-strikes pattern app/quiz.py used.
        stricter_prompt = (
            prompt
            + "\n\nIMPORTANT: your previous response could not be parsed "
            "as JSON. Respond again with ONLY the raw JSON array -- no "
            "markdown code fences, no ```json, no explanation before or "
            "after it, and no other text whatsoever."
        )
        text = call(stricter_prompt, temperature=0.0)
        return _parse_practice_json(text, num_questions)  # let this one raise if it still fails


# -- deterministic fallback bank --------------------------------------------
#
# Used whenever Gemini fails outright (no/invalid key, network error) or
# still returns unparseable/malformed JSON after the retry above -- same
# "never leave the user with a bare error for a nice-to-have AI feature"
# principle app/explainer.py's template fallback follows, just as a fixed
# bank here rather than a generator (a practice MCQ, unlike a step
# explanation, has no data to template from -- there's no live DebugStep
# grounding a practice question the way there is for /explain).

_FALLBACK_BANK: dict[str, list[dict]] = {
    "easy": [
        {
            "question": "What is the main difference between a stored procedure and a stored function?",
            "options": [
                "A function must return a value via RETURN; a procedure does not have to",
                "A procedure can only contain one SQL statement",
                "A function cannot accept parameters",
                "There is no difference -- the terms are interchangeable",
            ],
            "correctIndex": 0,
            "explanation": "A function is declared with a RETURNS type and must RETURN a value of that type; a procedure has no return type and communicates results (if any) via OUT/INOUT parameters instead.",
        },
        {
            "question": "Which parameter mode allows a stored procedure to both receive a value and send a modified value back to the caller?",
            "options": ["IN", "OUT", "INOUT", "RETURN"],
            "correctIndex": 2,
            "explanation": "INOUT parameters are initialized from the caller's argument and can be reassigned inside the procedure; the final value is visible to the caller after the call returns. IN is read-only and OUT starts unset.",
        },
        {
            "question": "What are the four steps of the standard cursor lifecycle, in order?",
            "options": [
                "OPEN, FETCH, CLOSE, DECLARE",
                "DECLARE, OPEN, FETCH, CLOSE",
                "FETCH, DECLARE, OPEN, CLOSE",
                "DECLARE, FETCH, OPEN, CLOSE",
            ],
            "correctIndex": 1,
            "explanation": "A cursor is DECLAREd (bound to a query), OPENed (the query executes and the result set is positioned before the first row), FETCHed repeatedly to read rows one at a time, and finally CLOSEd to release it.",
        },
        {
            "question": "What does a cursor attribute like `cur_name%NOTFOUND` indicate right after a FETCH?",
            "options": [
                "The cursor was never opened",
                "The most recent FETCH did not return a row (the cursor is exhausted)",
                "The table being queried does not exist",
                "The FETCH statement had a syntax error",
            ],
            "correctIndex": 1,
            "explanation": "%NOTFOUND becomes true the moment a FETCH runs past the last row of the result set -- the standard way to detect end-of-cursor and break out of a fetch loop.",
        },
        {
            "question": "In exception handling, what does DECLARE CONTINUE HANDLER (as opposed to an EXIT handler) do when the declared condition is raised?",
            "options": [
                "It stops the whole procedure immediately",
                "It runs the handler's code and then resumes execution with the statement right after the one that raised the condition",
                "It rolls back the entire transaction and re-raises the error to the caller",
                "It silently ignores the condition with no handler code running at all",
            ],
            "correctIndex": 1,
            "explanation": "A CONTINUE handler runs its own block and then lets execution continue normally in the procedure, unlike an EXIT handler, which runs its block and then leaves the enclosing block entirely.",
        },
        {
            "question": "Which condition is conventionally raised when a FETCH runs out of rows to read?",
            "options": ["DIVISION_BY_ZERO", "NOT_FOUND", "OUT_OF_MEMORY", "SYNTAX_ERROR"],
            "correctIndex": 1,
            "explanation": "NOT_FOUND is the standard SQLSTATE-style condition tied to an exhausted cursor fetch (or a SELECT...INTO that matched no row), which a DECLARE ... HANDLER FOR NOT_FOUND can catch.",
        },
        {
            "question": "What is the purpose of an IF/ELSE statement inside a stored procedure?",
            "options": [
                "To declare a new cursor",
                "To branch execution based on a boolean condition",
                "To open a database connection",
                "To define a function's return type",
            ],
            "correctIndex": 1,
            "explanation": "IF/ELSE (and IF/ELSEIF/ELSE) is basic conditional control flow -- it evaluates a condition and executes one branch or the other, exactly like in any procedural language.",
        },
        {
            "question": "What does a WHILE loop's condition control?",
            "options": [
                "Whether the procedure is allowed to be called at all",
                "Whether the loop body runs again, checked before each iteration",
                "How many parameters the procedure accepts",
                "Which handler catches an exception",
            ],
            "correctIndex": 1,
            "explanation": "A WHILE loop re-checks its condition before every iteration (including the first); as soon as it evaluates false, the loop body stops running and execution continues after the loop.",
        },
    ],
    "medium": [
        {
            "question": "A procedure declares `DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = TRUE;` before a fetch loop. What happens on the FETCH that finally finds no more rows?",
            "options": [
                "The procedure aborts immediately with an unhandled error",
                "`done` is set to TRUE and execution continues with the statement after that FETCH -- typically a loop condition check",
                "The cursor is automatically reopened from the first row",
                "Nothing -- CONTINUE handlers only catch DIVISION_BY_ZERO",
            ],
            "correctIndex": 1,
            "explanation": "The handler catches NOT_FOUND, runs its one statement (SET done = TRUE), and then execution resumes right after the FETCH -- the enclosing WHILE NOT done loop then exits on its next condition check.",
        },
        {
            "question": "A parameter is declared IN and the procedure body reassigns it with SET. What does the caller see after the call?",
            "options": [
                "The caller's original argument, unchanged -- IN parameters are read-only from the caller's perspective",
                "The reassigned value, since all parameters are passed by reference",
                "A runtime error, since IN parameters cannot legally be reassigned at all",
                "NULL, since reassigning an IN parameter clears it",
            ],
            "correctIndex": 0,
            "explanation": "IN parameters are effectively passed by value: the procedure can reassign its own local copy freely, but that change never propagates back to the caller's variable, unlike OUT/INOUT.",
        },
        {
            "question": "Inside a WHILE loop, a division `total / count` can raise DIVISION_BY_ZERO when `count` is 0. If no handler for DIVISION_BY_ZERO is declared, what happens?",
            "options": [
                "It is silently treated as NULL and the loop continues",
                "It is an unhandled condition -- typically fatal, aborting the procedure at that point",
                "It is automatically caught by the nearest NOT_FOUND handler instead",
                "It retries the division with count treated as 1",
            ],
            "correctIndex": 1,
            "explanation": "An undeclared/unhandled condition is not silently absorbed -- without a matching handler, DIVISION_BY_ZERO propagates as a fatal error and halts execution at that statement.",
        },
        {
            "question": "A function is declared `RETURNS INT`. Which statement correctly ends its execution and hands a value back to the caller?",
            "options": ["EXIT 5;", "RETURN 5;", "SET RETURN = 5;", "OUT 5;"],
            "correctIndex": 1,
            "explanation": "RETURN <expr> both ends the function's execution and supplies the value the caller receives; a function without a matching RETURN before it finishes is generally invalid.",
        },
        {
            "question": "What is the key difference between CALLing a procedure from another procedure versus calling a function inside an expression?",
            "options": [
                "There is no difference -- both are written identically",
                "CALL invokes a procedure as its own statement (no value substituted into an expression); a function call appears inside an expression and is replaced by its RETURN value",
                "Functions can only be called from the top level, never from inside another procedure",
                "CALL can only invoke functions, never procedures",
            ],
            "correctIndex": 1,
            "explanation": "CALL ProcName(...) is a standalone statement that runs a procedure for its side effects/OUT params; a function call like `SET x = ComputeTotal(price, qty)` is an expression that evaluates to the function's RETURN value.",
        },
        {
            "question": "A CASE statement has three WHEN branches and no ELSE. If none of the WHEN conditions match, what happens?",
            "options": [
                "A syntax error is raised at parse time",
                "The first WHEN branch runs anyway as a default",
                "No branch runs at all, and execution simply continues with whatever statement follows the CASE",
                "The procedure automatically raises NOT_FOUND",
            ],
            "correctIndex": 2,
            "explanation": "Without an ELSE, a CASE that matches no WHEN simply falls through -- no branch executes and no error is raised, execution just proceeds to the next statement.",
        },
        {
            "question": "Inside a labeled LOOP (e.g. `outer_loop: LOOP ... END LOOP outer_loop;`), what does `LEAVE outer_loop;` do?",
            "options": [
                "Skips to the next iteration of the loop, like CONTINUE",
                "Exits the labeled loop entirely, resuming execution after its END LOOP",
                "Raises the NOT_FOUND condition",
                "Restarts the loop from its very first iteration",
            ],
            "correctIndex": 1,
            "explanation": "LEAVE (optionally with a label, needed when loops are nested) breaks out of the targeted loop entirely -- unlike a bare CONTINUE-style skip, it does not run any more iterations of that loop.",
        },
        {
            "question": "What does `SELECT total INTO running_total FROM orders WHERE id = 5;` do when no row matches id = 5?",
            "options": [
                "running_total is set to 0",
                "running_total is set to NULL explicitly",
                "running_total is left unchanged and the NOT_FOUND condition is raised, exactly like an exhausted cursor FETCH",
                "The statement silently does nothing and no condition is raised",
            ],
            "correctIndex": 2,
            "explanation": "A zero-row SELECT...INTO reuses the same NOT_FOUND condition an exhausted cursor FETCH raises -- the target variable(s) keep whatever value they held before, and a declared handler can catch it the same way.",
        },
    ],
    "hard": [
        {
            "question": "A procedure has two nested loops, each with its own CONTINUE HANDLER FOR NOT_FOUND, and the inner loop's cursor exhausts first. Which handler catches the NOT_FOUND condition?",
            "options": [
                "The outer loop's handler, since it was declared first",
                "The inner loop's handler -- exception handling resolves to the innermost matching handler in scope at the point the condition is raised",
                "Both handlers run, in declaration order",
                "Neither -- nested loops cannot each declare their own handler",
            ],
            "correctIndex": 1,
            "explanation": "Handler scoping resolves innermost-first: the handler declared in the block where the condition is actually raised catches it, so the inner loop's own NOT_FOUND handler fires, not the outer one.",
        },
        {
            "question": "A procedure passes a variable as an INOUT argument to another procedure it CALLs, and that callee reassigns the parameter twice before returning. What value does the caller see in its own variable afterward?",
            "options": [
                "The value from the first reassignment only",
                "The original value, unchanged, since INOUT never propagates through a CALL",
                "The final value after the callee's last reassignment",
                "An error -- INOUT parameters cannot be passed through a nested CALL",
            ],
            "correctIndex": 2,
            "explanation": "INOUT threads the value both directions: the callee starts with the caller's current value, and whatever it holds when the callee finishes is written back -- only the last reassignment before return matters to the caller.",
        },
        {
            "question": "Inside a WHILE loop, a DIVISION_BY_ZERO is raised and caught by a CONTINUE HANDLER that sets a flag and does nothing else. What is the risk if the loop's own exit condition depends on a variable that division was supposed to update?",
            "options": [
                "None -- the loop always exits safely regardless",
                "The loop can become infinite, since the variable the exit condition depends on never gets updated by the skipped division",
                "The procedure raises NOT_FOUND automatically as a safeguard",
                "The CONTINUE handler automatically also updates the loop counter",
            ],
            "correctIndex": 1,
            "explanation": "A CONTINUE handler only prevents the error from being fatal -- it does not retry or fix the skipped statement. If that statement was the only thing advancing the loop's exit condition, the loop can spin forever.",
        },
        {
            "question": "A function calls itself recursively without ever hitting a base-case RETURN. Combined with IN parameters being passed by value, what is the most accurate description of the failure mode?",
            "options": [
                "It fails immediately at parse time -- recursion is not legal syntax",
                "It runs until some resource/recursion limit is hit (e.g. stack exhaustion), since each call gets its own independent copy of its IN parameters and nothing stops the recursion from the caller's side",
                "OUT parameters silently cap the recursion at one level",
                "It succeeds and returns NULL after exactly one call",
            ],
            "correctIndex": 1,
            "explanation": "Recursion is ordinary control flow, not special syntax; each call's IN parameters are independent local copies, so without a base case actually reached, the calls keep nesting until something external (a recursion/stack limit) stops it.",
        },
        {
            "question": "A CASE statement's WHEN branch that matches contains a RETURN inside a function. A later statement in the function, after the CASE, also has a RETURN. Which one determines the function's result for that call?",
            "options": [
                "The later RETURN always wins, since it executes last in source order",
                "Both are evaluated and the function returns a list",
                "The RETURN inside the matched WHEN branch -- it ends execution immediately, so the later RETURN is never reached for that call",
                "It is a syntax error to have RETURN inside a CASE branch",
            ],
            "correctIndex": 2,
            "explanation": "RETURN ends execution the moment it runs, wherever it is -- inside a matched WHEN branch, it exits the function right there, so any code after the CASE (including another RETURN) never executes for that call.",
        },
        {
            "question": "A CONTINUE HANDLER FOR NOT_FOUND is declared, but the condition that is actually raised is DIVISION_BY_ZERO, with no handler declared for it. What happens?",
            "options": [
                "The NOT_FOUND handler catches it anyway, since it's the only handler declared",
                "DIVISION_BY_ZERO is unhandled and propagates as a fatal error -- a handler only catches the specific condition(s) it was declared for",
                "The procedure silently treats the division result as 0",
                "Both conditions are merged into one generic ERROR handler automatically",
            ],
            "correctIndex": 1,
            "explanation": "Handlers are matched by the specific condition they declare, not as a catch-all -- a NOT_FOUND handler does not catch DIVISION_BY_ZERO, so an undeclared DIVISION_BY_ZERO is still fatal even though some handler exists in the procedure.",
        },
        {
            "question": "A cursor's query joins two tables and is opened once; the fetch loop runs, and partway through, another statement inside the same loop body INSERTs a new row into one of the joined tables that would match the cursor's WHERE clause. Does the cursor's remaining FETCHes see that new row?",
            "options": [
                "Yes, always -- cursors always re-evaluate their query on every FETCH",
                "It depends on the database's cursor semantics (static vs. dynamic result set) -- a typical simple implementation snapshots the result set at OPEN time, so the new row is not seen",
                "The INSERT is rejected outright while a cursor is open on a related table",
                "The cursor automatically closes and reopens itself",
            ],
            "correctIndex": 1,
            "explanation": "Most straightforward cursor implementations fix the result set at OPEN time (a static/insensitive cursor) -- rows inserted afterward, even into a joined table, are not retroactively picked up by that cursor's remaining FETCHes.",
        },
        {
            "question": "An OUT parameter is never assigned anywhere in the procedure body before it returns. What value does the caller see?",
            "options": [
                "Whatever value the caller's own variable held before the CALL, since OUT parameters are pass-by-reference for reads too",
                "0 or an empty string, depending on the declared type, as a default",
                "Whatever the OUT parameter's own unset/default state is (commonly NULL/unset) -- OUT starts with no meaningful value from the caller's side and nothing set it",
                "A parse-time error -- every OUT parameter must be assigned at least once",
            ],
            "correctIndex": 2,
            "explanation": "Unlike IN/INOUT, an OUT parameter does not inherit the caller's argument value at all -- it starts unset inside the procedure, and if the body never assigns it, the caller gets back whatever that unset/default state is, not their original value.",
        },
    ],
}

for _level in DIFFICULTIES:
    assert len(_FALLBACK_BANK[_level]) >= 5, f"fallback bank for {_level!r} must have at least 5 questions"


def _fallback_questions(difficulty: str, num_questions: int) -> list[dict]:
    """Sample `num_questions` from the fixed bank for this difficulty.
    Without replacement when the bank is big enough (avoids duplicates in
    the common case), falling back to sampling WITH replacement when more
    questions are requested than the bank holds (up to 15 can be asked
    for; the bank is smaller than that)."""
    bank = _FALLBACK_BANK[difficulty]
    if num_questions <= len(bank):
        chosen = random.sample(bank, num_questions)
    else:
        chosen = random.choices(bank, k=num_questions)
    # Return copies -- callers/tests may mutate the returned dicts, and
    # random.sample/choices return references into the module-level bank.
    return [dict(q) for q in chosen]


# -- orchestrator: Gemini (with one retry) -> fallback bank -----------------


def generate_practice_questions(difficulty: str, num_questions: int) -> list[dict]:
    """Return a list of exactly `num_questions` question dicts for the
    given difficulty. Always succeeds (unlike the old /quiz, which had no
    fallback) -- any Gemini failure (missing/invalid key, network, rate
    limit, still-malformed JSON after the retry) degrades to the
    hardcoded fallback bank rather than raising."""
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty {difficulty!r}")
    if not (1 <= num_questions <= 15):
        raise ValueError("num_questions must be between 1 and 15")

    try:
        return _generate_via_gemini(difficulty, num_questions)
    except Exception:
        # Any failure at all (missing/wrong key, network, rate limit,
        # timeout, an empty response, still-unparseable JSON after the
        # retry, ...) degrades to the deterministic fallback bank rather
        # than surfacing an error -- same "never leave the user with a
        # bare failure for a nice-to-have AI feature" principle
        # app/explainer.py's template fallback follows for /explain.
        return _fallback_questions(difficulty, num_questions)
