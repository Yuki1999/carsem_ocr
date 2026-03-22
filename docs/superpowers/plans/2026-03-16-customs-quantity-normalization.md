# Customs Quantity Normalization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure customs draft quantity fields always store the smaller-or-equal value in the good-quantity fields for both header and detail rows.

**Architecture:** Normalize the quantity pairs inside `app/customs_submission.py` after numeric parsing so every draft source follows the same rule. Cover the behavior with focused backend tests before changing production code.

**Tech Stack:** Python, pytest

---

## Chunk 1: Backend Quantity Pair Normalization

### Task 1: Lock the header rule with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_submission_draft_swaps_header_quantity_fields_when_good_quantity_is_larger():
    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "header": {
                "TotalQuantity": "10",
                "GoodQuantity": "12",
            }
        },
    )

    assert draft["header"]["TotalQuantity"] == "12"
    assert draft["header"]["GoodQuantity"] == "10"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_swaps_header_quantity_fields_when_good_quantity_is_larger -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Add a helper in `app/customs_submission.py` that parses the numeric text of the quantity pair and swaps the stored strings when the good quantity is larger than the total quantity.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_swaps_header_quantity_fields_when_good_quantity_is_larger -q`
Expected: `1 passed`

### Task 2: Lock the detail-row rule with a failing test

**Files:**
- Modify: `tests/test_customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_submission_draft_swaps_detail_quantity_fields_when_good_quantity_is_larger():
    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "details": [
                {
                    "ItemQuantity": "3",
                    "ItemGoodQuantity": "5",
                }
            ]
        },
    )

    assert draft["details"][0]["ItemQuantity"] == "5"
    assert draft["details"][0]["ItemGoodQuantity"] == "3"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_swaps_detail_quantity_fields_when_good_quantity_is_larger -q`
Expected: `FAIL`

- [ ] **Step 3: Write minimal implementation**

Apply the same quantity-pair normalization to each detail row after field normalization.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_swaps_detail_quantity_fields_when_good_quantity_is_larger -q`
Expected: `1 passed`

### Task 3: Verify non-numeric placeholders stay untouched

**Files:**
- Modify: `tests/test_customs_submission.py`
- Test: `tests/test_customs_submission.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_submission_draft_does_not_swap_quantity_fields_for_placeholder_values():
    draft = build_submission_draft(
        response_payload={"detected": {}},
        template={},
        llm_output={
            "header": {
                "TotalQuantity": "-1",
                "GoodQuantity": "5",
            }
        },
    )

    assert draft["header"]["TotalQuantity"] == "-1"
    assert draft["header"]["GoodQuantity"] == "5"
```

- [ ] **Step 2: Run test to verify it fails or remains red for missing guard**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py::test_build_submission_draft_does_not_swap_quantity_fields_for_placeholder_values -q`
Expected: `FAIL` if the swap is too aggressive, otherwise adjust code only if needed

- [ ] **Step 3: Write minimal implementation**

Guard the normalization helper so placeholder values and unparseable values do not trigger swaps.

- [ ] **Step 4: Run the targeted backend suite**

Run: `PYTHONPATH=/home/sip-telecom/Services/carsem_ocr pytest /home/sip-telecom/Services/carsem_ocr/tests/test_customs_submission.py -q`
Expected: all tests pass
