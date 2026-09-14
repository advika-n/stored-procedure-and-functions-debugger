import base64
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CALCULATE_DISCOUNT = """\
DECLARE total NUMBER DEFAULT 0;
DECLARE discount NUMBER DEFAULT 0;
SET total = price * quantity;
IF total > 100 THEN
    SET discount = total * 0.1;
ELSE
    SET discount = total * 0.05;
END IF;
SET total = total - discount;
"""


def _run_debug(params=None):
    """Drives the real /debug endpoint first, exactly like the frontend
    does before ever calling /debug/report -- so every test here exports
    a genuine, freshly-interpreted trace, never a hand-built fixture."""
    response = client.post(
        "/debug",
        json={"code": CALCULATE_DISCOUNT, "params": params or {"price": 20, "quantity": 6}, "name": "Calculate Discount"},
    )
    assert response.status_code == 200
    return response.json()["steps"]


def _tiny_png_data_url():
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (30, 15), color=(0, 128, 128)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_report_endpoint_rejects_unknown_format():
    steps = _run_debug()
    response = client.post(
        "/debug/report",
        json={"format": "exe", "code": CALCULATE_DISCOUNT, "steps": steps},
    )
    assert response.status_code == 400


def test_report_endpoint_rejects_empty_steps():
    response = client.post(
        "/debug/report",
        json={"format": "txt", "code": CALCULATE_DISCOUNT, "steps": []},
    )
    assert response.status_code == 400


def test_report_endpoint_txt_contains_real_run_data():
    steps = _run_debug(params={"price": 20, "quantity": 6})
    response = client.post(
        "/debug/report",
        json={
            "format": "txt",
            "code": CALCULATE_DISCOUNT,
            "params": {"price": 20, "quantity": 6},
            "name": "Calculate Discount",
            "steps": steps,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attachment" in response.headers["content-disposition"]
    assert ".txt" in response.headers["content-disposition"]

    text = response.text
    assert "Calculate Discount" in text
    assert "108.0" in text  # the real final total, same value /debug itself returned
    assert "lorem ipsum" not in text.lower()


def test_report_endpoint_docx_opens_and_contains_real_run_data():
    from docx import Document

    steps = _run_debug(params={"price": 20, "quantity": 6})
    response = client.post(
        "/debug/report",
        json={
            "format": "docx",
            "code": CALCULATE_DISCOUNT,
            "params": {"price": 20, "quantity": 6},
            "name": "Calculate Discount",
            "steps": steps,
        },
    )
    assert response.status_code == 200
    assert "wordprocessingml.document" in response.headers["content-type"]

    doc = Document(io.BytesIO(response.content))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Calculate Discount" in all_text
    assert any("108.0" in cell.text for table in doc.tables for row in table.rows for cell in row.cells)


def test_report_endpoint_pdf_is_a_real_pdf():
    steps = _run_debug()
    response = client.post(
        "/debug/report",
        json={"format": "pdf", "code": CALCULATE_DISCOUNT, "name": "Calculate Discount", "steps": steps},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert len(response.content) > 1000


def test_report_endpoint_embeds_client_rasterized_flowchart_image():
    steps = _run_debug()
    response = client.post(
        "/debug/report",
        json={
            "format": "pdf",
            "code": CALCULATE_DISCOUNT,
            "name": "Calculate Discount",
            "steps": steps,
            "flowchartImage": _tiny_png_data_url(),
        },
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")


def test_report_endpoint_ignores_malformed_flowchart_image_instead_of_failing():
    steps = _run_debug()
    response = client.post(
        "/debug/report",
        json={
            "format": "txt",
            "code": CALCULATE_DISCOUNT,
            "name": "Calculate Discount",
            "steps": steps,
            "flowchartImage": "not-a-real-data-url",
        },
    )
    assert response.status_code == 200
    assert "No control-flow diagram image was captured" in response.text


def test_report_endpoint_is_honest_about_missing_params():
    steps = _run_debug(params={})
    response = client.post(
        "/debug/report",
        json={"format": "txt", "code": "DECLARE x NUMBER DEFAULT 1;", "params": {}, "steps": steps},
    )
    assert response.status_code == 200
    assert "does not currently provide a UI" in response.text


def test_report_endpoint_does_not_require_a_fresh_debug_run(monkeypatch):
    """The whole point of this endpoint: it must work from a trace the
    caller already has, without this module re-invoking the interpreter
    itself. Patch app.interpreter.run to explode if it's ever called from
    this endpoint's code path."""
    import app.main as main_module

    steps = _run_debug()  # get a real trace via the *unpatched* /debug first

    def _boom(*args, **kwargs):
        raise AssertionError("report endpoint must not re-run the interpreter")

    monkeypatch.setattr(main_module, "run", _boom)

    response = client.post(
        "/debug/report",
        json={"format": "txt", "code": CALCULATE_DISCOUNT, "name": "Calculate Discount", "steps": steps},
    )
    assert response.status_code == 200
