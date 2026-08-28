from app import history


def _sample_run(name="Sample", code="DECLARE x NUMBER DEFAULT 1;"):
    steps = [{"stepNumber": 1, "line": 1, "nodeType": "DeclareStatement", "statementText": code, "variables": {}}]
    ast = {"type": "Procedure", "body": []}
    return history.save_run(code=code, params={"a": 1}, steps=steps, ast=ast, name=name)


def test_save_and_list_runs_most_recent_first():
    first_id = _sample_run(name="First")
    second_id = _sample_run(name="Second")

    runs = history.list_runs()

    assert [r["id"] for r in runs] == [second_id, first_id]
    assert runs[0]["procedureName"] == "Second"
    assert runs[0]["status"] == "success"
    assert runs[0]["stepCount"] == 1
    assert "code" not in runs[0]  # summaries don't include the full payload


def test_list_runs_caps_at_limit():
    for i in range(5):
        _sample_run(name=f"Run {i}")

    runs = history.list_runs(limit=3)

    assert len(runs) == 3
    assert runs[0]["procedureName"] == "Run 4"  # most recent first


def test_get_run_returns_full_detail():
    run_id = _sample_run(name="Detailed", code="DECLARE y NUMBER DEFAULT 2;")

    run = history.get_run(run_id)

    assert run["procedureName"] == "Detailed"
    assert run["code"] == "DECLARE y NUMBER DEFAULT 2;"
    assert run["params"] == {"a": 1}
    assert run["ast"] == {"type": "Procedure", "body": []}
    assert len(run["steps"]) == 1


def test_get_run_returns_none_for_missing_id():
    assert history.get_run(999999) is None


def test_derive_name_uses_explicit_name_when_given():
    assert history.derive_procedure_name("SET x = 1;", "MyProcedure") == "MyProcedure"


def test_derive_name_falls_back_to_first_nonblank_line():
    code = "\n\n  DECLARE total NUMBER DEFAULT 0;\nSET total = 1;\n"
    assert history.derive_procedure_name(code, None) == "DECLARE total NUMBER DEFAULT 0;"


def test_derive_name_falls_back_to_placeholder_for_empty_code():
    assert history.derive_procedure_name("   \n  \n", None) == "Untitled procedure"


def test_delete_run_removes_it():
    run_id = _sample_run()
    assert history.delete_run(run_id) is True
    assert history.get_run(run_id) is None
    assert history.delete_run(run_id) is False  # already gone


def test_clear_all_removes_everything_and_reports_count():
    _sample_run()
    _sample_run()
    _sample_run()

    removed = history.clear_all()

    assert removed == 3
    assert history.list_runs() == []
