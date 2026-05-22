import html
import io
import zipfile


def _make_xlsx(rows, sheet_name="报关单"):
    strings = []
    indexes = {}

    def string_index(value):
        text = str(value)
        if text not in indexes:
            indexes[text] = len(strings)
            strings.append(text)
        return indexes[text]

    def col_name(index):
        index += 1
        out = ""
        while index:
            index, rem = divmod(index - 1, 26)
            out = chr(65 + rem) + out
        return out

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            ref = f"{col_name(col_index)}{row_index}"
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="s"><v>{string_index(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    shared_strings = "".join(f"<si><t>{html.escape(value)}</t></si>" for value in strings)
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{html.escape(sheet_name)}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        "xl/_rels/workbook.xml.rels": """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/sharedStrings.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  {shared_strings}
</sst>""",
        "xl/worksheets/sheet1.xml": f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(sheet_rows)}
  </sheetData>
</worksheet>""",
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    return out.getvalue()


def test_run_excel_and_read_text_reads_xlsx_rows():
    from app.services.excel_extractor import run_excel_and_read_text

    outputs = run_excel_and_read_text(
        file_name="declaration.xlsx",
        file_bytes=_make_xlsx(
            [
                ["报关单号", "IB0001"],
                ["贸易方式", "一般贸易"],
                ["数量", 12],
            ]
        ),
    )

    assert "## 报关单" in outputs["markdown"]
    assert "报关单号" in outputs["text"]
    assert "IB0001" in outputs["text"]
    assert outputs["json"]["sheets"][0]["rows"][2] == ["数量", "12"]
    assert any(item["path"] == "excel/preview.md" for item in outputs["history_assets"])


def test_run_excel_and_read_text_adds_compact_table_for_sparse_invoice_rows():
    from app.services.excel_extractor import run_excel_and_read_text

    header = [""] * 98
    header[1] = "ITEM"
    header[11] = "P/O"
    header[45] = "SAMSUNG P/N"
    header[68] = "PC"
    header[82] = "@RMB/1000"
    header[97] = "RMB"
    detail = [""] * 98
    detail[1] = "5"
    detail[11] = "XHD01-20251009-015"
    detail[45] = "CL10B332KB8WPNC"
    detail[68] = "164,000"
    detail[82] = "1"
    detail[97] = "164000"

    outputs = run_excel_and_read_text(
        file_name="invoice.xlsx",
        file_bytes=_make_xlsx([header, detail], sheet_name="LEIV001"),
    )

    assert "### 结构化表格：LEIV001 第 1 行" in outputs["markdown"]
    assert "| 源行 | ITEM | P/O | SAMSUNG P/N | PC | @RMB/1000 | RMB |" in outputs["markdown"]
    assert "| 2 | 5 | XHD01-20251009-015 | CL10B332KB8WPNC | 164,000 | 1 | 164000 |" in outputs["markdown"]


def test_build_extract_payload_routes_xlsx_to_excel_text(tmp_path, monkeypatch):
    import app.api.app as main_mod

    seen = {}
    called = {"mineru": 0, "opendataloader": 0, "qwen": 0}

    monkeypatch.setattr(main_mod, "project_root", tmp_path)
    monkeypatch.setattr(main_mod, "extract_fields_by_regions", lambda *args, **kwargs: {})
    def fake_llm_extract(**kwargs):
        seen["text"] = kwargs["text"]
        return {
            "detected": {"报关单号": "IB0001"},
            "endpoint": kwargs["base_url"],
            "model": kwargs["model"],
            "content": '{"报关单号":"IB0001"}',
        }

    monkeypatch.setattr(main_mod, "run_llm_extract", fake_llm_extract)
    monkeypatch.setattr(main_mod, "run_mineru_and_read_text", lambda **kwargs: called.__setitem__("mineru", called["mineru"] + 1) or {})
    monkeypatch.setattr(
        main_mod,
        "run_opendataloader_and_read_text",
        lambda **kwargs: called.__setitem__("opendataloader", called["opendataloader"] + 1) or {},
    )
    monkeypatch.setattr(
        main_mod,
        "run_qwen_vision_extract",
        lambda **kwargs: called.__setitem__("qwen", called["qwen"] + 1) or {},
    )

    payload = main_mod._build_extract_payload(
        file_name="declaration.xlsx",
        file_bytes=_make_xlsx([["报关单号", "IB0001"]]),
        vendor="嘉盛半导体",
        doc_type="报关单",
        fields="",
        region_rules="",
        llm_prompt="提取报关单号",
        llm_base_url="https://example.com/v1",
        llm_model="demo-model",
        llm_api_key="",
        mineru_model_version="vlm",
        backend="vlm",
        parse_method="auto",
        lang_list="en",
        ocr_engine="qwen_vision",
    )

    assert called == {"mineru": 0, "opendataloader": 0, "qwen": 0}
    assert "报关单号" in seen["text"]
    assert "IB0001" in seen["text"]
    assert payload["ocr_engine"] == "excel"
    assert payload["ocr_engine_label"] == "Excel 表格解析"
    assert payload["model_version"] == "excel"
    assert payload["detected"] == {"报关单号": "IB0001"}
    history_path = tmp_path / "output" / "history" / payload["history"]["id"] / "unzipped" / "excel" / "preview.md"
    assert history_path.is_file()
