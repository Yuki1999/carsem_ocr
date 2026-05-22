def test_packet_draft_uses_invoice_original_rows_without_merging():
    from app.services.customs_packet import build_packet_submission_draft

    llm_output = {
        "packet_id": "DS12650253",
        "invoice_lines": [
            {
                "source_row": 28,
                "ITEM": "8",
                "P/O": "XHD01-20251105-027",
                "SAMSUNG P/N": "CL31B106KOHVPNE",
                "PC": "100,000",
                "@RMB/1000": "1",
                "RMB": "100000",
                "Country of Origin": "Korea",
            },
            {
                "source_row": 29,
                "ITEM": "8",
                "P/O": "XHD01-20251105-027",
                "SAMSUNG P/N": "CL31B106KOHVPNE",
                "PC": "124,000",
                "@RMB/1000": "1",
                "RMB": "124000",
                "Country of Origin": "Korea",
            },
        ],
        "packing_lines": [
            {"source_row": 6, "C/T NO": "6", "ITEM": "8", "P/O No": "XHD01-20251105-027", "SAMSUNG P/N": "CL31B106KOHVPNE", "PC": "90,000"},
            {"source_row": 7, "C/T NO": "7", "ITEM": "8", "P/O No": "XHD01-20251105-027", "SAMSUNG P/N": "CL31B106KOHVPNE", "PC": "102,000"},
            {"source_row": 8, "C/T NO": "8", "ITEM": "8", "P/O No": "XHD01-20251105-027", "SAMSUNG P/N": "CL31B106KOHVPNE", "PC": "32,000"},
        ],
    }

    draft = build_packet_submission_draft({"filename": "DS12650253_IV(1).xlsx"}, llm_output=llm_output)

    assert [row["ItemCode"] for row in draft["details"]] == ["CL31B106KOHVPNE", "CL31B106KOHVPNE"]
    assert [row["ItemQuantity"] for row in draft["details"]] == ["100000", "124000"]
    assert draft["details"][0]["ItemUnitPrice"] == "1"
    assert draft["details"][0]["ItemPrice"] == "100000"
    assert draft["details"][0]["ItemOrigin"] == "Korea"
    assert draft["meta"]["packet"]["packing_groups"][0]["quantity"] == "224000"
    assert draft["meta"]["packet"]["detail_reviews"][0]["quantity_check"] == "matched_by_invoice_group"


def test_packet_draft_marks_mismatch_but_keeps_invoice_quantity():
    from app.services.customs_packet import build_packet_submission_draft

    draft = build_packet_submission_draft(
        {"filename": "DS12650253_IV(1).xlsx"},
        llm_output={
            "packet_id": "DS12650253",
            "invoice_lines": [
                {
                    "source_row": 28,
                    "ITEM": "8",
                    "P/O No": "XHD01-20251105-027",
                    "SAMSUNG P/N": "CL31B106KOHVPNE",
                    "PC": "224,000",
                    "RMB": "224000",
                }
            ],
            "packing_lines": [
                {"source_row": 6, "ITEM": "8", "P/O No": "XHD01-20251105-027", "SAMSUNG P/N": "CL31B106KOHVPNE", "PC": "220,000"},
            ],
        },
    )

    assert draft["details"][0]["ItemQuantity"] == "224000"
    review = draft["meta"]["packet"]["detail_reviews"][0]
    assert review["quantity_check"] == "mismatch"
    assert review["invoice_quantity"] == "224000"
    assert review["packing_quantity"] == "220000"
    assert "details[0].ItemQuantity" in draft["meta"]["required_missing"]


def test_packet_draft_preserves_header_candidates_with_recommended_value():
    from app.services.customs_packet import build_packet_submission_draft

    draft = build_packet_submission_draft(
        {"filename": "DS12650253_IV(1).xlsx"},
        llm_output={
            "header_candidates": {
                "CustomerName": {
                    "recommended": "Samsung Electronics HCMC CE Complex Co., Ltd.",
                    "candidates": [
                        {"source": "invoice", "value": "Samsung Electronics HCMC CE Complex Co., Ltd."},
                        {"source": "packing", "value": "Samsung Electronics HCMC CE Complex"},
                    ],
                    "review_required": True,
                    "reason": "发票名称更完整",
                }
            },
            "invoice_lines": [
                {"source_row": 28, "ITEM": "8", "P/O": "PO-A", "SAMSUNG P/N": "PN-1", "PC": "10"},
            ],
        },
    )

    assert draft["header"]["CustomerName"] == "Samsung Electronics HCMC CE Complex Co., Ltd."
    assert draft["meta"]["packet"]["header_candidates"]["CustomerName"]["review_required"] is True
    assert draft["meta"]["packet"]["field_reviews"][0]["field"] == "CustomerName"


def test_build_submission_draft_routes_packet_structures_to_packet_rules():
    from app.customs_submission import build_submission_draft

    draft = build_submission_draft(
        response_payload={"filename": "DS12650253_IV(1).xlsx", "detected": {}},
        template={},
        llm_output={
            "packet_id": "DS12650253",
            "invoice_lines": [
                {
                    "source_row": 28,
                    "ITEM": "8",
                    "P/O": "XHD01-20251105-027",
                    "SAMSUNG P/N": "CL31B106KOHVPNE",
                    "PC": "224,000",
                    "@RMB/1000": "1",
                    "RMB": "224000",
                }
            ],
            "packing_lines": [
                {"source_row": 6, "ITEM": "8", "P/O No": "XHD01-20251105-027", "SAMSUNG P/N": "CL31B106KOHVPNE", "PC": "224,000"},
            ],
        },
    )

    assert draft["meta"]["mapping_source"] == "packet"
    assert draft["details"][0]["ItemCode"] == "CL31B106KOHVPNE"
    assert draft["details"][0]["ItemQuantity"] == "224000"
