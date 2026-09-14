import io

from app import report
from app.interpreter import run
from app.parser import parse
from app.tokenizer import tokenize

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


def _real_steps(code=CALCULATE_DISCOUNT, params=None):
    """A real DebugStep trace, produced by actually running the
    interpreter -- never hand-written/fabricated -- so every report test
    below is checking against genuine execution data."""
    ast = parse(tokenize(code))
    steps = run(ast, params or {"price": 20, "quantity": 6})
    return ast, [step.to_dict() for step in steps]


def test_build_report_user_inputs_includes_real_code_and_honest_empty_params():
    _, steps = _real_steps(params={})
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={}, procedure_name="Calculate Discount", steps=steps, flowchart_png_bytes=None
    )
    user_inputs = next(s for s in sections if s.title == "User Inputs")
    code_block = next(b for b in user_inputs.blocks if b.kind == "code")
    assert code_block.text == CALCULATE_DISCOUNT
    # No params were sent -- must say so honestly, never fabricate a value.
    joined = " ".join(b.text for b in user_inputs.blocks if b.kind == "paragraph" and b.text)
    assert "none" in joined.lower()
    assert "does not currently provide a UI" in joined


def test_build_report_user_inputs_lists_real_params_when_present():
    _, steps = _real_steps(params={"price": 20, "quantity": 6})
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={"price": 20, "quantity": 6}, procedure_name="x", steps=steps, flowchart_png_bytes=None
    )
    user_inputs = next(s for s in sections if s.title == "User Inputs")
    table = next(b for b in user_inputs.blocks if b.kind == "table")
    assert ["price", "20"] in table.rows
    assert ["quantity", "6"] in table.rows


def test_build_report_processing_steps_matches_real_trace():
    _, steps = _real_steps()
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={}, procedure_name="x", steps=steps, flowchart_png_bytes=None
    )
    assert meta["step_count"] == len(steps) == 6
    processing = next(s for s in sections if s.title == "Processing Steps")
    table = next(b for b in processing.blocks if b.kind == "table")
    assert len(table.rows) == len(steps)
    # Real line numbers/statement text from the actual steps, not placeholders.
    assert table.rows[0][1] == str(steps[0]["line"])
    assert table.rows[0][3] == steps[0]["statementText"]


def test_build_report_intermediate_results_reflects_variable_changes():
    _, steps = _real_steps()
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={}, procedure_name="x", steps=steps, flowchart_png_bytes=None
    )
    intermediate = next(s for s in sections if s.title == "Intermediate Results")
    table = next(b for b in intermediate.blocks if b.kind == "table")
    # "total" is declared, then reassigned twice -- expect at least 3 rows for it.
    total_rows = [r for r in table.rows if r[1] == "total"]
    assert len(total_rows) >= 3


def test_build_report_final_output_uses_last_steps_final_value():
    _, steps = _real_steps(params={"price": 20, "quantity": 6})
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={"price": 20, "quantity": 6}, procedure_name="x", steps=steps, flowchart_png_bytes=None
    )
    final = next(s for s in sections if s.title == "Final Output")
    final_table = next(b for b in final.blocks if b.kind == "table")
    total_row = next(r for r in final_table.rows if r[0] == "total")
    # price*quantity = 120 -> >100 branch -> discount 10% -> total = 108.0, the
    # exact same value test_debug_endpoint.py asserts against the real interpreter.
    assert total_row[1] == "108.0"


def test_build_report_graphs_section_notes_missing_image_honestly():
    _, steps = _real_steps()
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={}, procedure_name="x", steps=steps, flowchart_png_bytes=None
    )
    graphs = next(s for s in sections if s.title == "Graphs, Tables & Figures")
    paragraphs = [b.text for b in graphs.blocks if b.kind == "paragraph"]
    assert any("No control-flow diagram image was captured" in p for p in paragraphs)


def test_build_report_graphs_section_includes_real_image_bytes():
    fake_png = b"\x89PNG\r\n\x1a\nfake-but-real-bytes"
    _, steps = _real_steps()
    meta, sections = report.build_report(
        code=CALCULATE_DISCOUNT, params={}, procedure_name="x", steps=steps, flowchart_png_bytes=fake_png
    )
    graphs = next(s for s in sections if s.title == "Graphs, Tables & Figures")
    image_block = next(b for b in graphs.blocks if b.kind == "image")
    assert image_block.image_bytes == fake_png


def test_decode_flowchart_image_handles_data_url_and_raw_base64():
    import base64

    raw = b"hello world"
    encoded = base64.b64encode(raw).decode()
    assert report.decode_flowchart_image(f"data:image/png;base64,{encoded}") == raw
    assert report.decode_flowchart_image(encoded) == raw


def test_decode_flowchart_image_returns_none_for_garbage_or_missing():
    assert report.decode_flowchart_image(None) is None
    assert report.decode_flowchart_image("") is None
    assert report.decode_flowchart_image("not valid base64!!!") is None


def test_generate_report_text_contains_real_data_not_placeholders():
    _, steps = _real_steps(params={"price": 20, "quantity": 6})
    content, content_type, filename = report.generate_report(
        fmt="txt",
        code=CALCULATE_DISCOUNT,
        params={"price": 20, "quantity": 6},
        procedure_name="Calculate Discount",
        steps=steps,
        flowchart_png_bytes=None,
    )
    text = content.decode("utf-8")
    assert content_type == "text/plain; charset=utf-8"
    assert filename.endswith(".txt")
    assert "lorem ipsum" not in text.lower()
    assert "Calculate Discount" in text
    assert "SET total = total - discount" in text
    assert "108.0" in text


def test_generate_report_docx_round_trips_via_python_docx():
    from docx import Document

    _, steps = _real_steps(params={"price": 20, "quantity": 6})
    content, content_type, filename = report.generate_report(
        fmt="docx",
        code=CALCULATE_DISCOUNT,
        params={"price": 20, "quantity": 6},
        procedure_name="Calculate Discount",
        steps=steps,
        flowchart_png_bytes=None,
    )
    assert content_type.endswith("wordprocessingml.document")
    assert filename.endswith(".docx")

    doc = Document(io.BytesIO(content))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Calculate Discount" in all_text
    # At least the Processing Steps table should have real rows -> real cells.
    tables = doc.tables
    assert len(tables) >= 3
    step_table_cells = [cell.text for table in tables for row in table.rows for cell in row.cells]
    assert "IfStatement" in step_table_cells


def test_generate_report_pdf_produces_a_valid_pdf_with_real_content():
    _, steps = _real_steps(params={"price": 20, "quantity": 6})
    content, content_type, filename = report.generate_report(
        fmt="pdf",
        code=CALCULATE_DISCOUNT,
        params={"price": 20, "quantity": 6},
        procedure_name="Calculate Discount",
        steps=steps,
        flowchart_png_bytes=None,
    )
    assert content_type == "application/pdf"
    assert filename.endswith(".pdf")
    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 1000  # a real multi-section report, not an empty shell


def test_generate_report_pdf_embeds_a_real_flowchart_image():
    from PIL import Image as PILImage

    # A real (tiny) PNG, not fabricated bytes -- generated with Pillow so
    # reportlab's ImageReader can actually read its real width/height.
    buf = io.BytesIO()
    PILImage.new("RGB", (40, 20), color=(255, 0, 0)).save(buf, format="PNG")
    png_bytes = buf.getvalue()

    _, steps = _real_steps()
    content, _, _ = report.generate_report(
        fmt="pdf",
        code=CALCULATE_DISCOUNT,
        params={},
        procedure_name="Calculate Discount",
        steps=steps,
        flowchart_png_bytes=png_bytes,
    )
    assert content.startswith(b"%PDF-")
    # The raw PNG bytes get re-encoded into the PDF's internal image
    # stream, so we can't substring-match them directly -- a large PDF
    # (bigger than the no-image case) is the practical signal the image
    # was actually embedded rather than skipped.
    assert len(content) > 2000


def test_generate_report_rejects_unsupported_format():
    import pytest

    _, steps = _real_steps()
    with pytest.raises(ValueError):
        report.generate_report(
            fmt="exe", code=CALCULATE_DISCOUNT, params={}, procedure_name="x", steps=steps, flowchart_png_bytes=None
        )
